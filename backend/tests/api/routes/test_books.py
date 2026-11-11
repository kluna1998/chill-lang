import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models import Book
from tests.utils.user import create_random_user


@pytest.mark.parametrize("is_superuser", [False, True])
def test_read_books_personal_library(
    client: TestClient, db: Session, is_superuser: bool
) -> None:
    owner = create_random_user(db)
    owner.is_superuser = is_superuser
    other_owner = create_random_user(db)
    db.add(owner)
    now = datetime.now(UTC)
    books = [
        Book(title="Older", owner_id=owner.id, created_at=now - timedelta(days=1)),
        Book(title="Newer", author="Author", owner_id=owner.id, created_at=now),
        Book(title="Private", owner_id=other_owner.id, created_at=now),
    ]
    db.add_all(books)
    db.commit()
    headers = {
        "Authorization": f"Bearer {create_access_token(owner.id, timedelta(minutes=5))}"
    }
    url = f"{settings.API_V1_STR}/books/"

    response = client.get(url, headers=headers)
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 2
    assert [book["id"] for book in content["data"]] == [
        str(books[1].id),
        str(books[0].id),
    ]
    assert all(book["owner_id"] == str(owner.id) for book in content["data"])
    assert content["data"][0]["author"] == "Author"

    response = client.get(
        url,
        headers=headers,
        params={"skip": 1, "limit": 1, "owner_id": str(other_owner.id)},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert [book["id"] for book in response.json()["data"]] == [str(books[0].id)]

    response = client.get(url, headers=headers, params={"skip": 2})
    assert response.json() == {"data": [], "count": 2}


def test_read_books_empty(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    token = create_access_token(owner.id, timedelta(minutes=5))
    response = client.get(
        f"{settings.API_V1_STR}/books/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


def test_read_books_requires_authentication(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/books/")
    assert response.status_code == 401


def test_get_book_owner(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    book = Book(title="Le Petit Prince", author="Antoine de Saint-Exupéry", owner=owner)
    db.add(book)
    db.commit()
    token = create_access_token(owner.id, timedelta(minutes=5))

    response = client.get(
        f"{settings.API_V1_STR}/books/{book.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(book.id)
    assert content["owner_id"] == str(owner.id)
    assert content["title"] == book.title
    assert content["author"] == book.author
    assert "created_at" in content
    assert "owner" not in content


@pytest.mark.parametrize("is_superuser", [False, True])
def test_get_book_hides_other_users_books(
    client: TestClient, db: Session, is_superuser: bool
) -> None:
    owner = create_random_user(db)
    other_user = create_random_user(db)
    other_user.is_superuser = is_superuser
    book = Book(title="Private book", owner=owner)
    db.add_all([other_user, book])
    db.commit()
    token = create_access_token(other_user.id, timedelta(minutes=5))
    headers = {"Authorization": f"Bearer {token}"}

    private_response = client.get(
        f"{settings.API_V1_STR}/books/{book.id}", headers=headers
    )
    missing_response = client.get(
        f"{settings.API_V1_STR}/books/{uuid.uuid4()}", headers=headers
    )
    assert private_response.status_code == missing_response.status_code == 404
    assert (
        private_response.json()
        == missing_response.json()
        == {"detail": "Book not found"}
    )


def test_get_book_requires_authentication(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/books/{uuid.uuid4()}")
    assert response.status_code == 401


def test_get_book_invalid_uuid(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    token = create_access_token(owner.id, timedelta(minutes=5))
    response = client.get(
        f"{settings.API_V1_STR}/books/not-a-uuid",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
