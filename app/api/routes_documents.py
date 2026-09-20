import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories import DocumentRepository
from app.schemas.document import DocumentUploadResponse, DocumentStatusResponse, DocumentStatus
from app.core.config import get_settings
from app.core.security import validate_file, compute_file_hash
from app.ingestion.pipeline import ingest_document
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), session: AsyncSession = Depends(get_db)):
    is_valid, msg = validate_file(file.filename, file.size or 0)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    settings = get_settings()
    doc_id = str(uuid.uuid4())
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{doc_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    repo = DocumentRepository(session)
    doc = await repo.create(filename=file.filename, file_path=str(file_path))

    # run ingestion in background-ish (for now synchronous, can be moved to task queue)
    try:
        await ingest_document(str(file_path), str(doc.id), session)
    except Exception as e:
        logger.error("upload_ingestion_failed", error=str(e))

    return DocumentUploadResponse(document_id=str(doc.id), filename=file.filename, status=DocumentStatus.PROCESSING)


@router.get("/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str, session: AsyncSession = Depends(get_db)):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    repo = DocumentRepository(session)
    doc = await repo.get(doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    stats = await repo.get_stats(doc_uuid)

    return DocumentStatusResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        status=DocumentStatus(doc.status),
        total_pages=doc.page_count,
        text_chunks=stats["text_chunks"],
        table_chunks=stats["table_chunks"],
        images=stats["images"],
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str, session: AsyncSession = Depends(get_db)):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    repo = DocumentRepository(session)
    deleted = await repo.delete(doc_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted", "document_id": document_id}
