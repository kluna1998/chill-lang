"""French analysis of a bounded window from persisted chapter text."""

import uuid
from importlib.metadata import version
from threading import Lock

import spacy
from spacy.language import Language

from app.models import AnalyzedSentence, AnalyzedToken, SelectionAnalysis

MODEL_NAME = "fr_core_news_sm"
MAX_SELECTION_UTF16 = 512
MAX_WINDOW_CHARS = 4096
_pipeline: Language | None = None
_pipeline_lock = Lock()


class InvalidSelection(ValueError):
    pass


class NLPUnavailable(RuntimeError):
    pass


def get_pipeline() -> Language:
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            try:
                _pipeline = spacy.load(MODEL_NAME, exclude=["ner"])
            except (OSError, ValueError) as exc:
                raise NLPUnavailable(
                    "El modelo lingüístico francés no está disponible."
                ) from exc
    return _pipeline


def utf16_to_python(text: str, start: int, end: int) -> tuple[int, int]:
    if start < 0 or end <= start or end - start > MAX_SELECTION_UTF16:
        raise InvalidSelection("La selección debe tener entre 1 y 512 unidades UTF-16.")
    offset = 0
    positions: dict[int, int] = {}
    for index, char in enumerate(text):
        if offset == start:
            positions[start] = index
        if offset >= end:
            if offset == end:
                positions[end] = index
            break
        offset += 2 if ord(char) > 0xFFFF else 1
    else:
        if offset == end:
            positions[end] = len(text)
    if start not in positions or end not in positions:
        raise InvalidSelection(
            "Los offsets están fuera del capítulo o cortan un carácter Unicode."
        )
    return positions[start], positions[end]


def analyze_selection(
    text: str, book_id: uuid.UUID, chapter_id: uuid.UUID, start: int, end: int
) -> SelectionAnalysis:
    first, last = utf16_to_python(text, start, end)
    selected = text[first:last]
    if not selected.strip():
        raise InvalidSelection("Selecciona texto, no solo espacios en blanco.")
    radius = (MAX_WINDOW_CHARS - (last - first)) // 2
    window_start, window_end = max(0, first - radius), min(len(text), last + radius)
    window = text[window_start:window_end]
    # Only scan the chapter once to locate the selection. All inverse mappings
    # are local to the bounded window, including supplementary Unicode chars.
    window_base = start - len(text[window_start:first].encode("utf-16-le")) // 2
    offsets = [window_base]
    for char in window:
        offsets.append(offsets[-1] + (2 if ord(char) > 0xFFFF else 1))
    pipeline = get_pipeline()
    doc = pipeline(window)
    local_start, local_end = first - window_start, last - window_start
    tokens = [
        token
        for token in doc
        if not token.is_space
        and token.idx < local_end
        and token.idx + len(token.text) > local_start
    ]
    if not tokens:
        raise InvalidSelection("La selección no contiene tokens analizables.")
    sentences = (
        [
            sentence
            for sentence in doc.sents
            if sentence.start_char < local_end and sentence.end_char > local_start
        ]
        if doc.has_annotation("SENT_START")
        else []
    )
    spans = [
        AnalyzedSentence(
            text=sentence.text,
            start_offset=offsets[sentence.start_char],
            end_offset=offsets[sentence.end_char],
            is_truncated=(window_start > 0 and sentence.start == 0)
            or (window_end < len(text) and sentence.end == len(doc)),
        )
        for sentence in sentences
    ]
    context_start = min(sentences[0].start_char, local_start) if sentences else 0
    context_end = max(sentences[-1].end_char, local_end) if sentences else len(window)
    has_morph = doc.has_annotation("MORPH")
    has_dep = doc.has_annotation("DEP")
    analyzed = [
        AnalyzedToken(
            text=token.text,
            lemma=token.lemma_ or None,
            pos=token.pos_ or None,
            morphology={
                key: value.split(",") for key, value in token.morph.to_dict().items()
            }
            if has_morph
            else None,
            dependency=token.dep_ or None if has_dep else None,
            start_offset=offsets[token.idx],
            end_offset=offsets[token.idx + len(token.text)],
            head_text=token.head.text if has_dep and token.dep_ else None,
            head_start_offset=offsets[token.head.idx]
            if has_dep and token.dep_
            else None,
            head_end_offset=offsets[token.head.idx + len(token.head.text)]
            if has_dep and token.dep_
            else None,
        )
        for token in tokens
    ]
    return SelectionAnalysis(
        book_id=book_id,
        chapter_id=chapter_id,
        selected_text=selected,
        start_offset=start,
        end_offset=end,
        context=window[context_start:context_end],
        context_start_offset=offsets[context_start],
        context_end_offset=offsets[context_end],
        context_truncated=any(sentence.is_truncated for sentence in spans)
        if spans
        else (window_start > 0 or window_end < len(text)),
        sentences=spans,
        tokens=analyzed,
        selection_covers_full_tokens=all(
            token.idx >= local_start and token.idx + len(token.text) <= local_end
            for token in tokens
        ),
        model_name=MODEL_NAME,
        model_version=pipeline.meta["version"],
        spacy_version=version("spacy"),
    )
