"""
core/rag_engine.py
──────────────────
RAG (Retrieval Augmented Generation) engine wrapper.
Provides sector-specific document intelligence.
"""

from typing import Optional, List
from tools.document_processor import DocumentProcessor
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class RAGEngine:
    """
    Manages sector-specific document collections for RAG.
    Each sector has its own ChromaDB collection.
    """

    def __init__(self):
        self.settings = get_settings()
        self._processors: dict[str, DocumentProcessor] = {}

    def get_processor(self, sector: str) -> DocumentProcessor:
        """Get or create a DocumentProcessor for a sector."""
        if sector not in self._processors:
            collection_name = getattr(
                self.settings,
                f"chroma_collection_{sector}",
                f"{sector}_sector_docs",
            )
            self._processors[sector] = DocumentProcessor(collection_name)
        return self._processors[sector]

    def ingest_document(self, filepath: str, sector: str, metadata: Optional[dict] = None) -> int:
        """Ingest a PDF document into the sector's vector store."""
        processor = self.get_processor(sector)
        return processor.process_pdf(filepath, metadata or {"sector": sector})

    def ingest_directory(self, directory: str, sector: str) -> int:
        """Ingest all PDFs from a directory."""
        processor = self.get_processor(sector)
        return processor.process_directory(directory, {"sector": sector})

    def query(self, query_text: str, sector: str, n_results: int = 5) -> List[dict]:
        """Retrieve relevant document chunks for a query."""
        processor = self.get_processor(sector)
        return processor.query(query_text, n_results)

    def format_results(self, results: List[dict]) -> str:
        """Format RAG results for LLM prompt."""
        if not results:
            return ""
        processor = list(self._processors.values())[0]
        return processor.format_rag_results(results)

    def get_stats(self) -> dict:
        """Return stats for all sector collections."""
        return {
            sector: proc.get_stats()
            for sector, proc in self._processors.items()
        }
