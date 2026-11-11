import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile
from sqlmodel import Session, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Book,
    BookCreate,
    BookPublic,
    BooksPublic,
    BookUpdate,
    Chapter,
    ChapterCreate,
    ChapterPublic,
    ChaptersPublic,
    ChapterSummary,
    ChapterUpdate,
    Message,
)
from app.services.book_import import MAX_TXT_BYTES, BookImportError, parse_txt_book

router = APIRouter(prefix="/books", tags=["books"])


def _get_owned_book(session: Session, book_id: uuid.UUID, owner_id: uuid.UUID) -> Book:
    statement = select(Book).where(Book.id == book_id, Book.owner_id == owner_id)
    book = session.exec(statement).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


def _get_owned_chapter(
    session: Session, book_id: uuid.UUID, chapter_id: uuid.UUID, owner_id: uuid.UUID
) -> Chapter:
    _get_owned_book(session, book_id, owner_id)
    chapter = session.exec(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.book_id == book_id)
    ).first()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.post("/", response_model=BookPublic, status_code=201)
def create_book(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_in: BookCreate,
) -> Book:
    book = Book.model_validate(
        book_in,
        update={"owner_id": current_user.id},
    )

    session.add(book)
    session.commit()
    session.refresh(book)

    return book


@router.get("/", response_model=BooksPublic)
def read_books(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> BooksPublic:
    count_statement = (
        select(func.count()).select_from(Book).where(Book.owner_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Book)
        .where(Book.owner_id == current_user.id)
        .order_by(col(Book.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    books = session.exec(statement).all()
    return BooksPublic(
        data=[BookPublic.model_validate(book) for book in books],
        count=count,
    )


@router.post("/import-txt", response_model=BookPublic, status_code=201)
def import_txt_book(
    *, session: SessionDep, current_user: CurrentUser, file: UploadFile
) -> BookPublic:
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=422, detail="Selecciona un archivo con extensión .txt."
        )
    data = file.file.read(MAX_TXT_BYTES + 1)
    if len(data) > MAX_TXT_BYTES:
        raise HTTPException(
            status_code=413, detail="El archivo supera el límite de 5 MiB."
        )
    try:
        parsed = parse_txt_book(data)
    except BookImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    book = Book.model_validate(parsed.book, update={"owner_id": current_user.id})
    book.chapters = [
        Chapter.model_validate(chapter, update={"book_id": book.id})
        for chapter in parsed.chapters
    ]
    try:
        session.add(book)
        session.flush()
        result = BookPublic.model_validate(book)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return result


@router.get("/{book_id}", response_model=BookPublic)
def get_book(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
) -> Book:
    return _get_owned_book(session, book_id, current_user.id)


@router.patch("/{book_id}", response_model=BookPublic)
def update_book(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
    book_in: BookUpdate,
) -> Book:
    book = _get_owned_book(session, book_id, current_user.id)
    book.sqlmodel_update(book_in.model_dump(exclude_unset=True))
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@router.delete("/{book_id}", response_model=Message)
def delete_book(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
) -> Message:
    book = _get_owned_book(session, book_id, current_user.id)
    session.delete(book)
    session.commit()
    return Message(message="Book deleted successfully")


@router.post("/{book_id}/chapters", response_model=ChapterPublic, status_code=201)
def create_chapter(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
    chapter_in: ChapterCreate,
) -> Chapter:
    book = _get_owned_book(session, book_id, current_user.id)
    chapter = Chapter.model_validate(chapter_in, update={"book_id": book.id})
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


@router.get("/{book_id}/chapters", response_model=ChaptersPublic)
def read_chapters(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> ChaptersPublic:
    _get_owned_book(session, book_id, current_user.id)
    count = session.exec(
        select(func.count()).select_from(Chapter).where(Chapter.book_id == book_id)
    ).one()
    chapters = session.exec(
        select(Chapter.id, Chapter.book_id, Chapter.title, Chapter.position)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.position, Chapter.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return ChaptersPublic(
        data=[ChapterSummary.model_validate(chapter._mapping) for chapter in chapters],
        count=count,
    )


@router.get("/{book_id}/chapters/{chapter_id}", response_model=ChapterPublic)
def get_chapter(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
    chapter_id: uuid.UUID,
) -> Chapter:
    return _get_owned_chapter(session, book_id, chapter_id, current_user.id)


@router.patch("/{book_id}/chapters/{chapter_id}", response_model=ChapterPublic)
def update_chapter(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
    chapter_id: uuid.UUID,
    chapter_in: ChapterUpdate,
) -> Chapter:
    chapter = _get_owned_chapter(session, book_id, chapter_id, current_user.id)
    chapter.sqlmodel_update(chapter_in.model_dump(exclude_unset=True))
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


@router.delete("/{book_id}/chapters/{chapter_id}", response_model=Message)
def delete_chapter(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
    chapter_id: uuid.UUID,
) -> Message:
    chapter = _get_owned_chapter(session, book_id, chapter_id, current_user.id)
    session.delete(chapter)
    session.commit()
    return Message(message="Chapter deleted successfully")
