"""Bounded EPUB parsing into the same plain-text contract used by TXT."""

import io
import posixpath
import re
import zipfile
import zlib
from html.entities import name2codepoint
from urllib.parse import unquote, urlsplit

from ebooklib import epub
from lxml import etree
from pydantic import ValidationError

from app.models import BookCreate, ChapterCreate
from app.services.book_import import BookImportError, ParsedBook

MAX_EPUB_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_ENTRY_BYTES = 10 * 1024 * 1024
MAX_ENTRIES = 2000
EPUB_TYPE = "{http://www.idpf.org/2007/ops}type"
BLOCKS = {
    "p",
    "div",
    "section",
    "article",
    "blockquote",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "pre",
    "tr",
}
SKIP_TYPES = {"cover", "toc", "landmarks", "page-list"}


def _xml(data: bytes) -> etree._Element:
    parser = etree.XMLParser(
        resolve_entities=False, load_dtd=False, no_network=True, huge_tree=False
    )
    # Resolve only the standard XHTML character names, without loading a DTD.
    data = re.sub(
        rb"&([A-Za-z][A-Za-z0-9]+);",
        lambda match: (
            f"&#{name2codepoint[match[1].decode('ascii')]};".encode()
            if match[1].decode("ascii") in name2codepoint
            else match[0]
        ),
        data,
    )
    root = etree.fromstring(data, parser)
    dtd = root.getroottree().docinfo.internalDTD
    if (dtd is not None and list(dtd.iterentities())) or any(
        True for _ in root.iter(etree.Entity)
    ):
        raise BookImportError("El EPUB contiene entidades XML no permitidas.")
    return root


def _path(value: str, base: str = "") -> tuple[str, str]:
    url = urlsplit(value)
    if url.scheme or url.netloc or url.query:
        raise BookImportError("El EPUB contiene referencias externas no admitidas.")
    decoded = unquote(url.path)
    path = posixpath.normpath(posixpath.join(base, decoded))
    if path.startswith("/") or path == ".." or path.startswith("../") or "\\" in path:
        raise BookImportError("El EPUB contiene rutas no permitidas.")
    return path, unquote(url.fragment)


