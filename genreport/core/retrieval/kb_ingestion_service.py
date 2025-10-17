"""KB ingestion service - orchestrates PDF processing and storage.

Coordinates PDF extraction, chunking, embedding, and database storage.
"""

from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from genreport.core.database.models import KnowledgeBase, KBChunk
from genreport.core.parsing.pdf_extractor import PDFExtractor
from genreport.core.parsing.chunking_service import ChunkingService
from genreport.core.retrieval.embedding_service import EmbeddingService


class KBIngestionService:
    """Service for ingesting PDF documents into the knowledge base."""

    def __init__(self, db: Session):
        """Initialize ingestion service.

        Args:
            db: Database session
        """
        self.db = db
        self.pdf_extractor = PDFExtractor()
        self.chunker = ChunkingService(chunk_size=1000, chunk_overlap=200)
        self.embedding_service = EmbeddingService()

    def ingest_pdf(
        self,
        pdf_path: str | Path,
        title: str,
        jurisdiction: str,
        standard: Optional[str] = None,
        document_type: str = "standard",
        tenant_id: Optional[UUID] = None,
    ) -> int:
        """Ingest a PDF document into the knowledge base.

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
            },
        )

        self.db.add(kb_document)
        self.db.flush()  # Get ID without committing
        print(f"     ✓ Created KB document (ID: {kb_document.id})")

        # Step 3: Chunk the text
        print("  3️⃣  Chunking text...")
        text_chunks = self.chunker.chunk_text(full_text)
        print(f"     ✓ Created {len(text_chunks)} chunks")

        # Step 4: Generate embeddings and store chunks
        print("  4️⃣  Generating embeddings and storing chunks...")
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
                for chunk, embedding in zip(batch, embeddings):
                    kb_chunk = KBChunk(
                        tenant_id=tenant_id,
                        jurisdiction=jurisdiction,
                        kb_document_id=kb_document.id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        embedding=embedding,
                        embedding_model=self.embedding_service.get_model_name(),
                        review_status="auto_approved",  # Simple auto-approval for now
                        confidence_score=1.0,
                        chunk_metadata={
                            "start_char": chunk.start_char,
                            "end_char": chunk.end_char,
                            "char_count": len(chunk.content),
                            "embedding_provider": self.embedding_service.get_provider_name(),
                            "embedding_dimensions": self.embedding_service.get_dimensions(),
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

        print(f"✅ Ingestion complete! KB document ID: {kb_document.id}")
        return kb_document.id
