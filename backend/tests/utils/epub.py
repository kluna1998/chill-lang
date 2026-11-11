"""Small real EPUB archives used by parser and endpoint tests."""

import io
import zipfile
from xml.sax.saxutils import escape


def xhtml(title: str, body: str) -> str:
    return f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{escape(title)}</title></head><body>{body}</body></html>'


def make_epub(
    documents: dict[str, str] | None = None,
    spine: list[str] | None = None,
    toc: str | None = None,
    extra: dict[str, bytes] | None = None,
    package_meta: str = "",
    guide: str = "",
) -> bytes:
    documents = (
        documents
        if documents is not None
        else {
            "one.xhtml": xhtml(
                "Le départ",
                "<h1>Le départ</h1><p>Camille se réveille.</p><p>— Bonjour !<br/>— Salut !</p>",
            ),
            "two.xhtml": xhtml(
                "La rencontre", "<h1>La rencontre</h1><p>Elle rencontre Sophie.</p>"
            ),
        }
    )
    ids = {name: f"d{index}" for index, name in enumerate(documents)}
    ids["nav.xhtml"] = "nav"
    manifest = "".join(
        f'<item id="{ids[name]}" href="{name}" media-type="application/xhtml+xml"/>'
        for name in documents
    )
    if toc is None:
        toc = "".join(
            f'<li><a href="{name}">{index + 1}</a></li>'
            for index, name in enumerate(documents)
        )
    nav = xhtml("Sommaire", f'<nav epub:type="toc"><ol>{toc}</ol></nav>')
    refs = "".join(
        f'<itemref idref="{ids[name]}"/>'
        for name in (spine if spine is not None else list(documents))
    )
    package = f"""<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">test</dc:identifier><dc:title>Une aventure à Paris</dc:title><dc:creator>Chill-Lang</dc:creator><dc:language>fr</dc:language>{package_meta}</metadata><manifest>{manifest}<item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/></manifest><spine>{refs}</spine>{guide}</package>"""
    files = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        "OEBPS/content.opf": package.encode(),
        "OEBPS/nav.xhtml": nav.encode(),
        **{f"OEBPS/{name}": content.encode() for name, content in documents.items()},
        **(extra or {}),
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue()
