import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.security import create_access_token
from app.models import Book, Chapter, ChapterCreate, ChapterUpdate
from tests.utils.user import create_random_user


def _create_book(db: Session) -> tuple[Book, dict[str, str]]:
    owner = create_random_user(db)
    book = Book(title="Test book", owner=owner)
    db.add(book)
    db.commit()
    token = create_access_token(owner.id, timedelta(minutes=5))
    return book, {"Authorization": f"Bearer {token}"}


def test_create_and_get_chapter(client: TestClient, db: Session) -> None:
    book, headers = _create_book(db)
    other_book, _ = _create_book(db)
    payload = {
        "title": "Chapitre premier",
        "content": "Bonjour !\n" * 1000,
        "position": 1,
    }
    url = f"{settings.API_V1_STR}/books/{book.id}/chapters"
    response = client.post(
        url, headers=headers, json={**payload, "book_id": str(other_book.id)}
    )
    assert response.status_code == 201
    content = response.json()
    assert content == {**payload, "id": content["id"], "book_id": str(book.id)}
    chapter_id = uuid.UUID(content["id"])
    db.expire_all()
    chapter = db.get(Chapter, chapter_id)
    assert chapter is not None
    assert chapter.book_id == book.id
    db.refresh(book)
    assert chapter in book.chapters
    assert chapter.book is book
    response = client.get(f"{url}/{chapter_id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == content


def test_list_chapters_order_and_pagination(client: TestClient, db: Session) -> None:
    book, headers = _create_book(db)
    other_book, _ = _create_book(db)
    chapters = [
        Chapter(
            title=f"Chapter {position}", content="Text", position=position, book=book
        )
        for position in [3, 1, 2]
    ]
    db.add_all(
        [
            *chapters,
            Chapter(title="Private", content="Text", position=1, book=other_book),
        ]
    )
    db.commit()
    url = f"{settings.API_V1_STR}/books/{book.id}/chapters"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert all(
        set(chapter) == {"id", "book_id", "title", "position"}
        for chapter in response.json()["data"]
    )
    assert [chapter["position"] for chapter in response.json()["data"]] == [1, 2, 3]
    response = client.get(url, headers=headers, params={"skip": 1, "limit": 1})
    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert [chapter["position"] for chapter in response.json()["data"]] == [2]
    response = client.get(url, headers=headers, params={"skip": 3})
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 3}


def test_list_chapters_empty(client: TestClient, db: Session) -> None:
    book, headers = _create_book(db)
    response = client.get(
        f"{settings.API_V1_STR}/books/{book.id}/chapters", headers=headers
    )
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


@pytest.mark.parametrize("is_superuser", [False, True])
def test_chapters_hide_foreign_and_missing_books(
    client: TestClient, db: Session, is_superuser: bool
) -> None:
    book, _ = _create_book(db)
    user = create_random_user(db)
    user.is_superuser = is_superuser
    chapter = Chapter(title="Private", content="Text", position=1, book=book)
    db.add_all([user, chapter])
    db.commit()
    token = create_access_token(user.id, timedelta(minutes=5))
    headers = {"Authorization": f"Bearer {token}"}
    for book_id in [book.id, uuid.uuid4()]:
        url = f"{settings.API_V1_STR}/books/{book_id}/chapters"
        for method, suffix in [
            ("post", ""),
            ("get", ""),
            ("get", f"/{chapter.id}"),
            ("patch", f"/{chapter.id}"),
            ("delete", f"/{chapter.id}"),
        ]:
            response = client.request(
                method,
                url + suffix,
                headers=headers,
                **(
                    {"json": {"title": "New", "content": "Text", "position": 1}}
                    if method in {"post", "patch"}
                    else {}
                ),
            )
            assert response.status_code == 404
            assert response.json() == {"detail": "Book not found"}
    db.refresh(book)
    assert len(book.chapters) == 1


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_chapter_rejects_wrong_book(
    client: TestClient, db: Session, method: str
) -> None:
    book, headers = _create_book(db)
    same_owner_book = Book(title="Second book", owner_id=book.owner_id)
    foreign_book, _ = _create_book(db)
    chapters = [
        Chapter(title="Other chapter", content="Text", position=1, book=parent)
        for parent in [same_owner_book, foreign_book]
    ]
    db.add_all(chapters)
    db.commit()
    for chapter_id in [*(chapter.id for chapter in chapters), uuid.uuid4()]:
        response = client.request(
            method,
            f"{settings.API_V1_STR}/books/{book.id}/chapters/{chapter_id}",
            headers=headers,
            **({"json": {"title": "Changed"}} if method == "patch" else {}),
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Chapter not found"}


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("post", ""),
        ("get", ""),
        ("get", "/" + str(uuid.uuid4())),
        ("patch", "/" + str(uuid.uuid4())),
        ("delete", "/" + str(uuid.uuid4())),
    ],
)
def test_chapters_require_authentication(
    client: TestClient, method: str, suffix: str
) -> None:
    response = client.request(
        method,
        f"{settings.API_V1_STR}/books/{uuid.uuid4()}/chapters{suffix}",
        **(
            {"json": {"title": "New", "content": "Text", "position": 1}}
            if method in {"post", "patch"}
            else {}
        ),
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "", "content": "Text", "position": 1},
        {"title": "a" * 256, "content": "Text", "position": 1},
        {"title": "Title", "content": "", "position": 1},
        {"title": "Title", "content": None, "position": 1},
        {"title": "Title", "content": "Text", "position": 0},
        {"title": "Title", "content": "Text", "position": -1},
        {"title": "Title", "content": "Text", "position": 1.5},
    ],
)
def test_create_chapter_validation(
    client: TestClient, db: Session, payload: dict[str, str | int | float | None]
) -> None:
    book, headers = _create_book(db)
    response = client.post(
        f"{settings.API_V1_STR}/books/{book.id}/chapters", headers=headers, json=payload
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "params", [{"skip": -1}, {"limit": 0}, {"limit": 101}, {"skip": "bad"}]
)
def test_list_chapters_pagination_validation(
    client: TestClient, db: Session, params: dict[str, int | str]
) -> None:
    book, headers = _create_book(db)
    response = client.get(
        f"{settings.API_V1_STR}/books/{book.id}/chapters",
        headers=headers,
        params=params,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "bad/chapters",
        "bad/chapters/" + str(uuid.uuid4()),
        str(uuid.uuid4()) + "/chapters/bad",
    ],
)
def test_chapter_path_validation(client: TestClient, db: Session, path: str) -> None:
    _, headers = _create_book(db)
    response = client.get(f"{settings.API_V1_STR}/books/{path}", headers=headers)
    assert response.status_code == 422


