import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Book, BookCreate, BookPublic, BooksPublic

router = APIRouter(prefix="/books", tags=["books"])


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
    skip: int = 0,
    limit: int = 100,
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


@router.get("/{book_id}", response_model=BookPublic)
def get_book(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
) -> Book:
    statement = select(Book).where(
        Book.id == book_id,
        Book.owner_id == current_user.id,
    )
    book = session.exec(statement).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
