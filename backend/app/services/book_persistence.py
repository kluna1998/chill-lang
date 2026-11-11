"""Book persistence and shared ownership checks for books and chapters."""

import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

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


def get_owned_book(session: Session, book_id: uuid.UUID, owner_id: uuid.UUID) -> Book:
    statement = select(Book).where(Book.id == book_id, Book.owner_id == owner_id)
    book = session.exec(statement).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


def get_owned_chapter(
    session: Session, book_id: uuid.UUID, chapter_id: uuid.UUID, owner_id: uuid.UUID
) -> Chapter:
    get_owned_book(session, book_id, owner_id)
    chapter = session.exec(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.book_id == book_id)
    ).first()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
