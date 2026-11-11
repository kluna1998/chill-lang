"""Exercise the reading workflow with real persistence/NLP and a mocked AI provider."""

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import ContextualExplanation
from tests.api.routes.test_book_import import _headers
from tests.services.test_contextual_explanation import (
    fake_client as _fake_client_fixture,  # noqa: F401
)
from tests.utils.epub import make_epub, xhtml


@pytest.mark.parametrize("file_type", ["txt", "epub"])
def test_import_to_vocabulary_and_progress(
    client: TestClient, db: Session, fake_client, file_type: str
) -> None:
    headers, other = _headers(db), _headers(db)
    text = "😀 La maison est grande."
    data = (
        f"TITLE: Intégration\n\n=== CHAPTER: Premier ===\n{text}".encode()
        if file_type == "txt"
        else make_epub(documents={"one.xhtml": xhtml("Premier", f"<p>{text}</p>")})
    )
    base = settings.API_V1_STR
    imported = client.post(
        f"{base}/books/import-{file_type}",
        headers=headers,
        files={"file": (f"book.{file_type}", data)},
    )
    assert imported.status_code == 201
    book_url = f"{base}/books/{imported.json()['id']}"
    index = client.get(f"{book_url}/chapters", headers=headers).json()
    chapter_id = index["data"][0]["id"]
    assert "content" not in index["data"][0]
    chapter_url = f"{book_url}/chapters/{chapter_id}"
    content = client.get(chapter_url, headers=headers).json()["content"]
    assert text in content
    assert client.get(chapter_url, headers=other).status_code == 404
    start = len(content[: content.index("maison")].encode("utf-16-le")) // 2
    selection = {
        "start_offset": start,
        "end_offset": start + 6,
        "offset_unit": "utf-16",
    }
    analyzed = client.post(f"{chapter_url}/analyze", headers=headers, json=selection)
    assert analyzed.status_code == 200
    analysis = analyzed.json()
    assert analysis["selected_text"] == "maison"
    assert analysis["tokens"][0]["lemma"] == "maison"
    fake_client.responses.parse.return_value.output_parsed = ContextualExplanation(
        contextual_translation="casa",
        meaning_explanation=None,
        grammar_explanation=None,
        sentence_translation=None,
        uncertainty_note=None,
    )
    translated = client.post(f"{chapter_url}/explain", headers=headers, json=selection)
    assert translated.status_code == 200
    saved = client.post(
        f"{base}/vocabulary/",
        headers=headers,
        json={
            **selection,
            "chapter_id": chapter_id,
            "original_text": translated.json()["selected_text"],
            "contextual_translation": translated.json()["explanation"][
                "contextual_translation"
            ],
            "context": analysis["context"],
            "context_start_offset": analysis["context_start_offset"],
            "context_end_offset": analysis["context_end_offset"],
        },
    )
    assert saved.status_code == 200
    assert client.get(f"{base}/vocabulary/", headers=headers).json()["data"] == [
        saved.json()
    ]
    assert client.get(f"{base}/vocabulary/", headers=other).json()["count"] == 0
    assert (
        client.delete(
            f"{base}/vocabulary/{saved.json()['id']}", headers=other
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"{base}/vocabulary/{saved.json()['id']}", headers=headers
        ).status_code
        == 200
    )
    assert client.get(f"{base}/vocabulary/", headers=headers).json()["count"] == 0
    progress = client.put(
        f"{book_url}/progress",
        headers=headers,
        json={
            "chapter_id": chapter_id,
            "position": start,
            "expected_version": 0,
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        },
    )
    assert progress.status_code == 200
    assert client.get(f"{book_url}/progress", headers=headers).json() == progress.json()
    assert client.get(f"{book_url}/progress", headers=other).status_code == 404
    fake_client.responses.parse.assert_called_once()
