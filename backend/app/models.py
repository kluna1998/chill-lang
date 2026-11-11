import uuid
from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator
from pydantic import Field as PydanticField
from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    books: list[Book] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class BookBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    author: str | None = Field(default=None, max_length=255)


class Book(BookBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=DateTime(timezone=True)
    )
    owner: User | None = Relationship(back_populates="books")
    chapters: list["Chapter"] = Relationship(  # noqa: UP037
        back_populates="book",
        cascade_delete=True,
    )


class BookCreate(BookBase):
    pass


class BookUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def title_must_not_be_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Title cannot be null")
        return value


class BookPublic(BookBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime


class BooksPublic(SQLModel):
    data: list[BookPublic]
    count: int


class ChapterBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, sa_type=Text)
    position: int = Field(ge=1)


class Chapter(ChapterBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    book_id: uuid.UUID = Field(
        foreign_key="book.id", nullable=False, ondelete="CASCADE"
    )
    book: Book | None = Relationship(back_populates="chapters")


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    position: int | None = Field(default=None, ge=1)

    @field_validator("title", "content", "position")
    @classmethod
    def fields_must_not_be_null(cls, value: str | int | None) -> str | int:
        if value is None:
            raise ValueError("Chapter fields cannot be null")
        return value


class ChapterPublic(ChapterBase):
    id: uuid.UUID
    book_id: uuid.UUID


class ChapterSummary(SQLModel):
    id: uuid.UUID
    book_id: uuid.UUID
    title: str
    position: int


class ChaptersPublic(SQLModel):
    data: list[ChapterSummary]
    count: int


class VocabularyCreate(SQLModel):
    chapter_id: uuid.UUID
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    original_text: str = Field(min_length=1, max_length=512)
    contextual_translation: str | None = Field(
        default=None, min_length=1, max_length=500
    )
    context: str = Field(min_length=1, max_length=2000)
    context_start_offset: int = Field(ge=0)
    context_end_offset: int = Field(ge=1)
    offset_unit: Literal["utf-16"] = "utf-16"

    @field_validator("original_text", "contextual_translation")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Text cannot be blank")
        return value


class VocabularyUpdate(SQLModel):
    contextual_translation: str | None = Field(min_length=1, max_length=500)

    @field_validator("contextual_translation")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        return VocabularyCreate.nonblank(value)


class VocabularyEntry(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("owner_id", "chapter_id", "start_offset", "end_offset"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
    book_id: uuid.UUID = Field(foreign_key="book.id", ondelete="CASCADE")
    chapter_id: uuid.UUID = Field(foreign_key="chapter.id", ondelete="CASCADE")
    original_text: str = Field(max_length=512)
    contextual_translation: str | None = Field(default=None, max_length=500)
    context: str = Field(sa_type=Text)
    start_offset: int
    end_offset: int
    context_start_offset: int
    context_end_offset: int
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=DateTime(timezone=True)
    )


class VocabularyPublic(SQLModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    book_id: uuid.UUID
    chapter_id: uuid.UUID
    original_text: str
    contextual_translation: str | None
    context: str
    start_offset: int
    end_offset: int
    context_start_offset: int
    context_end_offset: int
    offset_unit: Literal["utf-16"] = "utf-16"
    created_at: datetime


class VocabularyPublicList(SQLModel):
    data: list[VocabularyPublic]
    count: int


class ReadingProgressUpdate(SQLModel):
    chapter_id: uuid.UUID
    position: int = Field(ge=0)
    content_hash: str = PydanticField(pattern=r"^[0-9a-f]{64}$")
    expected_version: int = Field(ge=0)
    offset_unit: Literal["utf-16"] = "utf-16"


class ReadingProgress(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("owner_id", "book_id"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
    book_id: uuid.UUID = Field(foreign_key="book.id", ondelete="CASCADE")
    chapter_id: uuid.UUID = Field(foreign_key="chapter.id", ondelete="CASCADE")
    position: int
    content_hash: str = Field(max_length=64)
    version: int = Field(default=1)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=DateTime(timezone=True)
    )


class ReadingProgressPublic(SQLModel):
    book_id: uuid.UUID
    chapter_id: uuid.UUID
    position: int
    content_hash: str
    version: int
    offset_unit: Literal["utf-16"] = "utf-16"
    updated_at: datetime


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class SelectionAnalysisRequest(SQLModel):
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    offset_unit: Literal["utf-16"] = "utf-16"

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if self.end_offset <= self.start_offset:
            raise ValueError("El final debe ser posterior al inicio de la selección.")
        if self.end_offset - self.start_offset > 512:
            raise ValueError("Selecciona como máximo 512 unidades UTF-16.")
        return self


class AnalyzedSentence(SQLModel):
    text: str
    start_offset: int
    end_offset: int
    is_truncated: bool


class AnalyzedToken(SQLModel):
    text: str
    lemma: str | None
    pos: str | None
    morphology: dict[str, list[str]] | None
    dependency: str | None
    start_offset: int
    end_offset: int
    head_text: str | None
    head_start_offset: int | None
    head_end_offset: int | None


class SelectionAnalysis(SQLModel):
    book_id: uuid.UUID
    chapter_id: uuid.UUID
    offset_unit: Literal["utf-16"] = "utf-16"
    selected_text: str
    start_offset: int
    end_offset: int
    context: str
    context_start_offset: int
    context_end_offset: int
    context_truncated: bool
    sentences: list[AnalyzedSentence]
    tokens: list[AnalyzedToken]
    selection_covers_full_tokens: bool
    model_name: str
    model_version: str
    spacy_version: str


class ContextualExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    contextual_translation: str = PydanticField(min_length=1, max_length=500)
    meaning_explanation: str | None = PydanticField(min_length=1, max_length=1200)
    grammar_explanation: str | None = PydanticField(min_length=1, max_length=1000)
    sentence_translation: str | None = PydanticField(min_length=1, max_length=1200)
    uncertainty_note: str | None = PydanticField(min_length=1, max_length=500)


class SelectionExplanation(SQLModel):
    book_id: uuid.UUID
    chapter_id: uuid.UUID
    start_offset: int
    end_offset: int
    offset_unit: Literal["utf-16"] = "utf-16"
    selected_text: str
    explanation: ContextualExplanation
