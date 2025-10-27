"""
Structure-Aware Retriever - Mimics human document navigation.

Combines:
1. Document structure knowledge (from TOC)
2. Semantic search (embedding similarity)
3. Intent understanding (what user is looking for)
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from genreport.core.retrieval.document_structure_analyzer import (
    DocumentStructureAnalyzer,
    DocumentSection,
)
from genreport.core.retrieval.kb_retriever import KBRetriever
from genreport.core.retrieval.embedding_service import EmbeddingService


class StructureAwareRetriever:
    """
    Retrieves chunks using document structure + semantic search.

    Human-like navigation:
    1. Understand query intent
    2. Consult "mental map" (document structure)
    3. Navigate to relevant sections
    4. Semantic search within those sections
    5. Rank and merge results
    """

    def __init__(
        self,
        db: Session,
        jurisdiction: str,
        tenant_id: UUID,
        embedding_service: EmbeddingService,
        document_structure: Dict[str, DocumentSection],
    ):
        """
        Initialize structure-aware retriever.

        Args:
            db: Database session
            jurisdiction: Jurisdiction code
            tenant_id: Tenant ID
            embedding_service: Embedding service
            document_structure: Document structure index (from TOC)
        """
        self.db = db
        self.jurisdiction = jurisdiction
        self.tenant_id = tenant_id
        self.embedding_service = embedding_service
        self.document_structure = document_structure

        # Base retriever for semantic search
        self.base_retriever = KBRetriever(
            db, jurisdiction, tenant_id, embedding_service
        )

        # Structure analyzer for navigation
        self.structure_analyzer = DocumentStructureAnalyzer()

    def retrieve(
        self,
        query: str,
        intent: str = "general",
        top_k: int = 5,
        use_structure: bool = True,
    ) -> List[Dict]:
        """
        Retrieve chunks using structure-aware strategy.

        Args:
            query: User query
            intent: Query intent (template, requirement, example, general)
            top_k: Number of results to return
            use_structure: Whether to use document structure (True) or pure semantic search (False)

        Returns:
            List of chunk dicts with relevance scores
        """
        if not use_structure or not self.document_structure:
            # Fallback to pure semantic search
            return self.base_retriever.retrieve(query, top_k)

        # Step 1: Get navigation path from structure
        navigation_path = self.structure_analyzer.get_navigation_path(
            self.document_structure, query, intent
        )

        if not navigation_path:
            # No structural match, use pure semantic search
            return self.base_retriever.retrieve(query, top_k)

        # Step 2: Retrieve from prioritized sections
        results = self._retrieve_from_sections(
            query, navigation_path, top_k * 2  # Get more candidates
        )

        # Step 3: Re-rank by intent
        results = self._rerank_by_intent(results, intent)

        # Step 4: Merge related chunks (if from same section)
        results = self._merge_related_chunks(results)

        # Step 5: Return top_k
        return results[:top_k]

    def _retrieve_from_sections(
        self, query: str, section_ids: List[str], top_k: int
    ) -> List[Dict]:
        """
        Retrieve chunks from specific sections.

        Args:
            query: User query
            section_ids: List of section IDs to search (in priority order)
            top_k: Number of results

        Returns:
            Ranked chunks from specified sections
        """
        from sqlalchemy import and_
        from genreport.core.database.models import KBChunk

        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(
            query, task_type="RETRIEVAL_QUERY"
        )

        # Build filter for section_ids
        # Section metadata stored in chunk_metadata['section_number']
        all_results = []

        for priority_idx, section_id in enumerate(section_ids):
            section = self.document_structure.get(section_id)
            if not section:
                continue

            # Query all chunks for this jurisdiction
            # Then filter by page range in Python (page_num is in chunk_metadata JSON)
            all_chunks = (
                self.db.query(KBChunk)
                .filter(KBChunk.jurisdiction == self.jurisdiction)
                .all()
            )

            # Filter by page range using chunk_metadata
            chunks = []
            for chunk in all_chunks:
                if chunk.chunk_metadata:
                    page_num = chunk.chunk_metadata.get('page_num')
                    if page_num is not None and section.page_start is not None:
                        page_end = section.page_end or (section.page_start + 10)
                        if section.page_start <= page_num <= page_end:
                            chunks.append(chunk)
                    elif page_num is None and section.page_start is None:
                        # If both are None, include the chunk (no page filtering)
                        chunks.append(chunk)

            # Calculate similarity for each chunk
            for chunk in chunks:
                if chunk.embedding is not None:
                    # Calculate L2 distance and convert to similarity score
                    distance = self._calculate_l2_distance(query_embedding, chunk.embedding)
                    similarity = max(0.0, 1.0 - (distance / 2.0))  # Convert to [0, 1]

                    # Boost score based on section priority
                    priority_boost = 0.1 * (len(section_ids) - priority_idx) / len(section_ids)

                    all_results.append({
                        "chunk_id": chunk.id,
                        "content": chunk.content,
                        "similarity_score": similarity + priority_boost,
                        "chunk_type": chunk.chunk_type,
                        "chunk_metadata": chunk.chunk_metadata,
                        "section_id": section_id,
                        "section_title": section.title,
                        "document_title": chunk.kb_document.title if chunk.kb_document else "",
                        "standard": chunk.kb_document.standard if chunk.kb_document else "",
                        "jurisdiction": chunk.jurisdiction,
                        "confidence_score": chunk.confidence_score,
                    })

        # Sort by similarity
        all_results.sort(key=lambda x: x["similarity_score"], reverse=True)

        return all_results[:top_k]

    def _rerank_by_intent(self, results: List[Dict], intent: str) -> List[Dict]:
        """
        Re-rank results based on query intent.

        Args:
            results: Initial results
            intent: Query intent

        Returns:
            Re-ranked results
        """
        intent_boosts = {
            "template": {"template": 0.3, "example": 0.1, "requirement": -0.05},
            "requirement": {"requirement": 0.2, "general": 0.05, "template": -0.1},
            "example": {"example": 0.3, "template": 0.1, "requirement": -0.05},
            "definition": {"definition": 0.3, "general": 0.1},
            "general": {},  # No boosting for general queries
        }

        boosts = intent_boosts.get(intent, {})

        for result in results:
            chunk_type = result.get("chunk_type", "general")
            boost = boosts.get(chunk_type, 0.0)
            result["similarity_score"] += boost

        # Re-sort after boosting
        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        return results

    def _merge_related_chunks(self, results: List[Dict]) -> List[Dict]:
        """
        Merge chunks from the same section if they're adjacent.

        This addresses fragmentation by combining related content.

        Args:
            results: Ranked results

        Returns:
            Results with merged chunks where appropriate
        """
        merged_results = []
        skip_indices = set()

        for i, result in enumerate(results):
            if i in skip_indices:
                continue

            # Check if next result is from same section and similar score
            if i + 1 < len(results):
                next_result = results[i + 1]

                same_section = (
                    result.get("section_id") == next_result.get("section_id")
                )
                similar_score = (
                    abs(result["similarity_score"] - next_result["similarity_score"]) < 0.05
                )
                adjacent_chunks = (
                    abs(result["chunk_id"] - next_result["chunk_id"]) <= 2
                )

                if same_section and similar_score and adjacent_chunks:
                    # Merge chunks
                    merged_content = result["content"] + "\n\n" + next_result["content"]
                    merged_result = result.copy()
                    merged_result["content"] = merged_content
                    merged_result["is_merged"] = True
                    merged_result["merged_from"] = [result["chunk_id"], next_result["chunk_id"]]

                    merged_results.append(merged_result)
                    skip_indices.add(i + 1)
                    continue

            # No merge, add as-is
            merged_results.append(result)

        return merged_results

    def _calculate_l2_distance(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate L2 (Euclidean) distance between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            L2 distance (lower is more similar)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimensionality")

        return sum((a - b) ** 2 for a, b in zip(embedding1, embedding2)) ** 0.5

    def explain_retrieval(self, query: str, intent: str = "general") -> Dict:
        """
        Explain the retrieval strategy for a query (debugging/transparency).

        Args:
            query: User query
            intent: Query intent

        Returns:
            Explanation dict with navigation path, sections searched, etc.
        """
        navigation_path = self.structure_analyzer.get_navigation_path(
            self.document_structure, query, intent
        )

        sections_searched = [
            {
                "section_id": section_id,
                "title": self.document_structure[section_id].title,
                "type": self.document_structure[section_id].section_type.value,
                "page_range": f"{self.document_structure[section_id].page_start}-{self.document_structure[section_id].page_end}",
            }
            for section_id in navigation_path
            if section_id in self.document_structure
        ]

        return {
            "query": query,
            "intent": intent,
            "navigation_path": navigation_path,
            "sections_searched": sections_searched,
            "strategy": "structure_aware" if navigation_path else "pure_semantic",
            "explanation": self._generate_explanation(query, intent, navigation_path),
        }

    def _generate_explanation(
        self, query: str, intent: str, navigation_path: List[str]
    ) -> str:
        """Generate human-readable explanation of retrieval strategy."""
        if not navigation_path:
            return f"No structural match found. Using pure semantic search for: '{query}'"

        sections_str = ", ".join([
            self.document_structure[sid].title
            for sid in navigation_path[:3]
            if sid in self.document_structure
        ])

        if intent == "template":
            return (
                f"Looking for template for '{query}'. "
                f"Prioritizing appendices and examples in sections: {sections_str}"
            )
        elif intent == "requirement":
            return (
                f"Looking for disclosure requirements for '{query}'. "
                f"Searching requirement sections: {sections_str}"
            )
        else:
            return (
                f"General search for '{query}'. "
                f"Navigating to relevant sections: {sections_str}"
            )
