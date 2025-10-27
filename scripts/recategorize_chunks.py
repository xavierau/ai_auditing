"""
Re-categorize existing KB chunks using improved ChunkCategorizer with template support.

This script re-categorizes chunks that were previously classified as "general"
to properly identify templates, examples, requirements, etc.

Usage:
    python scripts/recategorize_chunks.py [options]

Options:
    --jurisdiction HK         Jurisdiction to re-categorize (default: HK)
    --page-range 87-120       Only re-categorize chunks in specific page range
    --batch-size 10           Number of chunks to process at once (default: 10)
    --dry-run                 Preview changes without updating database
    --force-all               Re-categorize ALL chunks (not just "general")
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Tuple
from sqlalchemy import create_engine, Integer, func
from sqlalchemy.orm import sessionmaker, Session
import dspy

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from genreport.core.database.models import KBChunk, KnowledgeBase
from genreport.core.retrieval.chunk_categorizer import ChunkCategorizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_chunks_to_recategorize(
    db: Session,
    jurisdiction: str,
    page_range: Tuple[int, int] = None,
    force_all: bool = False
) -> List[KBChunk]:
    """Get chunks that need re-categorization.

    Args:
        db: Database session
        jurisdiction: Jurisdiction code (e.g., 'HK')
        page_range: Optional (min_page, max_page) tuple to filter
        force_all: If True, re-categorize all chunks regardless of type

    Returns:
        List of KBChunk objects to re-categorize
    """
    query = db.query(KBChunk).filter(KBChunk.jurisdiction == jurisdiction)

    # Filter by chunk_type if not forcing all
    if not force_all:
        # Re-categorize only "general" chunks (likely miscategorized)
        query = query.filter(KBChunk.chunk_type == "general")

    # Filter by page range if specified
    if page_range:
        min_page, max_page = page_range
        query = query.filter(
            KBChunk.chunk_metadata['page_num'].astext.cast(Integer) >= min_page,
            KBChunk.chunk_metadata['page_num'].astext.cast(Integer) <= max_page
        )

    chunks = query.all()
    logger.info(f"Found {len(chunks)} chunks to re-categorize")

    return chunks


def recategorize_chunk(
    categorizer: ChunkCategorizer,
    chunk: KBChunk
) -> Tuple[str, float, str]:
    """Re-categorize a single chunk.

    Args:
        categorizer: ChunkCategorizer instance
        chunk: KB chunk to categorize

    Returns:
        Tuple of (new_chunk_type, confidence_score, reasoning)
    """
    try:
        # Get document title
        doc_title = chunk.kb_document.title if chunk.kb_document else "Unknown"

        # Get chunk index from metadata or use ID
        chunk_index = chunk.chunk_metadata.get('chunk_index', chunk.id)

        # Categorize using improved categorizer
        result = categorizer.categorize(
            chunk_content=chunk.content[:2000],  # Limit to 2000 chars
            kb_document_title=doc_title,
            chunk_index=chunk_index
        )

        return result.chunk_type, result.confidence_score, result.reasoning

    except Exception as e:
        logger.error(f"Failed to categorize chunk {chunk.id}: {e}")
        return "general", 0.0, f"Categorization failed: {str(e)}"


def main():
    """Main re-categorization function."""
    parser = argparse.ArgumentParser(
        description="Re-categorize KB chunks with improved categorizer"
    )
    parser.add_argument(
        "--jurisdiction",
        default="HK",
        help="Jurisdiction to re-categorize (default: HK)"
    )
    parser.add_argument(
        "--page-range",
        help="Page range to re-categorize (e.g., '87-120' for Appendix 2)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of chunks to process at once (default: 10)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating database"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Re-categorize ALL chunks (not just 'general')"
    )

    args = parser.parse_args()

    # Parse page range
    page_range = None
    if args.page_range:
        try:
            min_page, max_page = map(int, args.page_range.split('-'))
            page_range = (min_page, max_page)
            logger.info(f"Filtering to page range: {min_page}-{max_page}")
        except ValueError:
            logger.error(f"Invalid page range format: {args.page_range}. Use 'MIN-MAX'")
            sys.exit(1)

    # Load environment variables
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    load_dotenv(dotenv_path=env_path)

    DATABASE_URL = os.getenv("DATABASE_URL")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment")
        sys.exit(1)

    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not found in environment")
        sys.exit(1)

    # Initialize database
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Initialize DSPy with Gemini
        lm = dspy.LM('gemini/gemini-2.5-flash-lite', api_key=GOOGLE_API_KEY)
        dspy.configure(lm=lm)

        # Initialize categorizer with template support
        categorizer = ChunkCategorizer(lm=lm, auto_approve_threshold=0.85)
        logger.info("Initialized ChunkCategorizer with template support")

        # Get chunks to re-categorize
        chunks = get_chunks_to_recategorize(
            db,
            args.jurisdiction,
            page_range,
            args.force_all
        )

        if not chunks:
            logger.info("No chunks to re-categorize")
            return

        # Statistics
        stats = {
            "total": len(chunks),
            "updated": 0,
            "unchanged": 0,
            "failed": 0,
            "type_changes": {}
        }

        # Process chunks in batches
        logger.info(f"Starting re-categorization of {len(chunks)} chunks...")

        for i, chunk in enumerate(chunks, 1):
            try:
                old_type = chunk.chunk_type
                page_num = chunk.chunk_metadata.get('page_num', 'unknown')

                # Re-categorize
                new_type, confidence, reasoning = recategorize_chunk(categorizer, chunk)

                # Log the change
                if new_type != old_type:
                    logger.info(
                        f"[{i}/{len(chunks)}] Chunk {chunk.id} (page {page_num}): "
                        f"{old_type} → {new_type} (confidence: {confidence:.2f})"
                    )

                    # Track type changes
                    change_key = f"{old_type}→{new_type}"
                    stats["type_changes"][change_key] = stats["type_changes"].get(change_key, 0) + 1

                    # Update chunk if not dry-run
                    if not args.dry_run:
                        chunk.chunk_type = new_type
                        chunk.confidence_score = confidence
                        stats["updated"] += 1
                    else:
                        logger.info(f"  DRY RUN: Would update {chunk.id}")
                        stats["updated"] += 1
                else:
                    stats["unchanged"] += 1

                # Commit in batches
                if not args.dry_run and i % args.batch_size == 0:
                    db.commit()
                    logger.info(f"Committed batch of {args.batch_size} chunks")

            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.id}: {e}")
                stats["failed"] += 1

        # Final commit
        if not args.dry_run:
            db.commit()
            logger.info("✅ Final commit completed")

        # Print summary
        print("\n" + "="*80)
        print("RE-CATEGORIZATION SUMMARY")
        print("="*80)
        print(f"Total chunks processed: {stats['total']}")
        print(f"Updated: {stats['updated']}")
        print(f"Unchanged: {stats['unchanged']}")
        print(f"Failed: {stats['failed']}")

        if stats['type_changes']:
            print(f"\nType Changes:")
            for change, count in sorted(stats['type_changes'].items(), key=lambda x: -x[1]):
                print(f"  {change}: {count}")

        if args.dry_run:
            print("\n⚠️  DRY RUN MODE: No changes were saved to the database")
        else:
            print("\n✅ Changes saved to database")

        print("="*80)

    except Exception as e:
        logger.error(f"Re-categorization failed: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
