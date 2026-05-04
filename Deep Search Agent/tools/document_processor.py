"""
tools/document_processor.py
────────────────────────────
Process PDF annual reports and financial documents.
Chunks and indexes them into the ChromaDB vector store for RAG retrieval.
"""

import os
from pathlib import Path
from typing import List, Optional
import chromadb
from chromadb.utils import embedding_functions

from config.settings import get_settings
from utils.logger import get_logger
from utils.helpers import truncate_text

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Processes financial documents (PDFs, TXTs) and stores them
    in a ChromaDB vector database for semantic retrieval.
    """

    def __init__(self, collection_name: str):
        self.settings = get_settings()
        self.collection_name = collection_name

        # Init ChromaDB with persistence
        self.chroma_client = chromadb.PersistentClient(
            path=self.settings.chroma_persist_dir
        )

        # Use sentence-transformers for embeddings (free, local)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"RAG collection '{collection_name}' ready ({self.collection.count()} docs)")

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            i += chunk_size - overlap
        return chunks

    def process_pdf(self, filepath: str, metadata: Optional[dict] = None) -> int:
        """
        Extract text from a PDF file and index it.
        Returns the number of chunks indexed.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            logger.error("pypdf not installed. Run: pip install pypdf")
            return 0

        filepath = Path(filepath)
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return 0

        logger.info(f"Processing PDF: {filepath.name}")

        reader = PdfReader(str(filepath))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        if not full_text.strip():
            logger.warning(f"No text extracted from {filepath.name}")
            return 0

        chunks = self._chunk_text(full_text)
        base_metadata = metadata or {}
        base_metadata["source"] = filepath.name
        base_metadata["file_type"] = "pdf"

        # Add chunks to ChromaDB
        ids = [f"{filepath.stem}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{**base_metadata, "chunk_index": i} for i in range(len(chunks))]

        # Batch insert (ChromaDB handles up to 5461 at a time)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            self.collection.add(
                documents=chunks[i:i + batch_size],
                ids=ids[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
            )

        logger.info(f"Indexed {len(chunks)} chunks from {filepath.name}")
        return len(chunks)

    def process_directory(self, directory: str, metadata: Optional[dict] = None) -> int:
        """Process all PDFs in a directory."""
        total = 0
        for f in Path(directory).glob("*.pdf"):
            total += self.process_pdf(str(f), metadata)
        logger.info(f"Total chunks indexed from directory: {total}")
        return total

    def query(self, query_text: str, n_results: int = 5) -> List[dict]:
        """
        Retrieve the most relevant document chunks for a query.
        
        Returns:
            List of {text, source, score, metadata}
        """
        if self.collection.count() == 0:
            logger.debug("RAG collection is empty — no documents indexed yet")
            return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=min(n_results, self.collection.count()),
                include=["documents", "distances", "metadatas"],
            )

            output = []
            for doc, dist, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
            ):
                output.append({
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "relevance_score": round(1 - dist, 4),  # cosine: 1=identical
                    "metadata": meta,
                })
            return output
        except Exception as e:
            logger.warning(f"RAG query failed: {e}")
            return []

    def format_rag_results(self, results: List[dict]) -> str:
        """Format RAG results for LLM prompt insertion."""
        if not results:
            return "No relevant documents found in internal knowledge base."

        parts = ["**Relevant Document Excerpts:**\n"]
        for i, r in enumerate(results, 1):
            parts.append(
                f"[Doc {i} | Source: {r['source']} | Relevance: {r['relevance_score']:.2f}]\n"
                f"{truncate_text(r['text'], 600)}\n"
            )
        return "\n---\n".join(parts)

    def get_stats(self) -> dict:
        """Return collection statistics."""
        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "persist_dir": self.settings.chroma_persist_dir,
        }
