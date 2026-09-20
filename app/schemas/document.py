from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid


class ElementType(str, Enum):
    TEXT = "text"
    HEADING = "heading"
    TABLE = "table"
    IMAGE = "image"
    CAPTION = "caption"
    LIST = "list"


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ParsedElement(BaseModel):
    element_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    element_type: ElementType
    section: str = ""
    content: str = ""
    bbox: list[float] = Field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class TextChunkSchema(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    section: str = ""
    parent_section: str = ""
    content: str
    chunk_type: str = "text"
    metadata: dict = Field(default_factory=dict)


class TableChunkSchema(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    section: str = ""
    table_content: str
    table_data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class ImageChunkSchema(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    section: str = ""
    caption: str = ""
    image_path: str = ""
    image_width: int = 0
    image_height: int = 0
    metadata: dict = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus


class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    total_pages: int = 0
    text_chunks: int = 0
    table_chunks: int = 0
    images: int = 0
