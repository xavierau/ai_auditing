"""Text chunking service for KB documents.

Simple chunking strategy with configurable size and overlap.
"""

from typing import List
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    page_range: tuple[int, int] | None = None  # (start_page, end_page)


class ChunkingService:
    """Service for chunking large text documents into smaller pieces."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """Initialize chunking service.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[TextChunk]:
        """Chunk text into overlapping segments.

        Args:
            text: Full text to chunk

        Returns:
            List of TextChunk objects
        """
        if not text or len(text) == 0:
            return []

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # Don't exceed text length
            if end > len(text):
                end = len(text)
            else:
                # Try to break at sentence boundary (period + space)
                # Look back up to 200 chars for a good break point
                search_start = max(end - 200, start)
                last_period = text.rfind(". ", search_start, end)

                if last_period > start:
                    end = last_period + 1  # Include the period

            # Extract chunk content
            chunk_content = text[start:end].strip()

            if chunk_content:  # Only add non-empty chunks
                chunk = TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move start position (with overlap)
            start = end - self.chunk_overlap

            # Prevent infinite loop
            if start <= chunks[-1].start_char if chunks else False:
                start = end

        return chunks

    def estimate_chunks(self, text: str) -> int:
        """Estimate number of chunks for given text.

        Args:
            text: Text to estimate

        Returns:
            Estimated number of chunks
        """
        if not text:
            return 0

        effective_chunk_size = self.chunk_size - self.chunk_overlap
        return max(1, (len(text) + effective_chunk_size - 1) // effective_chunk_size)
