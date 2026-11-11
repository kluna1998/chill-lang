"""Owned vocabulary snapshots and versioned reading positions; no AI calls."""

import hashlib
import uuid

from fastapi import HTTPException
from sqlalchemy import Update, update
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlmodel import Session, col, func, select

from app.models import (
    Book,
    Chapter,
    ReadingProgress,
    ReadingProgressUpdate,
    VocabularyCreate,
    VocabularyEntry,
    VocabularyPublic,
    VocabularyPublicList,
    get_datetime_utc,
)
from app.services.book_persistence import get_owned_book, get_owned_chapter
from app.services.french_nlp import InvalidSelection, utf16_to_python


def save_vocabulary(
    session: Session, owner_id: uuid.UUID, data: VocabularyCreate
) -> VocabularyEntry:
    chapter = session.exec(
        select(Chapter)
        .join(Book)
        .where(
            Chapter.id == data.chapter_id,
            Book.owner_id == owner_id,
        )
    ).first()
    if chapter is None:
        raise HTTPException(404, "Chapter not found")
    try:
        first, last = utf16_to_python(
            chapter.content, data.start_offset, data.end_offset
        )
        if chapter.content[first:last] != data.original_text:
            raise ValueError("El texto del capítulo ha cambiado.")
        if not (
            0
            <= data.context_start_offset
            <= data.start_offset
            < data.end_offset
            <= data.context_end_offset
        ):
            raise ValueError("Contexto inválido.")
        encoded = chapter.content.encode("utf-16-le")
        if (
            data.context_end_offset * 2 > len(encoded)
            or data.context_end_offset - data.context_start_offset > 2000
        ):
            raise ValueError("Contexto fuera de límites.")
        context = encoded[
            data.context_start_offset * 2 : data.context_end_offset * 2
        ].decode("utf-16-le")
        if context != data.context:
            raise ValueError("El contexto del capítulo ha cambiado.")
    except (InvalidSelection, ValueError) as exc:
        raise HTTPException(422, str(exc)) from None
    entry = VocabularyEntry(
        **data.model_dump(exclude={"offset_unit", "context"}),
        owner_id=owner_id,
        book_id=chapter.book_id,
        context=context,
    )
    # PostgreSQL enforces idempotence even for concurrent double clicks.
    session.connection().execute(
        insert(VocabularyEntry)
        .values(entry.model_dump())
        .on_conflict_do_nothing(
            index_elements=["owner_id", "chapter_id", "start_offset", "end_offset"],
        )
    )
    saved = session.exec(
        select(VocabularyEntry).where(
            VocabularyEntry.owner_id == owner_id,
            VocabularyEntry.chapter_id == chapter.id,
            VocabularyEntry.start_offset == data.start_offset,
            VocabularyEntry.end_offset == data.end_offset,
        )
    ).one()
    session.commit()
    return saved


def list_vocabulary(
    session: Session, owner_id: uuid.UUID, skip: int, limit: int
) -> VocabularyPublicList:
    count = session.exec(
        select(func.count())
        .select_from(VocabularyEntry)
        .where(VocabularyEntry.owner_id == owner_id)
    ).one()
    entries = session.exec(
        select(VocabularyEntry)
        .where(VocabularyEntry.owner_id == owner_id)
        .order_by(col(VocabularyEntry.created_at).desc(), col(VocabularyEntry.id))
        .offset(skip)
        .limit(limit)
    ).all()
    return VocabularyPublicList(
        data=[VocabularyPublic.model_validate(entry) for entry in entries], count=count
    )


def delete_vocabulary(
    session: Session, owner_id: uuid.UUID, entry_id: uuid.UUID
) -> None:
    entry = session.exec(
        select(VocabularyEntry).where(
            VocabularyEntry.id == entry_id, VocabularyEntry.owner_id == owner_id
        )
    ).first()
    if entry is None:
        raise HTTPException(404, "Vocabulary entry not found")
    session.delete(entry)
    session.commit()


def get_progress(
    session: Session, owner_id: uuid.UUID, book_id: uuid.UUID
) -> ReadingProgress | None:
    get_owned_book(session, book_id, owner_id)
    return session.exec(
        select(ReadingProgress).where(
            ReadingProgress.owner_id == owner_id, ReadingProgress.book_id == book_id
        )
    ).first()


def save_progress(
    session: Session,
    owner_id: uuid.UUID,
    book_id: uuid.UUID,
    data: ReadingProgressUpdate,
) -> ReadingProgress:
    chapter = get_owned_chapter(session, book_id, data.chapter_id, owner_id)
    if hashlib.sha256(chapter.content.encode()).hexdigest() != data.content_hash:
        raise HTTPException(
            409, "El contenido del capítulo ha cambiado. Recarga antes de guardar."
        )
    encoded = chapter.content.encode("utf-16-le")
    try:
        if data.position * 2 > len(encoded):
            raise ValueError()
        encoded[: data.position * 2].decode("utf-16-le")
    except ValueError:
        raise HTTPException(422, "Posición UTF-16 inválida.") from None
    progress = ReadingProgress(
        owner_id=owner_id,
        book_id=book_id,
        chapter_id=data.chapter_id,
        position=data.position,
        content_hash=data.content_hash,
    )
    statement: Insert | Update
    if data.expected_version == 0:
        statement = (
            insert(ReadingProgress)
            .values(progress.model_dump())
            .on_conflict_do_nothing(index_elements=["owner_id", "book_id"])
        )
    else:
        statement = (
            update(ReadingProgress)
            .where(
                col(ReadingProgress.owner_id) == owner_id,
                col(ReadingProgress.book_id) == book_id,
                col(ReadingProgress.version) == data.expected_version,
            )
            .values(
                chapter_id=data.chapter_id,
                position=data.position,
                content_hash=data.content_hash,
                version=data.expected_version + 1,
                updated_at=get_datetime_utc(),
            )
        )
    result = (
        session.connection()
        .execute(statement.returning(col(ReadingProgress.id)))
        .first()
    )
    if result is None:
        session.rollback()
        raise HTTPException(
            409, "El progreso se actualizó desde otra lectura. Recarga para continuar."
        )
    session.commit()
    session.expire_all()
    return session.exec(
        select(ReadingProgress).where(ReadingProgress.id == result[0])
    ).one()
