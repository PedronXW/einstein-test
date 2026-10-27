"""Testes TDD da feature F-010 (AC-002/AC-003: extração de texto e chunking).

Valida o TextExtractor (txt/md utf-8 e PDF via pypdf) e o TextChunker
(chunk_size com overlap).
"""

from einstein_test.vector import TextChunker, TextExtractor


def test_ac002_extractor_txt():
    ex = TextExtractor()
    text = ex.extract("nota.txt", "olá mundo".encode("utf-8"))
    assert text == "olá mundo"


def test_ac002_extractor_md():
    ex = TextExtractor()
    text = ex.extract("readme.md", b"# Titulo\ncorpo")
    assert "# Titulo\ncorpo" in text


def test_ac002_extractor_strips_nul_bytes():
    ex = TextExtractor()
    text = ex.extract("nota.txt", b"ola\x00mundo")
    assert text == "olamundo", "bytes NUL removidos do texto"
    assert "\x00" not in text


def test_ac002_extractor_unknown_type_returns_empty():
    ex = TextExtractor()
    assert ex.extract("img.png", b"xxxx") == ""


def test_ac002_extractor_pdf():
    ex = TextExtractor()
    pdf_bytes = _minimal_pdf()
    text = ex.extract("doc.pdf", pdf_bytes)
    assert "Hello PDF" in text, "pypdf extrai texto do PDF simples"


def test_ac002_extractor_pdf_invalid_returns_empty():
    ex = TextExtractor()
    assert ex.extract("broken.pdf", b"not a pdf") == ""


def _minimal_pdf() -> bytes:
    """PDF 1.4 mínimo válido com um stream de texto 'Hello PDF'."""
    text = "Hello PDF"
    stream = b"BT /F1 12 Tf 72 720 Td (" + text.encode() + b") Tj ET"
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    out = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out += obj
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        out += ("%010d 00000 n \n" % off).encode()
    out += (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode()
        + b"\n%%EOF\n"
    )
    return out


def test_ac003_chunker_defaults():
    ch = TextChunker()
    assert ch.chunk_size == 1000
    assert ch.overlap == 200


def test_ac003_chunker_short_text_single_chunk():
    ch = TextChunker()
    chunks = ch.chunk("texto curto")
    assert chunks == ["texto curto"]


def test_ac003_chunker_long_text_multiple_chunks():
    ch = TextChunker(chunk_size=10, overlap=2)
    text = "a" * 35
    chunks = ch.chunk(text)
    assert len(chunks) > 1, "texto longo gera múltiplos chunks"
    assert all(0 < len(c) <= 10 for c in chunks)


def test_ac003_chunker_overlap_connects_chunks():
    ch = TextChunker(chunk_size=10, overlap=2)
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = ch.chunk(text)
    assert chunks[0] == "abcdefghij"
    assert chunks[1] == "ijklmnopqr", "overlap de 2 caracteres entre chunks"


def test_ac003_chunker_invalid_overlap():
    import pytest

    with pytest.raises(ValueError):
        TextChunker(chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        TextChunker(chunk_size=10, overlap=12)
    with pytest.raises(ValueError):
        TextChunker(chunk_size=0)


def test_ac003_chunker_empty_text():
    ch = TextChunker()
    assert ch.chunk("") == []


def test_ac003_chunker_whitespace_only():
    ch = TextChunker()
    assert ch.chunk("   \n  ") == []