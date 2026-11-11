import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Chapter
from app.services import french_nlp
from tests.api.routes.test_chapters import _create_book


def setup_chapter(db: Session):
    book, headers = _create_book(db)
    chapter = Chapter(
        title="Chapitre", content="😀 Elle aperçut un homme.", position=1, book=book
    )
    db.add(chapter)
    db.commit()
    return book, chapter, headers


def url(book_id: uuid.UUID, chapter_id: uuid.UUID) -> str:
    return f"{settings.API_V1_STR}/books/{book_id}/chapters/{chapter_id}/analyze"


PAYLOAD = {"start_offset": 8, "end_offset": 15, "offset_unit": "utf-16"}


def test_analysis_uses_persisted_text(client: TestClient, db: Session) -> None:
    book, chapter, headers = setup_chapter(db)
    response = client.post(
        url(book.id, chapter.id),
        headers=headers,
        json={**PAYLOAD, "text": "Invented text"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["selected_text"] == "aperçut"
    assert result["book_id"] == str(book.id)
    assert result["chapter_id"] == str(chapter.id)
    assert result["tokens"][0]["lemma"] == "apercevoir"
    assert result["offset_unit"] == "utf-16"


@pytest.mark.parametrize("is_superuser", [False, True])
def test_analysis_hides_private_and_wrong_books(
    client: TestClient, db: Session, is_superuser: bool
) -> None:
    book, chapter, _ = setup_chapter(db)
    other_book, headers = _create_book(db)
    owner = other_book.owner
    owner.is_superuser = is_superuser
    db.add(owner)
    db.commit()
    for target in [url(book.id, chapter.id), url(uuid.uuid4(), chapter.id)]:
        response = client.post(target, headers=headers, json=PAYLOAD)
        assert response.status_code == 404
        assert response.json()["detail"] == "Book not found"
    response = client.post(
        url(other_book.id, chapter.id), headers=headers, json=PAYLOAD
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Chapter not found"


@pytest.mark.parametrize(
    "payload",
    [
        {"start_offset": -1, "end_offset": 1},
        {"start_offset": 5, "end_offset": 5},
        {"start_offset": 0, "end_offset": 999},
        {"start_offset": 1, "end_offset": 3},
        {"start_offset": 0, "end_offset": 1},
        {**PAYLOAD, "offset_unit": "code-points"},
        {"start_offset": 30, "end_offset": 35},
    ],
)
def test_analysis_validates_offsets(
    client: TestClient, db: Session, payload: dict
) -> None:
    book, chapter, headers = setup_chapter(db)
    assert (
        client.post(url(book.id, chapter.id), headers=headers, json=payload).status_code
        == 422
    )


def test_analysis_requires_authentication(client: TestClient) -> None:
    assert client.post(url(uuid.uuid4(), uuid.uuid4()), json=PAYLOAD).status_code == 401


def test_model_unavailable_has_clear_error(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    book, chapter, headers = setup_chapter(db)

    def unavailable():
        raise french_nlp.NLPUnavailable(
            "El modelo lingüístico francés no está disponible."
        )

    monkeypatch.setattr(french_nlp, "get_pipeline", unavailable)
    response = client.post(url(book.id, chapter.id), headers=headers, json=PAYLOAD)
    assert response.status_code == 503
    assert "no está disponible" in response.json()["detail"]
