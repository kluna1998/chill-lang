import io
import zipfile

import pytest

from app.services.book_import import BookImportError
from app.services.epub_import import parse_epub_book
from tests.utils.epub import make_epub, xhtml


def test_metadata_spine_paragraphs_and_dialogue() -> None:
    book = parse_epub_book(make_epub(spine=["nav.xhtml", "two.xhtml", "one.xhtml"]))
    assert book.book.title == "Une aventure à Paris"
    assert book.book.author == "Chill-Lang"
    assert book.language == "fr"
    assert [chapter.title for chapter in book.chapters] == ["La rencontre", "Le départ"]
    assert [chapter.position for chapter in book.chapters] == [1, 2]
    assert "Camille se réveille.\n\n— Bonjour !\n— Salut !" in book.chapters[1].content
    assert "Sommaire" not in "".join(chapter.content for chapter in book.chapters)


def test_split_chapter_continues_without_losing_text() -> None:
    parsed = parse_epub_book(
        make_epub(
            documents={
                "one.xhtml": xhtml(
                    "Le départ", "<h1>Le départ</h1><p>Premier paragraphe.</p>"
                ),
                "continued.xhtml": xhtml("Le départ", "<p>Suite du chapitre.</p>"),
                "two.xhtml": xhtml(
                    "La rencontre", "<h1>La rencontre</h1><p>Autre chapitre.</p>"
                ),
            },
            toc='<li><a href="one.xhtml">Le départ</a></li><li><a href="two.xhtml">La rencontre</a></li>',
        )
    )
    assert len(parsed.chapters) == 2
    assert "Premier paragraphe." in parsed.chapters[0].content
    assert "Suite du chapitre." in parsed.chapters[0].content


def test_toc_anchors_split_one_document_and_preserve_preamble() -> None:
    parsed = parse_epub_book(
        make_epub(
            documents={
                "one.xhtml": xhtml(
                    "Sections",
                    '<p>Préface.</p><section id="a"><p>Premier.</p></section><section id="b"><p>Deuxième.</p></section>',
                )
            },
            toc='<li><a href="one.xhtml#a">Un</a></li><li><a href="one.xhtml#b">Deux</a></li>',
        )
    )
    assert [chapter.title for chapter in parsed.chapters] == ["Sections", "Un", "Deux"]
    assert all(
        value in "\n".join(chapter.content for chapter in parsed.chapters)
        for value in ["Préface.", "Premier.", "Deuxième."]
    )


def test_conservative_spine_sections_keep_source_titles() -> None:
    parsed = parse_epub_book(
        make_epub(
            documents={
                "one.xhtml": xhtml("Source A", "<p>A</p>"),
                "two.xhtml": xhtml("Source B", "<p>B</p>"),
            },
            toc="",
        )
    )
    assert [chapter.title for chapter in parsed.chapters] == ["Source A", "Source B"]


def test_cover_navigation_scripts_and_images_are_not_narrative() -> None:
    parsed = parse_epub_book(
        make_epub(
            documents={
                "cover.xhtml": xhtml(
                    "Cover", '<div epub:type="cover"><p>Cover label</p></div>'
                ),
                "one.xhtml": xhtml(
                    "Chapter",
                    '<h1>Chapitre</h1><nav>Index duplicate</nav><script>bad()</script><style>.bad{}</style><p>Avant <em>et</em> après.</p><img src="photo.png"/><p>Fin.</p>',
                ),
            },
            guide='<guide><reference type="cover" href="cover.xhtml" title="Cover"/></guide>',
        )
    )
    assert len(parsed.chapters) == 1
    assert "Avant et après." in parsed.chapters[0].content
    assert not any(
        value in parsed.chapters[0].content
        for value in ["bad()", "Index duplicate", "Cover label"]
    )


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not a zip",
        make_epub(extra={"mimetype": b"wrong"}),
        make_epub(extra={"../outside": b"bad"}),
        make_epub(extra={"META-INF/container.xml": b"<bad>"}),
        make_epub(
            package_meta='<meta property="rendition:layout">pre-paginated</meta>'
        ),
        make_epub(
            extra={
                "META-INF/encryption.xml": b'<encryption><EncryptionMethod Algorithm="drm"/></encryption>'
            }
        ),
        make_epub(documents={"one.xhtml": xhtml("Empty", "<img src='x'/>")}),
    ],
)
def test_rejects_malformed_unsupported_and_unsafe_archives(data: bytes) -> None:
    with pytest.raises(BookImportError):
        parse_epub_book(data)


