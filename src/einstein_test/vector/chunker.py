"""Chunking de texto por tamanho de caracteres com overlap."""

class TextChunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size deve ser > 0")
        if not (0 <= overlap < chunk_size):
            raise ValueError("overlap deve ser 0 <= overlap < chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        size = self.chunk_size
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = end - self.overlap
        return chunks