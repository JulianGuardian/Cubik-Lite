"""RAG retriever for the Cubik-Lite Integral Calculus Tutor.

Indexes the markdown knowledge base under data/ into a persistent ChromaDB
collection, and retrieves the most relevant chunks for a student question:
a vector search fetches more candidates than needed, then an LLM re-ranks
them and keeps the best few. Embeddings and the re-ranking model come from
llm_client, so indexing, querying and re-ranking use whichever provider
(Gemini or local Ollama) is active.
"""

import json
import logging
from os import getenv
from pathlib import Path
from re import search
from shutil import rmtree

from chromadb import PersistentClient
from chromadb.errors import NotFoundError
from litellm import completion
from llm_client import CHAT_MODEL, USING_GEMINI, embed

DATA_DIR = Path(__file__).parent / "data"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "calculus_docs"

RERANK_ENABLED = getenv("RERANK_ENABLED", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
RERANK_CANDIDATES = int(getenv("RERANK_CANDIDATES", "15"))

RERANK_PROMPT = """\
You rank passages from an integral calculus knowledge base by how useful each one is to answer a question.

Question: {question}

Passages:
{passages}

Score every passage from 0 (irrelevant) to 10 (directly answers the question). Reply only with a JSON list of \
{n} numbers, one per passage, in the same order. Example for 3 passages: [2, 9, 0]"""

logger = logging.getLogger(__name__)


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


def _parse_scores(raw: str | None, expected: int) -> list[float]:
    """Read the re-ranker's reply: a JSON list with one number per passage.

    Args:
        raw: The model's reply, possibly with text around the list.
        expected: How many scores the reply must contain.

    Returns:
        The scores, in passage order.

    Raises:
        ValueError: If the reply has no list, isn't JSON, or has the wrong shape.
    """
    match = search(r"\[[^\[\]]*\]", raw or "")
    if match is None:
        raise ValueError(f"no score list in the reply: {raw!r}")
    scores = json.loads(match.group())
    if len(scores) != expected or not all(
        isinstance(s, (int, float)) and not isinstance(s, bool) for s in scores
    ):
        raise ValueError(f"expected {expected} numeric scores, got {scores!r}")
    return [float(s) for s in scores]


def rerank(
    question: str, chunks: list[dict[str, str]], top_k: int
) -> list[dict[str, str]]:
    """Reorder retrieved chunks by an LLM relevance score and keep the best ones.

    Never raises: if the model call fails or its reply can't be read, the
    vector-search order is kept so retrieval still works.

    Args:
        question: The student's question.
        chunks: Candidates from the vector search, most similar first.
        top_k: How many chunks to return.

    Returns:
        Up to top_k chunks, most relevant first. Ties keep the vector-search order.
    """
    if len(chunks) <= top_k:
        return chunks

    passages = "\n\n".join(f"[{i}] {chunk['text']}" for i, chunk in enumerate(chunks))
    prompt = RERANK_PROMPT.format(question=question, passages=passages, n=len(chunks))
    # Gemini 3+ deprecates sampling params; the local model needs 0 for stable scores.
    options = {} if USING_GEMINI else {"temperature": 0}
    try:
        response = completion(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            **options,
        )
        scores = _parse_scores(response.choices[0].message.content, len(chunks))
    except Exception as e:
        logger.warning("Re-ranking failed (%s); keeping vector-search order.", e)
        return chunks[:top_k]

    # sorted() is stable, so equal scores keep the vector-search order.
    order = sorted(range(len(chunks)), key=lambda i: -scores[i])
    return [chunks[i] for i in order[:top_k]]


def query(question: str, n_results: int = 5) -> list[dict[str, str]]:
    """Retrieve the most relevant knowledge base chunks for a question.

    With re-ranking enabled (the default), the vector search fetches
    RERANK_CANDIDATES chunks and rerank() keeps the best n_results.

    Args:
        question: The student's question.
        n_results: How many chunks to return.

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

    n_candidates = max(n_results, RERANK_CANDIDATES) if RERANK_ENABLED else n_results
    results = collection.query(
        query_embeddings=[embed(question)], n_results=n_candidates
    )
    chunks = [
        {"text": doc, "source": meta["source"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
    return rerank(question, chunks, n_results) if RERANK_ENABLED else chunks


if __name__ == "__main__":
    file_count, chunk_count = ingest()
    print(f"Indexed {chunk_count} chunks from {file_count} files into {CHROMA_DIR}")
