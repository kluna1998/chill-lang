import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.db import engine
from app.models import Book, Chapter, User


def test_chapter_migration_upgrade_and_downgrade() -> None:
    scripts = ScriptDirectory(str(Path(__file__).resolve().parents[2] / "app/alembic"))
    revision = scripts.get_revision("8c7ab0c90d05")
    assert revision is not None
    assert revision.down_revision == "b7c2d4e6f801"
    schema = f"test_chapter_migration_{uuid.uuid4().hex}"
    # Exercise the real chain in a separate schema; roll back all DDL and test data.
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            with Operations.context(MigrationContext.configure(connection)):
                for previous in reversed(
                    list(scripts.iterate_revisions("b7c2d4e6f801", "base"))
                ):
                    previous.module.upgrade()
                owner_id, book_id = uuid.uuid4(), uuid.uuid4()
                connection.execute(
                    User.__table__.insert().values(
                        id=owner_id,
                        email="migration@example.com",
                        hashed_password="unused",
                    )
                )
                connection.execute(
                    Book.__table__.insert().values(
                        id=book_id,
                        owner_id=owner_id,
                        title="Preserved book",
                        created_at=datetime.now(UTC),
                    )
                )
                revision.module.upgrade()
                assert {
                    column["name"]
                    for column in inspect(connection).get_columns(
                        "chapter", schema=schema
                    )
                } == {"id", "book_id", "title", "content", "position"}
                foreign_key = inspect(connection).get_foreign_keys(
                    "chapter", schema=schema
                )[0]
                assert foreign_key["referred_table"] == "book"
                assert foreign_key["options"]["ondelete"] == "CASCADE"
                connection.execute(
                    Chapter.__table__.insert().values(
                        id=uuid.uuid4(),
                        book_id=book_id,
                        title="Chapter",
                        content="Text",
                        position=1,
                    )
                )
                revision.module.downgrade()
                assert not inspect(connection).has_table("chapter", schema=schema)
                assert (
                    connection.execute(text("SELECT title FROM book")).scalar_one()
                    == "Preserved book"
                )
                revision.module.upgrade()
                assert inspect(connection).has_table("chapter", schema=schema)
        finally:
            transaction.rollback()
