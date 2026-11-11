from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.security import create_access_token
from app.models import Book, Chapter
from app.services.book_import import MAX_TXT_BYTES
from tests.utils.epub import make_epub
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

    failed_sessions: list[Session] = []
    rolled_back_sessions: list[Session] = []
    original_rollback = Session.rollback

    def fail_commit(session: Session) -> None:
        # Patch the request session, not only the separate db fixture.
        failed_sessions.append(session)
        assert [
            session.exec(select(func.count()).select_from(model)).one()
            for model in [Book, Chapter]
        ] == [books_before + 1, chapters_before + 2]
        raise SQLAlchemyError("Simulated failure after flush")

    def track_rollback(session: Session) -> None:
        rolled_back_sessions.append(session)
        original_rollback(session)

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        patch.setattr(Session, "rollback", track_rollback)
        with pytest.raises(SQLAlchemyError):
            client.post(URL, headers=headers, files={"file": ("book.txt", TXT)})
    assert len(failed_sessions) == 1
    assert rolled_back_sessions == failed_sessions
    with Session(db.get_bind()) as verification:
        assert (
            verification.exec(select(func.count()).select_from(Book)).one()
            == books_before
        )
        assert (
            verification.exec(select(func.count()).select_from(Chapter)).one()
            == chapters_before
        )


@pytest.mark.parametrize("file_type", ["txt", "epub"])
def test_import_database_constraint_failure_leaves_no_partial_records(
    client: TestClient, db: Session, file_type: str
) -> None:
    headers = _headers(db)
    before = [
        db.exec(select(func.count()).select_from(model)).one()
        for model in [Book, Chapter]
    ]

    def invalidate_second_chapter(
        session: Session, _flush_context: object, _instances: object
    ) -> None:
        chapters = [record for record in session.new if isinstance(record, Chapter)]
        assert len(chapters) == 2
        # Let PostgreSQL reject a real NOT NULL violation during chapter insertion.
        chapters[1].sqlmodel_update({"content": None})

    event.listen(Session, "before_flush", invalidate_second_chapter)
    try:
        with pytest.raises(IntegrityError) as error:
            client.post(
                f"{settings.API_V1_STR}/books/import-{file_type}",
                headers=headers,
                files={
                    "file": (
                        f"book.{file_type}",
                        TXT if file_type == "txt" else make_epub(),
                    )
                },
            )
    finally:
        event.remove(Session, "before_flush", invalidate_second_chapter)
    assert error.value.statement is not None
    assert "INSERT INTO chapter" in error.value.statement
    with Session(db.get_bind()) as verification:
        assert [
            verification.exec(select(func.count()).select_from(model)).one()
            for model in [Book, Chapter]
        ] == before
