"""Test script for KB ingestion with real SME-FRS document."""

from pathlib import Path

from genreport.core.database.base import SessionLocal
from genreport.core.retrieval.kb_ingestion_service import KBIngestionService


def test_sme_frs_ingestion():
    """Test ingestion of SME-FRS document."""
    # Path to the real SME-FRS PDF
    pdf_path = Path("genreport/markets/hk/knowledge_base/docs/smefrf1221.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    # Create database session
    db = SessionLocal()

    try:
        # Create ingestion service
        ingestion_service = KBIngestionService(db)

        # Ingest the document
        kb_id = ingestion_service.ingest_pdf(
            pdf_path=pdf_path,
            title="SME-FRF & SME-FRS (Revised September 2022/March 2025)",
            jurisdiction="HK",
            standard="SME-FRS",
            document_type="standard",
            tenant_id=None,  # Shared standard, available to all tenants
        )

        print(f"\n🎉 Success! KB document ID: {kb_id}")

    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("KB Ingestion Test - SME-FRS Document")
    print("=" * 60)
    print()

    test_sme_frs_ingestion()
