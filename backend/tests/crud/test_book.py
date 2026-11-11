import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app.models import Book
from tests.utils.user import create_random_user


def test_book_defaults() -> None:
    before = datetime.now(UTC)
    book = Book.model_validate({"title": "Le Petit Prince", "owner_id": uuid.uuid4()})
    assert isinstance(book.id, uuid.UUID)
    assert book.author is None
    assert before <= book.created_at <= datetime.now(UTC)


@pytest.mark.parametrize(
    "values",
    [
        {"title": ""},
        {"title": "a" * 256},
        {"title": "Valid", "author": "a" * 256},
        {"title": "Valid", "created_at": None},
    ],
)
def test_book_validation(values: dict[str, str | None]) -> None:
    with pytest.raises(ValidationError):
        Book.model_validate({"owner_id": uuid.uuid4(), **values})


def test_book_requires_owner() -> None:
    with pytest.raises(ValidationError):
        Book.model_validate({"title": "Le Petit Prince"})


def test_user_books_relationship_and_cascade(db: Session) -> None:
    owner = create_random_user(db)
    other_owner = create_random_user(db)
    books = [
        Book(title="Le Petit Prince", author="Antoine de Saint-Exupéry", owner=owner),
        Book(title="L'Étranger", owner=owner),
    ]
    other_book = Book(title="Candide", owner=other_owner)
    db.add_all([*books, other_book])
    db.commit()
    db.refresh(owner)
    assert {book.id for book in owner.books} == {book.id for book in books}
    assert books[0].owner_id == owner.id
    assert books[0].owner is owner

    book_ids = [book.id for book in books]
    db.delete(owner)
    db.commit()
    db.expire_all()
    assert all(db.get(Book, book_id) is None for book_id in book_ids)
    assert db.get(Book, other_book.id) is not None
    db.delete(other_owner)
    db.commit()