def test_rejects_entity_expansion() -> None:
    doc = b'<!DOCTYPE html [<!ENTITY x SYSTEM "file:///etc/passwd">]><html xmlns="http://www.w3.org/1999/xhtml"><body><p>&x;</p></body></html>'
    with pytest.raises(BookImportError, match="entidades"):
        parse_epub_book(make_epub(extra={"OEBPS/one.xhtml": doc}))


def test_standard_external_doctype_does_not_fetch_resources() -> None:
    doc = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://invalid.example/xhtml.dtd">'
        + xhtml("Safe", "<h1>Safe</h1><p>Texte.</p>")
    ).encode()
    assert (
        parse_epub_book(make_epub(extra={"OEBPS/one.xhtml": doc})).chapters[0].title
        == "Safe"
    )


def test_zip_bomb_is_rejected_before_ebooklib() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb", b"a" * 1024 * 1024)
    with pytest.raises(BookImportError, match="décompression|descompresión"):
        parse_epub_book(stream.getvalue())


def test_duplicate_entries_rejected() -> None:
    stream = io.BytesIO(make_epub())
    with pytest.warns(UserWarning), zipfile.ZipFile(stream, "a") as archive:
        archive.writestr("mimetype", b"application/epub+zip")
    with pytest.raises(BookImportError):
        parse_epub_book(stream.getvalue())


def test_standard_xhtml_entities_are_decoded_without_dtd_access() -> None:
    parsed = parse_epub_book(
        make_epub(
            documents={
                "one.xhtml": xhtml(
                    "Source", "<p>Fran&ccedil;ais&nbsp;: &laquo; bonjour &raquo;</p>"
                )
            }
        )
    )
    assert "Français : « bonjour »" in parsed.chapters[0].content


def test_generic_repeated_document_titles_do_not_merge_ambiguous_sections() -> None:
    parsed = parse_epub_book(
        make_epub(
            documents={
                "one.xhtml": xhtml("Book", "<p>One.</p>"),
                "two.xhtml": xhtml("Book", "<p>Two.</p>"),
            },
            toc="",
        )
    )
    assert len(parsed.chapters) == 2


def test_epub2_ncx_order_and_metadata() -> None:
    source = make_epub()
    with zipfile.ZipFile(io.BytesIO(source)) as archive:
        package = archive.read("OEBPS/content.opf").decode()
    package = package.replace('version="3.0"', 'version="2.0"').replace(
        '<item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/>',
        "",
    )
    package = package.replace(
        "</manifest>",
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>',
    ).replace("<spine>", '<spine toc="ncx">')
    ncx = b'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap><navPoint id="p1" playOrder="1"><navLabel><text>Le depart</text></navLabel><content src="one.xhtml"/></navPoint><navPoint id="p2" playOrder="2"><navLabel><text>La rencontre</text></navLabel><content src="two.xhtml"/></navPoint></navMap></ncx>'
    parsed = parse_epub_book(
        make_epub(extra={"OEBPS/content.opf": package.encode(), "OEBPS/toc.ncx": ncx})
    )
    assert len(parsed.chapters) == 2
    assert parsed.language == "fr"
    assert parsed.chapters[0].title == "Le départ"


def test_multiple_renditions_are_rejected_before_library_parsing() -> None:
    container = b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/><rootfile full-path="other.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
    with pytest.raises(BookImportError, match="único"):
        parse_epub_book(make_epub(extra={"META-INF/container.xml": container}))
