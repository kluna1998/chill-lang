import hashlib
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import create_access_token
from app.models import Book, Chapter, ReadingProgress, VocabularyEntry
from app.services import contextual_explanation
from tests.utils.user import create_random_user

BASE = settings.API_V1_STR
TEXT = "😀 La maison est grande."


@pytest.fixture(name="library")
def library_fixture(db: Session, monkeypatch):
    def no_ai():
        raise AssertionError("Reading state must never call OpenAI")

    monkeypatch.setattr(contextual_explanation, "get_client", no_ai)
    owner = create_random_user(db)
    other = create_random_user(db)
    other.is_superuser = True
    db.add(other)
    book = Book(title="French", owner_id=owner.id)
    chapter = Chapter(title="One", content=TEXT, position=1, book_id=book.id)
    second = Chapter(
        title="Two", content="Un autre chapitre.", position=2, book_id=book.id
    )
    db.add_all([book, chapter, second])
    db.commit()

    def headers(user):
        return {
            "Authorization": f"Bearer {create_access_token(user.id, timedelta(minutes=5))}"
        }

    return book, chapter, second, headers(owner), headers(other)


def vocabulary(chapter):
    return {
        "chapter_id": str(chapter.id),
        "original_text": "maison",
        "contextual_translation": "casa",
        "context": TEXT,
        "start_offset": 6,
        "end_offset": 12,
        "context_start_offset": 0,
        "context_end_offset": 24,
        "offset_unit": "utf-16",
    }


def progress(chapter, version=0, position=6):
    return {
        "chapter_id": str(chapter.id),
        "position": position,
        "content_hash": hashlib.sha256(chapter.content.encode()).hexdigest(),
        "expected_version": version,
    }


def test_vocabulary_persistence_idempotence_and_delete(
    client: TestClient, db: Session, library
):
    book, chapter, _, owner, _ = library
    response = client.post(
        f"{BASE}/vocabulary/", headers=owner, json=vocabulary(chapter)
    )
    assert response.status_code == 200, response.text
    entry = response.json()
    assert entry["original_text"] == "maison"
    assert entry["contextual_translation"] == "casa"
    assert entry["context"] == TEXT
    assert entry["book_id"] == str(book.id)
    assert entry["offset_unit"] == "utf-16"
    assert entry["created_at"]
    assert db.get(VocabularyEntry, uuid.UUID(entry["id"])) is not None
    duplicate = client.post(
        f"{BASE}/vocabulary/",
        headers=owner,
        json={**vocabulary(chapter), "contextual_translation": "otra"},
    )
    assert duplicate.json() == entry
    assert client.get(f"{BASE}/vocabulary/", headers=owner).json() == {
        "data": [entry],
        "count": 1,
    }
    page = client.get(f"{BASE}/vocabulary/?skip=1&limit=1", headers=owner).json()
    assert page == {"data": [], "count": 1}
    assert (
        client.delete(f"{BASE}/vocabulary/{entry['id']}", headers=owner).status_code
        == 200
    )
    assert client.get(f"{BASE}/vocabulary/", headers=owner).json()["count"] == 0


def test_vocabulary_private_even_for_admin(client: TestClient, library):
    _, chapter, _, owner, other = library
    entry = client.post(
        f"{BASE}/vocabulary/", headers=owner, json=vocabulary(chapter)
    ).json()
    assert client.get(f"{BASE}/vocabulary/", headers=other).json() == {
        "data": [],
        "count": 0,
    }
    assert (
        client.delete(f"{BASE}/vocabulary/{entry['id']}", headers=other).status_code
        == 404
    )
    assert (
        client.post(
            f"{BASE}/vocabulary/", headers=other, json=vocabulary(chapter)
        ).status_code
        == 404
    )
    missing = client.post(
        f"{BASE}/vocabulary/",
        headers=other,
        json={**vocabulary(chapter), "chapter_id": str(uuid.uuid4())},
    )
    private = client.post(
        f"{BASE}/vocabulary/", headers=other, json=vocabulary(chapter)
    )
    assert private.json() == missing.json()


