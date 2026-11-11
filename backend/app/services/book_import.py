"""Parse Chill-Lang UTF-8 TXT files without HTTP or database dependencies."""

import re

from pydantic import BaseModel, ValidationError

from app.models import BookCreate, ChapterCreate

MAX_TXT_BYTES = 5 * 1024 * 1024
CHAPTER_HEADER = re.compile(r"=== CHAPTER: (.+?) ===")


class BookImportError(ValueError):
    pass


class ParsedBook(BaseModel):
    book: BookCreate
    chapters: list[ChapterCreate]


def parse_txt_book(data: bytes) -> ParsedBook:
    if len(data) > MAX_TXT_BYTES:
        raise BookImportError("El archivo supera el límite de 5 MiB.")
    try:
        text = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError as exc:
        raise BookImportError("El archivo debe estar codificado en UTF-8.") from exc
    if not text.strip():
        raise BookImportError("El archivo está vacío.")
    if "\x00" in text:
        raise BookImportError("El archivo contiene caracteres nulos no permitidos.")

    metadata: dict[str, str] = {}
    chapters: list[ChapterCreate] = []
    chapter_title: str | None = None
    lines: list[str] = []

    def finish_chapter() -> None:
        if chapter_title is None:
            return
        content = "".join(lines)
        if not content.strip():
            raise BookImportError(f"El capítulo «{chapter_title}» no tiene contenido.")
        try:
            chapters.append(
                ChapterCreate(
                    title=chapter_title, content=content, position=len(chapters) + 1
                )
            )
        except ValidationError as exc:
            raise BookImportError(
                "El título de cada capítulo debe tener entre 1 y 255 caracteres."
            ) from exc

    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        marker = CHAPTER_HEADER.fullmatch(stripped)
        if marker:
            finish_chapter()
            chapter_title = marker.group(1).strip()
            lines = []
        elif stripped.startswith("==="):
            raise BookImportError(
                "Cabecera de capítulo inválida. Usa === CHAPTER: Nombre ===."
            )
        elif chapter_title is not None:
            lines.append(line)
        elif stripped.strip():
            key, separator, value = stripped.partition(":")
            if not separator or key not in {"TITLE", "AUTHOR"}:
                raise BookImportError(
                    "Antes del primer capítulo solo se permiten TITLE: y AUTHOR:."
                )
            if key in metadata:
                raise BookImportError(f"La cabecera {key}: está repetida.")
            metadata[key] = value.strip()
    finish_chapter()
    if not metadata.get("TITLE"):
        raise BookImportError("Falta TITLE: con el título del libro.")
    if not chapters:
        raise BookImportError(
            "El archivo debe incluir al menos un capítulo con contenido."
        )
    try:
        book = BookCreate(
            title=metadata["TITLE"], author=metadata.get("AUTHOR") or None
        )
    except ValidationError as exc:
        raise BookImportError(
            "El título y el autor no pueden superar los 255 caracteres."
        ) from exc
    return ParsedBook(book=book, chapters=chapters)
