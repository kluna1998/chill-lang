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


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_book_invalid_uuid(client: TestClient, db: Session, method: str) -> None:
    owner = create_random_user(db)
    token = create_access_token(owner.id, timedelta(minutes=5))
    response = client.request(
        method,
        f"{settings.API_V1_STR}/books/not-a-uuid",
        headers={"Authorization": f"Bearer {token}"},
        **({"json": {"title": "Changed"}} if method == "patch" else {}),
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "book_id"]


def test_patch_book_partial_update(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    book = Book(title="Original", author="Author", owner=owner)
    db.add(book)
    db.commit()
    book_id = book.id
    created_at = book.created_at.isoformat()
    token = create_access_token(owner.id, timedelta(minutes=5))
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{settings.API_V1_STR}/books/{book_id}"

    response = client.patch(
        url,
        headers=headers,
        json={"title": "Updated", "owner_id": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == "Updated"
    assert content["author"] == "Author"
    assert content["owner_id"] == str(owner.id)
    assert content["id"] == str(book_id)
    assert datetime.fromisoformat(content["created_at"]) == datetime.fromisoformat(
        created_at
    )

    response = client.patch(url, headers=headers, json={"author": "New author"})
    assert response.status_code == 200
    assert response.json()["author"] == "New author"
    assert response.json()["title"] == "Updated"

    response = client.patch(url, headers=headers, json={"author": None})
    assert response.status_code == 200
    assert response.json()["author"] is None
    response = client.patch(url, headers=headers, json={})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    assert response.json()["author"] is None
    db.expire_all()
    persisted = db.get(Book, book_id)
    assert persisted is not None
    assert persisted.title == "Updated"
    assert persisted.author is None


@pytest.mark.parametrize(
    "payload",
    [{"title": None}, {"title": ""}, {"title": "a" * 256}, {"author": "a" * 256}],
)
def test_patch_book_validation(
    client: TestClient, db: Session, payload: dict[str, str | None]
) -> None:
    owner = create_random_user(db)
    book = Book(title="Original", author="Author", owner=owner)
    db.add(book)
    db.commit()
    token = create_access_token(owner.id, timedelta(minutes=5))
    response = client.patch(
        f"{settings.API_V1_STR}/books/{book.id}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 422
    db.refresh(book)
    assert book.title == "Original"
    assert book.author == "Author"


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize("is_superuser", [False, True])
def test_modify_book_hides_other_users_books(
    client: TestClient, db: Session, method: str, is_superuser: bool
) -> None:
    owner = create_random_user(db)
    other_user = create_random_user(db)
    other_user.is_superuser = is_superuser
    book = Book(title="Private", owner=owner)
    db.add_all([other_user, book])
    db.commit()
    book_id = book.id
    token = create_access_token(other_user.id, timedelta(minutes=5))
    for target_id in [book_id, uuid.uuid4()]:
        response = client.request(
            method,
            f"{settings.API_V1_STR}/books/{target_id}",
            headers={"Authorization": f"Bearer {token}"},
            **({"json": {"title": "Changed"}} if method == "patch" else {}),
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Book not found"}
    db.expire_all()
    persisted = db.get(Book, book_id)
    assert persisted is not None
    assert persisted.title == "Private"


def test_delete_book_owner(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    books = [Book(title="Delete", owner=owner), Book(title="Keep", owner=owner)]
    db.add_all(books)
    db.commit()
    book_id, kept_id = [book.id for book in books]
    token = create_access_token(owner.id, timedelta(minutes=5))
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{settings.API_V1_STR}/books/{book_id}"
    response = client.delete(url, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Book deleted successfully"}
    db.expire_all()
    assert db.get(Book, book_id) is None
    assert db.get(Book, kept_id) is not None
    assert client.get(url, headers=headers).status_code == 404
    assert client.delete(url, headers=headers).status_code == 404


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_modify_book_requires_authentication(client: TestClient, method: str) -> None:
    response = client.request(
        method,
        f"{settings.API_V1_STR}/books/{uuid.uuid4()}",
        **({"json": {"title": "Changed"}} if method == "patch" else {}),
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("skip", "-1"),
        ("skip", "abc"),
        ("skip", "1.5"),
        ("limit", "0"),
        ("limit", "-1"),
        ("limit", "101"),
        ("limit", "abc"),
        ("limit", "1.5"),
    ],
)
def test_read_books_invalid_pagination(
    client: TestClient, db: Session, parameter: str, value: str
) -> None:
    owner = create_random_user(db)
    token = create_access_token(owner.id, timedelta(minutes=5))
    response = client.get(
        f"{settings.API_V1_STR}/books/",
        headers={"Authorization": f"Bearer {token}"},
        params={parameter: value},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", parameter]


@pytest.mark.parametrize("limit", [1, 100])
def test_read_books_pagination_boundaries(
    client: TestClient, db: Session, limit: int
) -> None:
    owner = create_random_user(db)
    now = datetime.now(UTC)
    books = [
        Book(title=str(index), owner=owner, created_at=now + timedelta(seconds=index))
        for index in range(101)
    ]
    db.add_all(books)
    db.commit()
    token = create_access_token(owner.id, timedelta(minutes=5))
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{settings.API_V1_STR}/books/"
    response = client.get(url, headers=headers, params={"skip": 0, "limit": limit})
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 101
    assert [book["id"] for book in content["data"]] == [
        str(book.id) for book in reversed(books[-limit:])
    ]

    response = client.get(url, headers=headers, params={"skip": 101, "limit": limit})
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 101}
