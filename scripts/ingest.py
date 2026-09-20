import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_session_factory, init_db
from app.db.repositories import DocumentRepository
from app.ingestion.pipeline import ingest_document
from app.core.logging import setup_logging, get_logger


async def main():
    parser = argparse.ArgumentParser(description="Ingest a PDF into the RAG system")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    args = parser.parse_args()

    setup_logging()
    logger = get_logger("ingest")

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error("pdf_not_found", path=str(pdf_path))
        return

    await init_db()

    factory = get_session_factory()
    async with factory() as session:
        repo = DocumentRepository(session)
        doc = await repo.create(filename=pdf_path.name, file_path=str(pdf_path))
        logger.info("document_created", document_id=str(doc.id))

        result = await ingest_document(str(pdf_path), str(doc.id), session)
        logger.info("ingestion_result", **result)
        print(f"\nDocument ID: {doc.id}")
        print(f"Text chunks: {result['text_chunks']}")
        print(f"Table chunks: {result['table_chunks']}")
        print(f"Images: {result['images']}")


if __name__ == "__main__":
    asyncio.run(main())
