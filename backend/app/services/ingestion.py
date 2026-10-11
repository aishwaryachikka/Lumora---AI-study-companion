"""Document ingestion orchestration boundary."""

from typing import Protocol


class IngestionService(Protocol):
    """Contract for coordinating document processing and indexing."""

    async def ingest(self, document_id: str, content: bytes, filename: str) -> None:
        """Process and index an uploaded document."""
        ...
