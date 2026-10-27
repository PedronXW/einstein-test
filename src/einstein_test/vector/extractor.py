"""Extração de texto de arquivos (texto puro e PDF via pypdf)."""

import io
from pathlib import PurePath

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".log"}


class TextExtractor:
    def extract(self, filename: str, content: bytes) -> str:
        suffix = PurePath(filename).suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(content)
        if suffix in TEXT_EXTENSIONS:
            return self._extract_text(content)
        return ""

    def _extract_text(self, content: bytes) -> str:
        try:
            return self._sanitize(content.decode("utf-8"))
        except UnicodeDecodeError:
            return ""

    def _extract_pdf(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return self._sanitize(text)
        except Exception:
            return ""

    @staticmethod
    def _sanitize(text: str) -> str:
        """Remove bytes NUL (proibidos pelo PostgreSQL em colunas text)."""
        return text.replace("\x00", "")