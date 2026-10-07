"""RAG retriever for the Cubik-Lite Integral Calculus Tutor.

Indexes the markdown knowledge base under data/ into a persistent ChromaDB
collection, and retrieves the most relevant chunks for a student question.
Embeddings come from llm_client.embed(), so indexing and querying use
whichever provider (Gemini or local Ollama) is active.
"""

from pathlib import Path
from shutil import rmtree

from chromadb import PersistentClient
from chromadb.errors import NotFoundError
from llm_client import embed

DATA_DIR = Path(__file__).parent / "data"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "calculus_docs"


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Split text into overlapping fixed-size chunks.

    Args:
        text: The text to split.
        chunk_size: Maximum characters per chunk.
        overlap: Characters shared between consecutive chunks.

    Returns:
        The list of chunks, in order.
    """
    text = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def ingest() -> tuple[int, int]:
    """Chunk and embed every markdown file in data/, replacing the persisted index.

    Wipes CHROMA_DIR first rather than calling delete_collection(): Chroma's
    delete_collection() only cleans up a collection's on-disk HNSW segment
    when it was already loaded into memory, so it otherwise leaves orphaned
    UUID-named folders behind on every reindex (a long-standing upstream bug,
    see https://github.com/chroma-core/chroma/issues/1009).

    Returns:
        A (file_count, chunk_count) tuple.
    """
    if CHROMA_DIR.exists():
        rmtree(CHROMA_DIR)
    client = PersistentClient(path=str(CHROMA_DIR))
    collection = client.create_collection(COLLECTION_NAME)

    files = sorted(f for f in DATA_DIR.rglob("*.md") if f.name != "README.md")
    documents, metadatas, embeddings, ids = [], [], [], []
    for file in files:
        source = str(file.relative_to(DATA_DIR)).replace("\\", "/")
        for i, chunk in enumerate(chunk_text(file.read_text(encoding="utf-8"))):
            documents.append(chunk)
            metadatas.append({"source": source})
            embeddings.append(embed(chunk))
            ids.append(f"{source}-{i}")

    collection.add(
        documents=documents, metadatas=metadatas, embeddings=embeddings, ids=ids
    )
    return len(files), len(documents)


def query(question: str, n_results: int = 5) -> list[dict[str, str]]:
    """Retrieve the most relevant knowledge base chunks for a question.

    Args:
        question: The student's question.
        n_results: How many chunks to retrieve.

    Returns:
        A list of {"text": ..., "source": ...} dicts, most relevant first.
    """
    client = PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except NotFoundError as e:
        raise RuntimeError(
            f"The RAG index ({COLLECTION_NAME!r}) does not exist. "
            "Run 'python retriever.py' first to index data/."
        ) from e

    results = collection.query(query_embeddings=[embed(question)], n_results=n_results)
    return [
        {"text": doc, "source": meta["source"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


if __name__ == "__main__":
    file_count, chunk_count = ingest()
    print(f"Indexed {chunk_count} chunks from {file_count} files into {CHROMA_DIR}")
