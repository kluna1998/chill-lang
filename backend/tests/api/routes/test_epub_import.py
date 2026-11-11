import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, func, select

from app.core.config import settings
from app.models import Book, Chapter
from app.services.epub_import import MAX_EPUB_BYTES
from tests.api.routes.test_book_import import _headers
from tests.utils.epub import make_epub

URL = f"{settings.API_V1_STR}/books/import-epub"


def test_epub_import_is_readable_and_private(client: TestClient, db: Session) -> None:
    headers, other = _headers(db), _headers(db)
    response = client.post(
        URL,
        headers=headers,
        files={"file": ("livre.EPUB", make_epub(), "application/epub+zip")},
    )
    assert response.status_code == 201
    book = response.json()
    assert book["title"] == "Une aventure à Paris"
    assert book["author"] == "Chill-Lang"
    url = f"{settings.API_V1_STR}/books/{book['id']}"
    index = client.get(f"{url}/chapters", headers=headers)
    assert index.status_code == 200
    assert index.json()["count"] == 2
    first = index.json()["data"][0]
    assert first["position"] == 1
    assert "content" not in first
    chapter = client.get(f"{url}/chapters/{first['id']}", headers=headers)
    assert chapter.status_code == 200
    assert "Camille se réveille." in chapter.json()["content"]
    assert client.get(url, headers=other).status_code == 404
    assert client.get(f"{url}/chapters", headers=other).status_code == 404


@pytest.mark.parametrize(
    "filename,data,status",
    [
        ("book.pdf", b"bad", 422),
        ("book.epub", b"bad", 422),
        ("book.epub", b"a" * (MAX_EPUB_BYTES + 1), 413),
    ],
)
def test_epub_invalid_upload_has_no_side_effects(
    client: TestClient, db: Session, filename: str, data: bytes, status: int
) -> None:
    headers = _headers(db)
    before = db.exec(select(func.count()).select_from(Book)).one()
    response = client.post(URL, headers=headers, files={"file": (filename, data)})
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)
    assert db.exec(select(func.count()).select_from(Book)).one() == before


def test_epub_requires_authentication_and_file(client: TestClient, db: Session) -> None:
    assert (
        client.post(URL, files={"file": ("book.epub", make_epub())}).status_code == 401
    )
    assert client.post(URL, headers=_headers(db)).status_code == 422


def test_epub_failure_rolls_back_book_and_chapters(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(db)
    before = [
        db.exec(select(func.count()).select_from(model)).one()
        for model in [Book, Chapter]
    ]

    def fail_commit() -> None:
        raise SQLAlchemyError("Simulated failure after flush")

    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", fail_commit)
        with pytest.raises(SQLAlchemyError):
            client.post(
                URL, headers=headers, files={"file": ("book.epub", make_epub())}
            )
    assert [
        db.exec(select(func.count()).select_from(model)).one()
        for model in [Book, Chapter]
    ] == before
