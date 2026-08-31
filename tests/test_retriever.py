"""Tests for the chunk_text() function in retriever.py.

Only pure, network-free logic is covered here. ingest()/query() depend on a
live embedding provider (Gemini or Ollama) and are verified manually via
`python retriever.py` and `python main.py`.
"""

from retriever import chunk_text


def test_chunk_text_respects_chunk_size() -> None:
    """Verify no chunk exceeds the requested chunk_size."""
    text = "word " * 500
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_chunk_text_overlap_shares_content() -> None:
    """Verify consecutive chunks share the requested overlap."""
    text = "0123456789" * 20
    chunks = chunk_text(text, chunk_size=50, overlap=10)

    for i in range(len(chunks) - 1):
        assert chunks[i][-10:] == chunks[i + 1][:10]


def test_chunk_text_normalizes_whitespace() -> None:
    """Verify newlines/tabs/repeated spaces collapse to single spaces."""
    text = "Line one.\n\n  Line   two.\tLine three."
    chunks = chunk_text(text, chunk_size=1000, overlap=0)

    assert len(chunks) == 1
    assert chunks[0] == "Line one. Line two. Line three."


def test_chunk_text_short_input_returns_single_chunk() -> None:
    """Verify text shorter than chunk_size returns exactly one chunk."""
    chunks = chunk_text("A short sentence.", chunk_size=600, overlap=100)

    assert chunks == ["A short sentence."]


def test_chunk_text_empty_input_returns_no_chunks() -> None:
    """Verify empty text produces an empty chunk list."""
    assert chunk_text("", chunk_size=600, overlap=100) == []
