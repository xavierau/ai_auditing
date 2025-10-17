"""Enhanced KB ingestion service with chunk categorization.

This is an enhanced version of KBIngestionService that integrates
the ChunkCategorizer for semi-automated review during ingestion.

Key improvements:
- Automatic chunk categorization during ingestion
- 80%+ auto-approval rate for high-confidence categorizations
- Manual review flagging for uncertain chunks
- Categorization statistics and monitoring
- Cost-efficient (<$0.05 per chunk with Gemini Flash)
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID
import logging

from sqlalchemy.orm import Session
import dspy

from genreport.core.database.models import KnowledgeBase, KBChunk
from genreport.core.parsing.pdf_extractor import PDFExtractor
from genreport.core.parsing.chunking_service import ChunkingService
from genreport.core.retrieval.embedding_service import EmbeddingService
from genreport.core.retrieval.chunk_categorizer import (
    ChunkCategorizer,
    ChunkCategorizationInput,
)


logger = logging.getLogger(__name__)


class KBIngestionServiceWithCategorizer:
    """Enhanced KB ingestion service with intelligent chunk categorization.

    Features:
    - All features from base KBIngestionService
    - Automatic chunk categorization using DSPy
    - Semi-automated review (80%+ auto-approval target)
    - Categorization statistics and monitoring
    - Cost-efficient model selection

    Example:
        >>> service = KBIngestionServiceWithCategorizer(
        ...     db=session,
        ...     categorizer_lm=dspy.LM("google/gemini-1.5-flash"),
        ...     auto_approve_threshold=0.85
        ... )
        >>> kb_doc_id = service.ingest_pdf(
        ...     pdf_path="hkfrs15.pdf",
        ...     title="HKFRS 15 Revenue Recognition",
        ...     jurisdiction="HK",
        ...     standard="HKFRS 15"
        ... )
    """

    def __init__(
        self,
        db: Session,
        categorizer_lm: Optional[dspy.LM] = None,
        auto_approve_threshold: float = 0.85,
        enable_categorization: bool = True,
    ):
        """Initialize enhanced ingestion service.

        Args:
            db: Database session
            categorizer_lm: DSPy LM for categorization (defaults to GPT-4o-mini)
            auto_approve_threshold: Confidence threshold for auto-approval (default: 0.85)
            enable_categorization: Whether to enable chunk categorization (default: True)
        """
        self.db = db
        self.pdf_extractor = PDFExtractor()
        self.chunker = ChunkingService(chunk_size=1000, chunk_overlap=200)
        self.embedding_service = EmbeddingService()

        # Initialize chunk categorizer
        self.enable_categorization = enable_categorization
        if self.enable_categorization:
            # Default to cost-efficient GPT-4o-mini if no LM provided
            if categorizer_lm is None:
                logger.info("Using default GPT-4o-mini for categorization")
                categorizer_lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)

            self.categorizer = ChunkCategorizer(
                lm=categorizer_lm, auto_approve_threshold=auto_approve_threshold
            )
            logger.info(
                f"Chunk categorization enabled (auto-approve threshold: {auto_approve_threshold})"
            )
        else:
            self.categorizer = None
            logger.info("Chunk categorization disabled")

    def ingest_pdf(
        self,
        pdf_path: str | Path,
        title: str,
        jurisdiction: str,
        standard: Optional[str] = None,
        document_type: str = "standard",
        tenant_id: Optional[UUID] = None,
    ) -> int:
        """Ingest a PDF document with chunk categorization.

        Args:
            pdf_path: Path to PDF file
            title: Document title
            jurisdiction: Jurisdiction code (HK, SG, AU)
            standard: Accounting standard (e.g., SME-FRS, HKFRS 15)
            document_type: Type of document
            tenant_id: Tenant ID (None for shared standards)

        Returns:
            ID of created KB document

        Raises:
            FileNotFoundError: If PDF doesn't exist
            Exception: If ingestion fails
        """
        pdf_path = Path(pdf_path)

        print(f"📄 Starting ingestion: {pdf_path.name}")

        # Step 1: Extract text from PDF
        print("  1️⃣  Extracting text from PDF...")
        try:
            full_text = self.pdf_extractor.extract_text(pdf_path)
            metadata = self.pdf_extractor.extract_metadata(pdf_path)
            print(
                f"     ✓ Extracted {len(full_text)} chars from {metadata['num_pages']} pages"
            )
        except Exception as e:
            raise Exception(f"PDF extraction failed: {e}") from e

        # Step 2: Create KB document record
        print("  2️⃣  Creating KB document record...")
        kb_document = KnowledgeBase(
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            title=title,
            standard=standard,
            document_type=document_type,
            source_file_path=str(pdf_path),
            raw_content=full_text[:10000],  # Store first 10K chars as preview
            access_level="PUBLIC" if tenant_id is None else "TENANT",
            is_active=True,
            kb_metadata={
                "num_pages": metadata.get("num_pages"),
                "pdf_metadata": metadata.get("metadata", {}),
                "categorization_enabled": self.enable_categorization,
            },
        )

        self.db.add(kb_document)
        self.db.flush()  # Get ID without committing
        print(f"     ✓ Created KB document (ID: {kb_document.id})")

        # Step 3: Chunk the text
        print("  3️⃣  Chunking text...")
        text_chunks = self.chunker.chunk_text(full_text)
        print(f"     ✓ Created {len(text_chunks)} chunks")

        # Step 4a: Categorize chunks (if enabled)
        categorization_results = None
        if self.enable_categorization and self.categorizer:
            print("  4a. Categorizing chunks...")
            try:
                # Prepare inputs for batch categorization
                categorization_inputs = [
                    ChunkCategorizationInput(
                        chunk_content=chunk.content[:2000],  # Truncate to max length
                        kb_document_title=title,
                        chunk_index=chunk.chunk_index,
                    )
                    for chunk in text_chunks
                ]

                # Batch categorize all chunks
                categorization_results = self.categorizer.categorize_batch(
                    categorization_inputs, log_progress=False
                )

                # Display statistics
                stats = self.categorizer.get_statistics(categorization_results)
                print(
                    f"     ✓ Categorized {stats['total_chunks']} chunks: "
                    f"{stats['auto_approved']} auto-approved "
                    f"({stats['auto_approval_rate']:.1f}%), "
                    f"{stats['pending_review']} pending review"
                )

                # Log type distribution
                type_dist = ", ".join(
                    f"{k}={v}" for k, v in stats["chunk_type_distribution"].items()
                )
                print(f"     ✓ Type distribution: {type_dist}")

            except Exception as e:
                logger.error(f"Categorization failed: {e}")
                print(f"     ⚠️  Categorization failed: {e}")
                print(f"     ⚠️  Continuing without categorization...")
                categorization_results = None

        # Step 4b: Generate embeddings and store chunks
        print("  4b. Generating embeddings and storing chunks...")
        batch_size = 100  # Process in batches to avoid memory issues

        for i in range(0, len(text_chunks), batch_size):
            batch = text_chunks[i : i + batch_size]
            batch_texts = [chunk.content for chunk in batch]

            try:
                # Generate embeddings for batch
                embeddings = self.embedding_service.generate_embeddings_batch(
                    batch_texts
                )

                # Create KB chunk records
                for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                    chunk_idx = i + j

                    # Get categorization result (if available)
                    if categorization_results and chunk_idx < len(
                        categorization_results
                    ):
                        cat_result = categorization_results[chunk_idx]
                        chunk_type = cat_result.chunk_type
                        confidence_score = cat_result.confidence_score
                        review_status = cat_result.review_status
                        categorization_metadata = {
                            "categorization_reasoning": cat_result.reasoning,
                            "categorization_timestamp": datetime.utcnow().isoformat(),
                            "categorization_model": "dspy_chain_of_thought",
                        }
                    else:
                        # Fallback if categorization disabled or failed
                        chunk_type = None
                        confidence_score = None
                        review_status = "pending_review"
                        categorization_metadata = {}

                    kb_chunk = KBChunk(
                        tenant_id=tenant_id,
                        jurisdiction=jurisdiction,
                        kb_document_id=kb_document.id,
                        chunk_index=chunk.chunk_index,
                        chunk_type=chunk_type,
                        content=chunk.content,
                        embedding=embedding,
                        embedding_model=self.embedding_service.get_model_name(),
                        confidence_score=confidence_score,
                        review_status=review_status,
                        chunk_metadata={
                            "start_char": chunk.start_char,
                            "end_char": chunk.end_char,
                            "char_count": len(chunk.content),
                            "embedding_provider": self.embedding_service.get_provider_name(),
                            "embedding_dimensions": self.embedding_service.get_dimensions(),
                            **categorization_metadata,
                        },
                    )
                    self.db.add(kb_chunk)

                print(
                    f"     ✓ Processed chunks {i+1}-{min(i+batch_size, len(text_chunks))}"
                )

            except Exception as e:
                print(f"     ✗ Error processing batch {i//batch_size + 1}: {e}")
                raise

        # Step 5: Commit all changes
        print("  5️⃣  Committing to database...")
        try:
            self.db.commit()
            print(f"     ✓ Successfully ingested {len(text_chunks)} chunks")
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Database commit failed: {e}") from e

        # Final summary
        print(f"✅ Ingestion complete! KB document ID: {kb_document.id}")

        if categorization_results:
            stats = self.categorizer.get_statistics(categorization_results)
            print(
                f"   Categorization: {stats['auto_approved']} auto-approved, "
                f"{stats['pending_review']} pending review "
                f"(auto-approval rate: {stats['auto_approval_rate']:.1f}%)"
            )

        return kb_document.id

    def get_pending_review_chunks(
        self, kb_document_id: Optional[int] = None, limit: int = 100
    ) -> list[KBChunk]:
        """Get chunks that need manual review.

        Args:
            kb_document_id: Filter by specific KB document (optional)
            limit: Maximum number of chunks to return

        Returns:
            List of KBChunk objects with review_status='pending_review'

        Example:
            >>> chunks = service.get_pending_review_chunks(kb_document_id=123)
            >>> print(f"Found {len(chunks)} chunks needing review")
        """
        query = self.db.query(KBChunk).filter(
            KBChunk.review_status == "pending_review"
        )

        if kb_document_id:
            query = query.filter(KBChunk.kb_document_id == kb_document_id)

        query = query.order_by(KBChunk.confidence_score.asc())  # Lowest confidence first
        query = query.limit(limit)

        return query.all()

    def approve_chunk(self, chunk_id: int, user_id: int) -> None:
        """Manually approve a chunk after review.

        Args:
            chunk_id: ID of the chunk to approve
            user_id: ID of the user performing the review

        Raises:
            ValueError: If chunk not found
        """
        chunk = self.db.query(KBChunk).filter(KBChunk.id == chunk_id).first()

        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found")

        chunk.review_status = "reviewed"
        chunk.reviewed_by = user_id
        chunk.chunk_metadata["manual_review_timestamp"] = (
            datetime.utcnow().isoformat()
        )

        self.db.commit()
        logger.info(f"Chunk {chunk_id} manually approved by user {user_id}")

    def get_categorization_statistics(
        self, kb_document_id: Optional[int] = None
    ) -> dict:
        """Get categorization statistics for KB documents.

        Args:
            kb_document_id: Filter by specific KB document (optional)

        Returns:
            Dictionary with categorization statistics

        Example:
            >>> stats = service.get_categorization_statistics(kb_document_id=123)
            >>> print(f"Auto-approval rate: {stats['auto_approval_rate']:.1f}%")
        """
        query = self.db.query(KBChunk)

        if kb_document_id:
            query = query.filter(KBChunk.kb_document_id == kb_document_id)

        all_chunks = query.all()

        if not all_chunks:
            return {
                "total_chunks": 0,
                "auto_approved": 0,
                "pending_review": 0,
                "manually_reviewed": 0,
                "auto_approval_rate": 0.0,
                "avg_confidence": 0.0,
                "chunk_type_distribution": {},
            }

        total = len(all_chunks)
        auto_approved = sum(
            1 for c in all_chunks if c.review_status == "auto_approved"
        )
        pending_review = sum(
            1 for c in all_chunks if c.review_status == "pending_review"
        )
        manually_reviewed = sum(1 for c in all_chunks if c.review_status == "reviewed")

        # Calculate average confidence (only for chunks with confidence scores)
        chunks_with_confidence = [
            c for c in all_chunks if c.confidence_score is not None
        ]
        avg_confidence = (
            sum(c.confidence_score for c in chunks_with_confidence)
            / len(chunks_with_confidence)
            if chunks_with_confidence
            else 0.0
        )

        # Type distribution
        type_distribution = {}
        for chunk in all_chunks:
            if chunk.chunk_type:
                type_distribution[chunk.chunk_type] = (
                    type_distribution.get(chunk.chunk_type, 0) + 1
                )

        return {
            "total_chunks": total,
            "auto_approved": auto_approved,
            "pending_review": pending_review,
            "manually_reviewed": manually_reviewed,
            "auto_approval_rate": (auto_approved / total) * 100 if total > 0 else 0.0,
            "avg_confidence": avg_confidence,
            "chunk_type_distribution": type_distribution,
        }
