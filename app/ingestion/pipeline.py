import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.parser import parse_pdf
from app.ingestion.normalizer import normalize_elements
from app.ingestion.chunker import chunk_elements
from app.ingestion.table_processor import (
    parse_markdown_table,
    table_to_text_representation,
)
from app.ingestion.image_processor import (
    extract_and_save_images,
)

from app.embeddings.text_embeddings import embed_texts
from app.embeddings.image_embeddings import embed_image

from app.db.repositories import (
    DocumentRepository,
    TextChunkRepository,
    TableChunkRepository,
    ImageChunkRepository,
)

from app.core.security import compute_file_hash
from app.core.logging import get_logger


logger = get_logger(__name__)


async def ingest_document(
    pdf_path: str,
    document_id: str,
    session: AsyncSession,
) -> dict:

    doc_repo = DocumentRepository(session)
    text_repo = TextChunkRepository(session)
    table_repo = TableChunkRepository(session)
    image_repo = ImageChunkRepository(session)

    doc_uuid = uuid.UUID(document_id)

    try:

        await doc_repo.update_status(
            doc_uuid,
            "PROCESSING",
        )

        logger.info(
            "ingestion_started",
            document_id=document_id,
        )


        parsed_data = parse_pdf(pdf_path)

        file_hash = compute_file_hash(
            pdf_path
        )

        await doc_repo.update_status(
            doc_uuid,
            "PROCESSING",
            page_count=parsed_data["page_count"],
            file_hash=file_hash,
        )


        elements = normalize_elements(
            document_id,
            parsed_data,
        )


        text_chunks, table_chunks = chunk_elements(
            elements,
            document_id,
        )


        for table_chunk in table_chunks:

            table_data = parse_markdown_table(
                table_chunk.table_content
            )

            table_chunk.table_data = table_data

            table_chunk.metadata[
                "text_representation"
            ] = table_to_text_representation(
                table_data,
                table_chunk.section,
                table_chunk.page_number,
            )


        image_chunks = extract_and_save_images(
            document_id,
            parsed_data,
            elements,
        )


        logger.info(
            "generating_text_embeddings",
            count=len(text_chunks),
        )

        text_contents = [
            chunk.content
            for chunk in text_chunks
        ]

        text_embeddings = (
            embed_texts(text_contents)
            if text_contents
            else []
        )


        table_texts = [
            chunk.metadata.get(
                "text_representation",
                chunk.table_content,
            )
            for chunk in table_chunks
        ]

        table_embeddings = (
            embed_texts(table_texts)
            if table_texts
            else []
        )

        logger.info(
            "generating_image_embeddings",
            count=len(image_chunks),
        )

        image_embeddings = []

        for image_chunk in image_chunks:

            try:

                embedding = embed_image(
                    image_chunk.image_path
                )

                image_embeddings.append(
                    embedding
                )

            except Exception as exc:

                logger.warning(
                    "image_embedding_failed",
                    path=image_chunk.image_path,
                    error=str(exc),
                )

                image_embeddings.append(None)

        text_records = []

        for index, chunk in enumerate(
            text_chunks
        ):

            text_records.append(
                {
                    "id": uuid.UUID(
                        chunk.chunk_id
                    ),
                    "document_id": doc_uuid,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "parent_section": chunk.parent_section,
                    "content": chunk.content,
                    "chunk_type": chunk.chunk_type,
                    "embedding": (
                        text_embeddings[index]
                        if index < len(text_embeddings)
                        else None
                    ),
                    "metadata_": chunk.metadata,
                }
            )

        table_records = []

        for index, chunk in enumerate(
            table_chunks
        ):

            table_records.append(
                {
                    "id": uuid.UUID(
                        chunk.chunk_id
                    ),
                    "document_id": doc_uuid,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "table_content": chunk.table_content,
                    "table_data": chunk.table_data,
                    "embedding": (
                        table_embeddings[index]
                        if index < len(table_embeddings)
                        else None
                    ),
                    "metadata_": chunk.metadata,
                }
            )

        image_records = []

        for index, chunk in enumerate(
            image_chunks
        ):

            image_records.append(
                {
                    "id": uuid.UUID(
                        chunk.chunk_id
                    ),
                    "document_id": doc_uuid,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "caption": chunk.caption,
                    "image_path": chunk.image_path,
                    "image_width": chunk.image_width,
                    "image_height": chunk.image_height,
                    "image_embedding": (
                        image_embeddings[index]
                        if index < len(image_embeddings)
                        else None
                    ),
                    "metadata_": chunk.metadata,
                }
            )

        if text_records:
            await text_repo.bulk_insert(
                text_records
            )

        if table_records:
            await table_repo.bulk_insert(
                table_records
            )

        if image_records:
            await image_repo.bulk_insert(
                image_records
            )

        # --------------------------------------------------
        # 13. Complete
        # --------------------------------------------------

        await doc_repo.update_status(
            doc_uuid,
            "COMPLETED",
        )

        result = {
            "document_id": document_id,
            "status": "COMPLETED",
            "text_chunks": len(text_records),
            "table_chunks": len(table_records),
            "images": len(image_records),
        }

        logger.info(
            "ingestion_completed",
            **result,
        )

        return result

    except Exception as exc:

        logger.error(
            "ingestion_failed",
            document_id=document_id,
            error=str(exc),
        )

        try:
            await doc_repo.update_status(
                doc_uuid,
                "FAILED",
            )
        except Exception:
            pass

        raise