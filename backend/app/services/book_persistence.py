"""Atomic persistence shared by the TXT and EPUB import endpoints."""

import uuid

from sqlmodel import Session

from app.models import Book, BookPublic, Chapter
from app.services.book_import import ParsedBook


def persist_imported_book(
    session: Session, owner_id: uuid.UUID, parsed: ParsedBook
) -> BookPublic:
    try:
        book = Book.model_validate(parsed.book, update={"owner_id": owner_id})
        book.chapters = [
            Chapter.model_validate(chapter, update={"book_id": book.id})
            for chapter in parsed.chapters
        ]
        session.add(book)
        session.flush()
        result = BookPublic.model_validate(book)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
