import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    ReadingProgress,
    ReadingProgressPublic,
    ReadingProgressUpdate,
    VocabularyCreate,
    VocabularyEntry,
    VocabularyPublic,
    VocabularyPublicList,
    VocabularyUpdate,
)
from app.services import reading_state

router = APIRouter(tags=["reading"])


@router.post("/vocabulary/", response_model=VocabularyPublic)
def save_vocabulary(
    session: SessionDep, current_user: CurrentUser, data: VocabularyCreate
) -> VocabularyEntry:
    return reading_state.save_vocabulary(session, current_user.id, data)


@router.get("/vocabulary/", response_model=VocabularyPublicList)
def list_vocabulary(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> VocabularyPublicList:
    return reading_state.list_vocabulary(session, current_user.id, skip, limit)


@router.delete("/vocabulary/{entry_id}", response_model=Message)
def delete_vocabulary(
    session: SessionDep, current_user: CurrentUser, entry_id: uuid.UUID
) -> Message:
    reading_state.delete_vocabulary(session, current_user.id, entry_id)
    return Message(message="Vocabulary entry deleted")


@router.patch("/vocabulary/{entry_id}", response_model=VocabularyPublic)
def update_vocabulary(
    session: SessionDep,
    current_user: CurrentUser,
    entry_id: uuid.UUID,
    data: VocabularyUpdate,
) -> VocabularyEntry:
    return reading_state.update_vocabulary(session, current_user.id, entry_id, data)


@router.get("/books/{book_id}/progress", response_model=ReadingProgressPublic | None)
def get_progress(
    session: SessionDep, current_user: CurrentUser, book_id: uuid.UUID
) -> ReadingProgress | None:
    return reading_state.get_progress(session, current_user.id, book_id)


@router.put("/books/{book_id}/progress", response_model=ReadingProgressPublic)
def save_progress(
    session: SessionDep,
    current_user: CurrentUser,
    book_id: uuid.UUID,
    data: ReadingProgressUpdate,
) -> ReadingProgress:
    return reading_state.save_progress(session, current_user.id, book_id, data)