@pytest.mark.parametrize("database_delete", [False, True])
def test_book_delete_cascades_to_chapters(db: Session, database_delete: bool) -> None:
    book, _ = _create_book(db)
    other_book, _ = _create_book(db)
    chapter = Chapter(title="Delete", content="Text", position=1, book=book)
    kept = Chapter(title="Keep", content="Text", position=1, book=other_book)
    db.add_all([chapter, kept])
    db.commit()
    chapter_id, kept_id = chapter.id, kept.id
    if database_delete:
        db.exec(delete(Book).where(Book.id == book.id))
    else:
        db.delete(book)
    db.commit()
    db.expunge_all()
    assert db.get(Chapter, chapter_id) is None
    assert db.get(Chapter, kept_id) is not None


def test_chapter_update_partial_validation() -> None:
    from pydantic import ValidationError

    assert ChapterUpdate().model_dump(exclude_unset=True) == {}
    assert ChapterUpdate(title="New").model_dump(exclude_unset=True) == {"title": "New"}
    for field in ["title", "content", "position"]:
        with pytest.raises(ValidationError):
            ChapterUpdate.model_validate({field: None})
    with pytest.raises(ValidationError):
        ChapterUpdate(position=0)
    assert ChapterCreate(title="Title", content="Text", position=1).position == 1


def test_patch_chapter_partial_update(client: TestClient, db: Session) -> None:
    book, headers = _create_book(db)
    chapter = Chapter(title="Original", content="Original text", position=1, book=book)
    db.add(chapter)
    db.commit()
    chapter_id = chapter.id
    url = f"{settings.API_V1_STR}/books/{book.id}/chapters/{chapter_id}"
    response = client.patch(
        url,
        headers=headers,
        json={
            "title": "Updated",
            "book_id": str(uuid.uuid4()),
            "id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": str(chapter_id),
        "book_id": str(book.id),
        "title": "Updated",
        "content": "Original text",
        "position": 1,
    }
    response = client.patch(
        url,
        headers=headers,
        json={"content": "New text\n\nNext paragraph", "position": 3},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    assert response.json()["content"] == "New text\n\nNext paragraph"
    assert response.json()["position"] == 3
    response = client.patch(url, headers=headers, json={})
    assert response.status_code == 200
    db.refresh(chapter)
    assert chapter.content == "New text\n\nNext paragraph"
    assert chapter.position == 3
    assert chapter.book_id == book.id


@pytest.mark.parametrize(
    "payload",
    [
        {"title": ""},
        {"title": None},
        {"title": "a" * 256},
        {"content": ""},
        {"content": None},
        {"position": 0},
        {"position": -1},
        {"position": None},
        {"position": 1.5},
    ],
)
def test_patch_chapter_validation(
    client: TestClient, db: Session, payload: dict[str, str | int | float | None]
) -> None:
    book, headers = _create_book(db)
    chapter = Chapter(title="Original", content="Text", position=1, book=book)
    db.add(chapter)
    db.commit()
    response = client.patch(
        f"{settings.API_V1_STR}/books/{book.id}/chapters/{chapter.id}",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422
    db.refresh(chapter)
    assert (chapter.title, chapter.content, chapter.position) == ("Original", "Text", 1)


def test_delete_chapter_preserves_book_and_other_chapters(
    client: TestClient, db: Session
) -> None:
    book, headers = _create_book(db)
    chapters = [
        Chapter(title="Chapter", content="Text", position=position, book=book)
        for position in [1, 2]
    ]
    db.add_all(chapters)
    db.commit()
    deleted_id, kept_id = [chapter.id for chapter in chapters]
    book_id = book.id
    url = f"{settings.API_V1_STR}/books/{book_id}/chapters/{deleted_id}"
    response = client.delete(url, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Chapter deleted successfully"}
    db.expunge_all()
    assert db.get(Chapter, deleted_id) is None
    assert db.get(Chapter, kept_id) is not None
    assert db.get(Book, book_id) is not None
    assert client.get(url, headers=headers).status_code == 404
    assert client.delete(url, headers=headers).status_code == 404


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize("invalid_part", ["book", "chapter"])
def test_modify_chapter_invalid_uuid(
    client: TestClient, db: Session, method: str, invalid_part: str
) -> None:
    book, headers = _create_book(db)
    book_id = "bad" if invalid_part == "book" else str(book.id)
    chapter_id = "bad" if invalid_part == "chapter" else str(uuid.uuid4())
    response = client.request(
        method,
        f"{settings.API_V1_STR}/books/{book_id}/chapters/{chapter_id}",
        headers=headers,
        **({"json": {"title": "Changed"}} if method == "patch" else {}),
    )
    assert response.status_code == 422
