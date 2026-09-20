import uuid
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, TextChunk, TableChunk, ImageChunk, User, ChatHistory


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, filename: str, file_path: str, file_hash: str = "") -> Document:
        doc = Document(
            id=uuid.uuid4(),
            filename=filename,
            file_path=file_path,
            file_hash=file_hash,
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get(self, document_id: uuid.UUID) -> Optional[Document]:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, document_id: uuid.UUID, status: str, **kwargs):
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(status=status, **kwargs)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_stats(self, document_id: uuid.UUID) -> dict:
        text_count = await self.session.scalar(
            select(func.count(TextChunk.id)).where(
                TextChunk.document_id == document_id
            )
        )
        table_count = await self.session.scalar(
            select(func.count(TableChunk.id)).where(
                TableChunk.document_id == document_id
            )
        )
        image_count = await self.session.scalar(
            select(func.count(ImageChunk.id)).where(
                ImageChunk.document_id == document_id
            )
        )

        return {
            "text_chunks": text_count or 0,
            "table_chunks": table_count or 0,
            "images": image_count or 0,
        }

    async def delete(self, document_id: uuid.UUID) -> bool:
        from sqlalchemy import delete
        import os

        # Cascade delete chunks and history
        await self.session.execute(delete(TextChunk).where(TextChunk.document_id == document_id))
        await self.session.execute(delete(TableChunk).where(TableChunk.document_id == document_id))
        await self.session.execute(delete(ImageChunk).where(ImageChunk.document_id == document_id))
        await self.session.execute(delete(ChatHistory).where(ChatHistory.document_id == document_id))

        doc = await self.get(document_id)
        if doc and doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass

        stmt = delete(Document).where(Document.id == document_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return (result.rowcount or 0) > 0


class TextChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, chunks: list[dict]):
        objects = [TextChunk(**chunk) for chunk in chunks]
        self.session.add_all(objects)
        await self.session.commit()

    async def search_by_vector(
        self,
        embedding: list[float],
        document_id: uuid.UUID,
        top_k: int = 10,
    ) -> list[tuple[TextChunk, float]]:
        distance = TextChunk.embedding.cosine_distance(embedding)

        stmt = (
            select(
                TextChunk,
                distance.label("distance"),
            )
            .where(TextChunk.document_id == document_id)
            .where(TextChunk.embedding.isnot(None))
            .order_by(distance)
            .limit(top_k)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            (chunk, 1.0 - float(distance))
            for chunk, distance in rows
        ]

    async def get_all_for_document(self, document_id: uuid.UUID) -> list[TextChunk]:
        result = await self.session.execute(
            select(TextChunk).where(
                TextChunk.document_id == document_id
            )
        )
        return list(result.scalars().all())

    async def get_initial_chunks(self, document_id: uuid.UUID, limit: int = 5) -> list[TextChunk]:
        stmt = (
            select(TextChunk)
            .where(TextChunk.document_id == document_id)
            .order_by(TextChunk.page_number.asc(), TextChunk.id.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_pattern(
        self,
        document_id: uuid.UUID,
        pattern: str,
        limit: int = 5,
    ) -> list[TextChunk]:
        stmt = (
            select(TextChunk)
            .where(
                TextChunk.document_id == document_id,
                TextChunk.content.ilike(f"%{pattern}%"),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_neighbors(self, chunk_id: uuid.UUID, document_id: uuid.UUID) -> list[TextChunk]:
        result = await self.session.execute(
            select(TextChunk).where(TextChunk.id == chunk_id)
        )
        current_chunk = result.scalar_one_or_none()

        if not current_chunk:
            return []

        stmt = (
            select(TextChunk)
            .where(TextChunk.document_id == document_id)
            .where(
                TextChunk.page_number.between(
                    current_chunk.page_number - 1,
                    current_chunk.page_number + 1,
                )
            )
            .where(TextChunk.id != chunk_id)
            .order_by(TextChunk.page_number, TextChunk.id)
            .limit(4)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TableChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, chunks: list[dict]):
        objects = [TableChunk(**chunk) for chunk in chunks]
        self.session.add_all(objects)
        await self.session.commit()

    async def search_by_vector(
        self,
        embedding: list[float],
        document_id: uuid.UUID,
        top_k: int = 10,
    ) -> list[tuple[TableChunk, float]]:
        distance = TableChunk.embedding.cosine_distance(embedding)

        stmt = (
            select(
                TableChunk,
                distance.label("distance"),
            )
            .where(TableChunk.document_id == document_id)
            .where(TableChunk.embedding.isnot(None))
            .order_by(distance)
            .limit(top_k)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            (chunk, 1.0 - float(distance))
            for chunk, distance in rows
        ]

    async def get_all_for_document(self, document_id: uuid.UUID) -> list[TableChunk]:
        result = await self.session.execute(
            select(TableChunk).where(
                TableChunk.document_id == document_id
            )
        )
        return list(result.scalars().all())


class ImageChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, chunks: list[dict]):
        objects = [ImageChunk(**chunk) for chunk in chunks]
        self.session.add_all(objects)
        await self.session.commit()

    async def search_by_vector(
        self,
        embedding: list[float],
        document_id: uuid.UUID,
        top_k: int = 10,
    ) -> list[tuple[ImageChunk, float]]:
        distance = ImageChunk.image_embedding.cosine_distance(embedding)

        stmt = (
            select(
                ImageChunk,
                distance.label("distance"),
            )
            .where(ImageChunk.document_id == document_id)
            .where(ImageChunk.image_embedding.isnot(None))
            .order_by(distance)
            .limit(top_k)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            (chunk, 1.0 - float(distance))
            for chunk, distance in rows
        ]


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, email: str, hashed_password: str, salt: str) -> User:
        user = User(id=uuid.uuid4(), email=email.lower().strip(), hashed_password=hashed_password, salt=salt)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


class ChatHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        query: str,
        answer: str,
        citations: list[dict] = None,
        evidence: list[dict] = None,
    ) -> ChatHistory:
        history = ChatHistory(
            id=uuid.uuid4(),
            user_id=user_id,
            document_id=document_id,
            query=query,
            answer=answer,
            citations=citations or [],
            evidence=evidence or [],
        )
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def get_by_user(self, user_id: uuid.UUID, limit: int = 50) -> list[ChatHistory]:
        stmt = (
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, history_id: uuid.UUID) -> Optional[ChatHistory]:
        result = await self.session.execute(select(ChatHistory).where(ChatHistory.id == history_id))
        return result.scalar_one_or_none()

    async def clear_for_user(self, user_id: uuid.UUID) -> None:
        from sqlalchemy import delete
        stmt = delete(ChatHistory).where(ChatHistory.user_id == user_id)
        await self.session.execute(stmt)
        await self.session.commit()