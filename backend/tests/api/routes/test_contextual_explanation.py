import uuid
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.routes import books
from app.core.config import settings
from tests.api.routes.test_chapters import _create_book
from tests.api.routes.test_french_nlp import PAYLOAD, setup_chapter
from tests.services.test_contextual_explanation import (
    fake_client as _fake_client_fixture,  # noqa: F401
)


def url(book_id, chapter_id):
    return f"{settings.API_V1_STR}/books/{book_id}/chapters/{chapter_id}/explain"


def test_explanation_uses_one_server_analysis(
    client: TestClient, db: Session, fake_client, monkeypatch
) -> None:
    book, chapter, headers = setup_chapter(db)
    spy = Mock(wraps=books.analyze_selection)
    monkeypatch.setattr(books, "analyze_selection", spy)
    response = client.post(
        url(book.id, chapter.id),
        headers=headers,
        json={**PAYLOAD, "text": "invented", "analysis": {"lemma": "invented"}},
    )
    assert response.status_code == 200
    assert response.json()["selected_text"] == "aperçut"
    assert response.json()["explanation"]["contextual_translation"] == "vislumbró"
    spy.assert_called_once()
    assert spy.call_args.args[0] == chapter.content
    fake_client.responses.parse.assert_called_once()
    assert (
        client.post(
            f"{settings.API_V1_STR}/books/{book.id}/chapters/{chapter.id}/analyze",
            headers=headers,
            json=PAYLOAD,
        ).status_code
        == 200
    )
    assert fake_client.responses.parse.call_count == 1


@pytest.mark.parametrize("superuser", [False, True])
def test_explanation_denies_foreign_and_missing_resources(
    client: TestClient, db: Session, fake_client, superuser: bool
) -> None:
    book, chapter, _ = setup_chapter(db)
    other, headers = _create_book(db)
    other.owner.is_superuser = superuser
    db.add(other.owner)
    db.commit()
    for target in [
        url(book.id, chapter.id),
        url(other.id, chapter.id),
        url(uuid.uuid4(), chapter.id),
        url(other.id, uuid.uuid4()),
    ]:
        assert client.post(target, headers=headers, json=PAYLOAD).status_code == 404
    fake_client.models.retrieve.assert_not_called()
    fake_client.responses.parse.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"start_offset": -1, "end_offset": 1},
        {"start_offset": 5, "end_offset": 5},
        {"start_offset": 0, "end_offset": 999},
        {"start_offset": 1, "end_offset": 3},
        {**PAYLOAD, "offset_unit": "code-points"},
        {"start_offset": 30, "end_offset": 35},
    ],
)
def test_explanation_rejects_offsets_without_provider_call(
    client: TestClient, db: Session, fake_client, payload
) -> None:
    book, chapter, headers = setup_chapter(db)
    assert (
        client.post(url(book.id, chapter.id), headers=headers, json=payload).status_code
        == 422
    )
    fake_client.responses.parse.assert_not_called()


def test_explanation_requires_authentication(client: TestClient, fake_client) -> None:
    assert client.post(url(uuid.uuid4(), uuid.uuid4()), json=PAYLOAD).status_code == 401
    fake_client.responses.parse.assert_not_called()


def test_explanation_disabled_by_configuration(
    client: TestClient, db: Session, fake_client, monkeypatch
) -> None:
    book, chapter, headers = setup_chapter(db)
    monkeypatch.setattr(settings, "OPENAI_ENABLED", False)
    assert (
        client.post(url(book.id, chapter.id), headers=headers, json=PAYLOAD).status_code
        == 503
    )
    fake_client.models.retrieve.assert_not_called()
    fake_client.responses.parse.assert_not_called()