@pytest.mark.parametrize("omit_translation", [False, True])
def test_vocabulary_without_translation_can_be_updated_without_duplicates(
    client: TestClient, db: Session, library, omit_translation: bool
) -> None:
    _, chapter, _, owner, _ = library
    payload = {**vocabulary(chapter), "contextual_translation": None}
    if omit_translation:
        payload.pop("contextual_translation")
    response = client.post(f"{BASE}/vocabulary/", headers=owner, json=payload)
    assert response.status_code == 200, response.text
    entry = response.json()
    assert entry["contextual_translation"] is None
    assert entry["context"] == TEXT
    assert entry["start_offset"] == 6 and entry["end_offset"] == 12
    db.expire_all()
    assert (
        db.get(VocabularyEntry, uuid.UUID(entry["id"])).contextual_translation is None
    )
    # A repeated POST does not implicitly replace a saved snapshot.
    duplicate = client.post(
        f"{BASE}/vocabulary/", headers=owner, json=vocabulary(chapter)
    )
    assert duplicate.json() == entry
    updated = client.patch(
        f"{BASE}/vocabulary/{entry['id']}",
        headers=owner,
        json={
            "contextual_translation": "casa",
            "owner_id": str(uuid.uuid4()),
            "original_text": "forged",
        },
    )
    assert updated.status_code == 200
    assert updated.json() == {**entry, "contextual_translation": "casa"}
    assert client.get(f"{BASE}/vocabulary/", headers=owner).json() == {
        "data": [updated.json()],
        "count": 1,
    }
    assert (
        client.post(f"{BASE}/vocabulary/", headers=owner, json=payload).json()
        == updated.json()
    )
    cleared = client.patch(
        f"{BASE}/vocabulary/{entry['id']}",
        headers=owner,
        json={"contextual_translation": None},
    )
    assert cleared.status_code == 200 and cleared.json() == entry


def test_vocabulary_update_is_private_even_for_admin(client, library):
    _, chapter, _, owner, other = library
    entry = client.post(
        f"{BASE}/vocabulary/", headers=owner, json=vocabulary(chapter)
    ).json()
    responses = [
        client.patch(
            f"{BASE}/vocabulary/{id_}",
            headers=other,
            json={"contextual_translation": "modified"},
        )
        for id_ in [entry["id"], uuid.uuid4()]
    ]
    assert all(response.status_code == 404 for response in responses)
    assert responses[0].json() == responses[1].json()
    assert client.get(f"{BASE}/vocabulary/", headers=owner).json()["data"] == [entry]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"contextual_translation": ""},
        {"contextual_translation": " "},
        {"contextual_translation": "x" * 501},
        {"contextual_translation": 42},
    ],
)
def test_vocabulary_update_validation_preserves_existing_entry(
    client, library, payload
):
    _, chapter, _, owner, _ = library
    entry = client.post(
        f"{BASE}/vocabulary/", headers=owner, json=vocabulary(chapter)
    ).json()
    assert (
        client.patch(
            f"{BASE}/vocabulary/{entry['id']}", headers=owner, json=payload
        ).status_code
        == 422
    )
    assert client.get(f"{BASE}/vocabulary/", headers=owner).json()["data"] == [entry]


@pytest.mark.parametrize(
    "changes",
    [
        {"start_offset": 1},
        {"end_offset": 9999},
        {"original_text": "changed"},
        {"context_start_offset": 7},
        {"context_start_offset": 1},
        {"context_end_offset": 9999},
        {"contextual_translation": " "},
        {"context": "A different context."},
        {"end_offset": 6},
    ],
)
def test_vocabulary_validates_persisted_utf16_selection(client, library, changes):
    _, chapter, _, owner, _ = library
    result = client.post(
        f"{BASE}/vocabulary/", headers=owner, json={**vocabulary(chapter), **changes}
    )
    assert result.status_code == 422, result.text