def _safe_archive(data: bytes) -> bytes:
    if len(data) > MAX_EPUB_BYTES:
        raise BookImportError("El EPUB supera el límite de 20 MiB.")
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        entries = source.infolist()
        if (
            len(entries) > MAX_ENTRIES
            or sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES
        ):
            raise BookImportError("El EPUB supera los límites de descompresión.")
        files: dict[str, bytes] = {}
        for entry in entries:
            name, fragment = _path(entry.filename)
            if name != entry.filename.rstrip("/") or fragment or name in files:
                raise BookImportError("El EPUB contiene rutas duplicadas o inválidas.")
            if entry.is_dir():
                continue
            if entry.flag_bits & 1:
                raise BookImportError("No se admiten EPUB cifrados o con DRM.")
            if (
                entry.file_size > MAX_ENTRY_BYTES
                or entry.file_size > max(entry.compress_size, 1) * 200
            ):
                raise BookImportError("El EPUB supera los límites de descompresión.")
            with source.open(entry) as stream:
                content = stream.read(MAX_ENTRY_BYTES + 1)
            if len(content) > MAX_ENTRY_BYTES:
                raise BookImportError("Un recurso del EPUB supera los 10 MiB.")
            files[name] = content
        if files.get("mimetype") != b"application/epub+zip":
            raise BookImportError("El archivo no tiene una estructura EPUB válida.")
        container = _xml(files["META-INF/container.xml"])
        rootfiles = container.findall(
            "{urn:oasis:names:tc:opendocument:xmlns:container}rootfiles/"
            "{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"
        )
        if (
            len(rootfiles) != 1
            or rootfiles[0].get("media-type") != "application/oebps-package+xml"
        ):
            raise BookImportError(
                "El EPUB debe contener un único documento principal válido."
            )
        opf_path, _ = _path(rootfiles[0].get("full-path", ""))
        package = _xml(files[opf_path])
        opf = "{http://www.idpf.org/2007/opf}"
        if package.tag != f"{opf}package" or any(
            package.find(f"{opf}{name}") is None
            for name in ["metadata", "manifest", "spine"]
        ):
            raise BookImportError(
                "El EPUB no contiene metadatos, manifiesto o spine válidos."
            )
        for meta in package.xpath("//*[local-name()='meta']"):
            if (
                meta.get("property") == "rendition:layout"
                and (meta.text or "").strip() == "pre-paginated"
            ) or (meta.get("name") == "fixed-layout" and meta.get("content") == "true"):
                raise BookImportError("No se admiten EPUB de maquetación fija.")
        xml_names = {"META-INF/container.xml", opf_path}
        items: dict[str, str] = {}
        for item in package.xpath(
            "//*[local-name()='manifest']/*[local-name()='item']"
        ):
            item_id = item.get("id")
            if (
                not item_id
                or item_id in items
                or not item.get("href")
                or not item.get("media-type")
            ):
                raise BookImportError(
                    "El manifiesto del EPUB contiene recursos inválidos o duplicados."
                )
            name, _ = _path(item.get("href", ""), posixpath.dirname(opf_path))
            items[item_id] = name
            if "rendition:layout-pre-paginated" in item.get("properties", "").split():
                raise BookImportError("No se admiten EPUB de maquetación fija.")
            if (
                item.get("media-type", "").endswith(("xml", "+xml"))
                or item.get("media-type") == "text/html"
            ):
                xml_names.add(name)
        spine = package.find(f"{opf}spine")
        assert spine is not None
        if spine.get("toc"):
            xml_names.add(items[spine.get("toc")])
        if "META-INF/encryption.xml" in files:
            encryption = _xml(files["META-INF/encryption.xml"])
            allowed = {
                "http://www.idpf.org/2008/embedding",
                "http://ns.adobe.com/pdf/enc#RC",
            }
            if any(
                method.get("Algorithm") not in allowed
                for method in encryption.xpath("//*[local-name()='EncryptionMethod']")
            ):
                raise BookImportError("No se admiten EPUB con DRM.")
            xml_names.add("META-INF/encryption.xml")
        # Re-serialize validated XML without DTDs before EbookLib parses it.
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as target:
            for name, content in files.items():
                if name in xml_names:
                    content = etree.tostring(
                        _xml(content), encoding="utf-8", xml_declaration=True
                    )
                target.writestr(name, content)
    return output.getvalue()


def _text(node: etree._Element) -> str:
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip()


def _toc(entries: list, result: dict[tuple[str, str], str]) -> None:
    for entry in entries:
        if isinstance(entry, tuple):
            _toc([entry[0]], result)
            _toc(entry[1], result)
        elif getattr(entry, "href", ""):
            result.setdefault(_path(entry.href), entry.title.strip())


