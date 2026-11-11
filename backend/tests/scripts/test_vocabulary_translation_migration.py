import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.db import engine
from app.models import Book, Chapter, User, VocabularyEntry


def test_optional_translation_migration_preserves_entries_and_guards_downgrade() -> (
    None
):
    scripts = ScriptDirectory(str(Path(__file__).resolve().parents[2] / "app/alembic"))
    revision = scripts.get_revision("62e63caea003")
    assert revision is not None and revision.down_revision == "020a2ca57aba"
    schema = f"test_vocabulary_migration_{uuid.uuid4().hex}"
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            with Operations.context(MigrationContext.configure(connection)):
                for previous in reversed(
                    list(scripts.iterate_revisions("020a2ca57aba", "base"))
                ):
                    previous.module.upgrade()
                owner = User(email="migration@example.com", hashed_password="unused")
                book = Book(title="Book", owner_id=owner.id)
                chapter = Chapter(
                    book_id=book.id, title="Chapter", content="maison", position=1
                )
                for model, record in [(User, owner), (Book, book), (Chapter, chapter)]:
                    connection.execute(
                        model.__table__.insert().values(record.model_dump())
                    )
                translated = VocabularyEntry(
                    owner_id=owner.id,
                    book_id=book.id,
                    chapter_id=chapter.id,
                    original_text="m",
                    contextual_translation="m",
                    context="maison",
                    start_offset=0,
                    end_offset=1,
                    context_start_offset=0,
                    context_end_offset=6,
                )
                connection.execute(
                    VocabularyEntry.__table__.insert().values(translated.model_dump())
                )
                revision.module.upgrade()
                columns = inspect(connection).get_columns(
                    "vocabularyentry", schema=schema
                )
                assert next(
                    column
                    for column in columns
                    if column["name"] == "contextual_translation"
                )["nullable"]
                untranslated = translated.model_copy(
                    update={
                        "id": uuid.uuid4(),
                        "end_offset": 6,
                        "original_text": "maison",
                        "contextual_translation": None,
                    }
                )
                connection.execute(
                    VocabularyEntry.__table__.insert().values(untranslated.model_dump())
                )
                # Never fill NULL with an invented translation just to downgrade.
                savepoint = connection.begin_nested()
                with pytest.raises(IntegrityError):
                    revision.module.downgrade()
                savepoint.rollback()
                entries = (
                    connection.execute(VocabularyEntry.__table__.select())
                    .mappings()
                    .all()
                )
                assert {
                    entry["id"]: entry["contextual_translation"] for entry in entries
                } == {
                    translated.id: "m",
                    untranslated.id: None,
                }
                connection.execute(
                    VocabularyEntry.__table__.delete().where(
                        VocabularyEntry.id == untranslated.id
                    )
                )
                revision.module.downgrade()
                columns = inspect(connection).get_columns(
                    "vocabularyentry", schema=schema
                )
                assert not next(
                    column
                    for column in columns
                    if column["name"] == "contextual_translation"
                )["nullable"]
        finally:
            transaction.rollback()
