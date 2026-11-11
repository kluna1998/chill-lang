import pytest

from app.services.book_import import MAX_TXT_BYTES, BookImportError, parse_txt_book


def test_parse_txt_preserves_text_and_chapter_order() -> None:
    parsed = parse_txt_book(
        "TITLE: Une aventure à Paris\nAUTHOR: Chill-Lang\n\n=== CHAPTER: Le départ ===\n\nCamille se réveille.\nElle regarde.\n\n=== CHAPTER: La rencontre ===\nBonjour !\n".encode()
    )
    assert parsed.book.title == "Une aventure à Paris"
    assert parsed.book.author == "Chill-Lang"
    assert [chapter.position for chapter in parsed.chapters] == [1, 2]
    assert [chapter.title for chapter in parsed.chapters] == [
        "Le départ",
        "La rencontre",
    ]
    assert parsed.chapters[0].content == "\nCamille se réveille.\nElle regarde.\n\n"
    assert parsed.chapters[1].content == "Bonjour !\n"


def test_utf8_bom_crlf_and_optional_author() -> None:
    parsed = parse_txt_book(
        "\ufeffTITLE: Livre\r\n=== CHAPTER: Un ===\r\nTexte\r\n\r\nSuite".encode()
    )
    assert parsed.book.author is None
    assert parsed.chapters[0].content == "Texte\n\nSuite"


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b" \n",
        b"\xff",
        b"TITLE: Book\x00",
        b"TITLE: Book",
        b"=== CHAPTER: One ===\nText",
        b"TITLE: \n=== CHAPTER: One ===\nText",
        b"TITLE: Book\n=== CHAPTER: One ===\n \n",
        b"TITLE: Book\n=== CHAPTER: ===\nText",
        b"TITLE: Book\n=== CHAPTER One ===\nText",
        b"TITLE: Book\nText before chapter\n=== CHAPTER: One ===\nText",
        b"TITLE: Book\nTITLE: Again\n=== CHAPTER: One ===\nText",
        b"TITLE: Book\n=== CHAPTER: One ===\nText\n=== CHAPTER: Two ===\n",
        ("TITLE: " + "a" * 256 + "\n=== CHAPTER: One ===\nText").encode(),
        ("TITLE: Book\nAUTHOR: " + "a" * 256 + "\n=== CHAPTER: One ===\nText").encode(),
        ("TITLE: Book\n=== CHAPTER: " + "a" * 256 + " ===\nText").encode(),
    ],
)
def test_rejects_invalid_txt(data: bytes) -> None:
    with pytest.raises(BookImportError):
        parse_txt_book(data)


def test_size_limit() -> None:
    prefix = b"TITLE: Book\n=== CHAPTER: One ===\n"
    assert (
        parse_txt_book(prefix + b"a" * (MAX_TXT_BYTES - len(prefix))).book.title
        == "Book"
    )
    with pytest.raises(BookImportError, match="5 MiB"):
        parse_txt_book(b"a" * (MAX_TXT_BYTES + 1))