def _sections(
    root: etree._Element, titles: dict[str, str], fallback: str
) -> tuple[list[tuple[str, str]], bool]:
    body = root.find(".//{*}body")
    if body is None:
        raise BookImportError("Un documento del EPUB no contiene body.")
    if set(body.get(EPUB_TYPE, "").split()) & SKIP_TYPES:
        return [], False
    for node in list(body.iter()):
        if not isinstance(node.tag, str):
            continue
        if (
            etree.QName(node).localname
            in {
                "script",
                "style",
                "nav",
                "noscript",
                "svg",
                "img",
                "audio",
                "video",
                "object",
                "iframe",
                "embed",
            }
            or set(node.get(EPUB_TYPE, "").split()) & SKIP_TYPES
        ):
            parent = node.getparent()
            if parent is not None:
                # Preserve following narrative text when removing navigation nodes.
                tail = node.tail or ""
                previous = node.getprevious()
                parent.remove(node)
                if previous is not None:
                    previous.tail = (previous.tail or "") + tail
                else:
                    parent.text = (parent.text or "") + tail
    sections: list[tuple[str, str]] = []
    title = titles.get("", fallback)
    parts: list[str] = []
    explicit = False

    def finish() -> None:
        content = "".join(parts)
        content = "\n".join(
            re.sub(r"[^\S\n]+", " ", line).strip() for line in content.splitlines()
        )
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        if content:
            sections.append((title, content))

    def visit(node: etree._Element) -> None:
        nonlocal title, parts, explicit
        if not isinstance(node.tag, str):
            return
        tag = etree.QName(node).localname
        label = titles.get(node.get("id", "")) if node.get("id") else None
        if tag == "h1":
            label = label or _text(node)
        if label:
            if "".join(parts).strip():
                finish()
                parts = []
            title = label
            explicit = True
        if tag in BLOCKS:
            parts.append("\n\n")
        if tag == "br":
            parts.append("\n")
        if node.text:
            parts.append(node.text if tag == "pre" else re.sub(r"\s+", " ", node.text))
        for child in node:
            visit(child)
            if child.tail:
                parts.append(re.sub(r"\s+", " ", child.tail))
        if tag in BLOCKS:
            parts.append("\n\n")

    visit(body)
    finish()
    return sections, explicit


def parse_epub_book(data: bytes) -> ParsedBook:
    try:
        safe = _safe_archive(data)
        book = epub.read_epub(io.BytesIO(safe), options={"ignore_ncx": True})

        def metadata(field: str) -> list[str]:
            return [
                value.strip()
                for value, _ in book.get_metadata("DC", field)
                if value and value.strip()
            ]

        title = next(iter(metadata("title")), None)
        if not title:
            raise BookImportError("El EPUB no contiene título.")
        authors = metadata("creator")
        language = next(iter(metadata("language")), None)
        toc: dict[tuple[str, str], str] = {}
        _toc(book.toc, toc)
        excluded = {
            _path(entry["href"])[0]
            for entry in book.guide
            if entry.get("type") in SKIP_TYPES
        }
        chapters: list[ChapterCreate] = []
        visited: set[str] = set()
        continuation_title: str | None = None
        for item_id, _linear in book.spine:
            item = book.get_item_with_id(item_id)
            if item is None:
                raise BookImportError(
                    "El spine del EPUB referencia un documento inexistente."
                )
            name, _ = _path(item.file_name)
            if (
                name in visited
                or name in excluded
                or isinstance(item, (epub.EpubNav, epub.EpubCover))
            ):
                continue
            visited.add(name)
            if not isinstance(item, epub.EpubHtml):
                continue
            root = _xml(item.content)
            document_title = root.find(".//{*}title")
            fallback = (
                _text(document_title) if document_title is not None else ""
            ) or name
            labels = {
                fragment: label
                for (path, fragment), label in toc.items()
                if path == name
            }
            sections, explicit = _sections(root, labels, fallback)
            continuing = bool(
                chapters
                and not labels
                and not explicit
                and continuation_title == fallback
            )
            for section_title, content in sections:
                # A prior TOC entry or heading and a matching document title
                # identify a continuation; generic repeated titles do not.
                if continuing:
                    chapters[-1].content += "\n\n" + content
                else:
                    chapters.append(
                        ChapterCreate(
                            title=section_title,
                            content=content,
                            position=len(chapters) + 1,
                        )
                    )
            if sections and not continuing:
                continuation_title = chapters[-1].title if explicit or labels else None
        if not chapters:
            raise BookImportError("El EPUB no contiene texto legible.")
        return ParsedBook(
            book=BookCreate(title=title, author=", ".join(authors) or None),
            chapters=chapters,
            language=language,
        )
    except BookImportError:
        raise
    except (
        zipfile.BadZipFile,
        zlib.error,
        EOFError,
        KeyError,
        ValueError,
        OSError,
        RuntimeError,
        etree.LxmlError,
        ValidationError,
        epub.EpubException,
    ) as exc:
        raise BookImportError(
            "El EPUB está dañado, contiene XML inválido o metadatos incompatibles."
        ) from exc
