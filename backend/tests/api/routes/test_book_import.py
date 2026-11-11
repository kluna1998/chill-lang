from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.security import create_access_token
from app.models import Book, Chapter
from app.services.book_import import MAX_TXT_BYTES
from tests.utils.user import create_random_user

TXT = "TITLE: Une aventure à Paris\nAUTHOR: Chill-Lang\n\n=== CHAPTER: Le départ ===\n\nBonjour !\n\n=== CHAPTER: La rencontre ===\nSalut !\n".encode()
URL = f"{settings.API_V1_STR}/books/import-txt"


def _headers(db: Session) -> dict[str, str]:
    user = create_random_user(db)
    return {
        "Authorization": f"Bearer {create_access_token(user.id, timedelta(minutes=5))}"
    }


def test_import_book_and_read_chapters(client: TestClient, db: Session) -> None:
    headers = _headers(db)
    other_headers = _headers(db)
    response = client.post(
        URL, headers=headers, files={"file": ("book.TXT", TXT, "text/plain")}
    )
    assert response.status_code == 201
    book = response.json()
    assert book["title"] == "Une aventure à Paris"
    assert book["author"] == "Chill-Lang"
    url = f"{settings.API_V1_STR}/books/{book['id']}"
    index = client.get(f"{url}/chapters", headers=headers)
    assert index.status_code == 200
    assert index.json()["count"] == 2
    assert [chapter["position"] for chapter in index.json()["data"]] == [1, 2]
    chapter_id = index.json()["data"][0]["id"]
    chapter = client.get(f"{url}/chapters/{chapter_id}", headers=headers)
    assert chapter.json()["content"] == "\nBonjour !\n\n"
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.get(f"{url}/chapters", headers=other_headers).status_code == 404


@pytest.mark.parametrize(
    "filename,data,status",
    [
        ("book.pdf", TXT, 422),
        ("book.txt", b"", 422),
        ("book.txt", b"\xff", 422),
        ("book.txt", b"TITLE: Bad", 422),
        ("book.txt", b"a" * (MAX_TXT_BYTES + 1), 413),
    ],
)
def test_invalid_upload_does_not_create_records(
    client: TestClient, db: Session, filename: str, data: bytes, status: int
) -> None:
    headers = _headers(db)
    before = db.exec(select(func.count()).select_from(Book)).one()
    response = client.post(
        URL, headers=headers, files={"file": (filename, data, "text/plain")}
    )
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)
    assert db.exec(select(func.count()).select_from(Book)).one() == before


def test_import_requires_authentication(client: TestClient) -> None:
    assert client.post(URL, files={"file": ("book.txt", TXT)}).status_code == 401


def test_import_requires_file(client: TestClient, db: Session) -> None:
    assert client.post(URL, headers=_headers(db)).status_code == 422


def test_import_rolls_back_all_records(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(db)
    books_before = db.exec(select(func.count()).select_from(Book)).one()
    chapters_before = db.exec(select(func.count()).select_from(Chapter)).one()

    def fail_commit() -> None:
        raise SQLAlchemyError("Simulated failure after flush")

    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", fail_commit)
        with pytest.raises(SQLAlchemyError):
            client.post(URL, headers=headers, files={"file": ("book.txt", TXT)})
    assert db.exec(select(func.count()).select_from(Book)).one() == books_before
    assert db.exec(select(func.count()).select_from(Chapter)).one() == chapters_before