def test_progress_recovery_and_stale_writes(client, db, library):
    book, chapter, second, owner, _ = library
    url = f"{BASE}/books/{book.id}/progress"
    assert client.get(url, headers=owner).json() is None
    first = client.put(url, headers=owner, json=progress(chapter))
    assert first.status_code == 200, first.text
    saved = first.json()
    assert saved["version"] == 1 and saved["position"] == 6
    assert client.get(url, headers=owner).json() == saved
    assert (
        db.exec(select(ReadingProgress).where(ReadingProgress.book_id == book.id))
        .one()
        .position
        == 6
    )
    assert client.put(url, headers=owner, json=progress(chapter)).status_code == 409
    newer = client.put(
        url, headers=owner, json=progress(second, version=1, position=3)
    ).json()
    assert newer["version"] == 2 and newer["chapter_id"] == str(second.id)
    assert (
        client.put(
            url, headers=owner, json=progress(chapter, version=1, position=0)
        ).status_code
        == 409
    )
    assert client.get(url, headers=owner).json() == newer


@pytest.mark.parametrize(
    "changes,status",
    [
        ({"position": 1}, 422),
        ({"position": 9999}, 422),
        ({"position": -1}, 422),
        ({"expected_version": -1}, 422),
        ({"content_hash": "0" * 64}, 409),
        ({"content_hash": "bad"}, 422),
        ({"chapter_id": str(uuid.uuid4())}, 404),
    ],
)
def test_progress_validation(client, library, changes, status):
    book, chapter, _, owner, _ = library
    result = client.put(
        f"{BASE}/books/{book.id}/progress",
        headers=owner,
        json={**progress(chapter), **changes},
    )
    assert result.status_code == status, result.text


def test_progress_private_and_wrong_book(client, db, library):
    book, chapter, _, owner, other = library
    url = f"{BASE}/books/{book.id}/progress"
    assert client.get(url, headers=other).status_code == 404
    assert client.put(url, headers=other, json=progress(chapter)).status_code == 404
    other_book = Book(title="Other", owner_id=book.owner_id)
    db.add(other_book)
    db.commit()
    assert (
        client.put(
            f"{BASE}/books/{other_book.id}/progress",
            headers=owner,
            json=progress(chapter),
        ).status_code
        == 404
    )


def test_chapter_edit_preserves_snapshot_and_rejects_outdated_progress(client, library):
    book, chapter, _, owner, _ = library
    url = f"{BASE}/books/{book.id}/progress"
    payload = progress(chapter)
    assert (
        client.post(
            f"{BASE}/vocabulary/", headers=owner, json=vocabulary(chapter)
        ).status_code
        == 200
    )
    saved = client.put(url, headers=owner, json=payload).json()
    assert (
        client.patch(
            f"{BASE}/books/{book.id}/chapters/{chapter.id}",
            headers=owner,
            json={"content": "Le texte a changé."},
        ).status_code
        == 200
    )
    assert (
        client.put(
            url, headers=owner, json={**payload, "expected_version": 1}
        ).status_code
        == 409
    )
    assert client.get(url, headers=owner).json() == saved
    assert (
        client.get(f"{BASE}/vocabulary/", headers=owner).json()["data"][0]["context"]
        == TEXT
    )


def test_deleted_chapter_cascades_reading_state(client, db, library):
    book, chapter, _, owner, _ = library
    entry = client.post(
        f"{BASE}/vocabulary/", headers=owner, json=vocabulary(chapter)
    ).json()
    assert (
        client.put(
            f"{BASE}/books/{book.id}/progress", headers=owner, json=progress(chapter)
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"{BASE}/books/{book.id}/chapters/{chapter.id}", headers=owner
        ).status_code
        == 200
    )
    assert client.get(f"{BASE}/books/{book.id}/progress", headers=owner).json() is None
    assert client.get(f"{BASE}/vocabulary/", headers=owner).json()["count"] == 0
    db.expire_all()
    assert db.get(VocabularyEntry, uuid.UUID(entry["id"])) is None


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/vocabulary/"),
        ("post", "/vocabulary/"),
        ("delete", f"/vocabulary/{uuid.uuid4()}"),
        ("patch", f"/vocabulary/{uuid.uuid4()}"),
        ("get", f"/books/{uuid.uuid4()}/progress"),
        ("put", f"/books/{uuid.uuid4()}/progress"),
    ],
)
def test_reading_state_requires_auth(client, method, path):
    assert getattr(client, method)(BASE + path).status_code == 401


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101"])
def test_vocabulary_pagination_limits(client, library, query):
    assert (
        client.get(f"{BASE}/vocabulary/?{query}", headers=library[3]).status_code == 422
    )
