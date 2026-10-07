"""Tests for chunk_text() and the re-ranking step of retriever.py.

Only network-free logic is covered here: the re-ranker's model call and the
Chroma client are monkeypatched. Real indexing and retrieval depend on a live
embedding provider (Gemini or Ollama) and are verified manually via
`python retriever.py` and `python main.py`.
"""

from types import SimpleNamespace

import pytest
import retriever
from retriever import _parse_scores, chunk_text, rerank


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


def make_chunks(count: int) -> list[dict[str, str]]:
    """Chunks named c0..c{count-1}, in vector-search order."""
    return [{"text": f"text {i}", "source": f"file{i}.md"} for i in range(count)]


def fake_completion(reply: str, calls: list | None = None):
    """A stand-in for litellm.completion that always answers with reply."""

    def completion(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        message = SimpleNamespace(content=reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    return completion


def test_parse_scores_reads_a_plain_list() -> None:
    """Verify a bare JSON list becomes floats in order."""
    assert _parse_scores("[1, 9.5, 0]", 3) == [1.0, 9.5, 0.0]


def test_parse_scores_ignores_text_around_the_list() -> None:
    """Verify a reply with prose or a code fence around the list still parses."""
    assert _parse_scores("Here you go:\n```json\n[3, 7]\n```", 2) == [3.0, 7.0]


@pytest.mark.parametrize(
    "raw",
    ["no list here", "[1, 2]", "[1, 2, 3, 4]", '[1, "high", 3]', "[1, true, 3]", "[1, 2,", None],
)
def test_parse_scores_rejects_unusable_replies(raw: str | None) -> None:
    """Verify a missing list, wrong length or non-numeric score raises ValueError."""
    with pytest.raises(ValueError):
        _parse_scores(raw, 3)


def test_rerank_orders_by_score_and_keeps_top_k(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the highest scores come first and the rest are dropped."""
    monkeypatch.setattr(retriever, "completion", fake_completion("[1, 9, 0, 5]"))
    chunks = make_chunks(4)

    result = rerank("question", chunks, top_k=2)

    assert result == [chunks[1], chunks[3]]


def test_rerank_ties_keep_vector_search_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify equal scores don't shuffle the vector-search order."""
    monkeypatch.setattr(retriever, "completion", fake_completion("[5, 5, 5, 5]"))
    chunks = make_chunks(4)

    assert rerank("question", chunks, top_k=3) == chunks[:3]


def test_rerank_prompt_includes_question_and_numbered_passages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the model is shown the question and every candidate with its index."""
    calls: list = []
    monkeypatch.setattr(retriever, "completion", fake_completion("[1, 2, 3]", calls))

    rerank("why +C?", make_chunks(3), top_k=2)

    prompt = calls[0]["messages"][0]["content"]
    assert "why +C?" in prompt
    assert "[0] text 0" in prompt and "[2] text 2" in prompt


def test_rerank_falls_back_to_vector_order_when_the_model_call_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify an API error (e.g. Gemini 503) keeps the original order and logs a warning."""

    def failing_completion(**kwargs):
        raise RuntimeError("503 UNAVAILABLE")

    monkeypatch.setattr(retriever, "completion", failing_completion)
    chunks = make_chunks(4)

    with caplog.at_level("WARNING"):
        result = rerank("question", chunks, top_k=2)

    assert result == chunks[:2]
    assert "Re-ranking failed" in caplog.text


def test_rerank_falls_back_when_the_reply_is_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify an unreadable reply keeps the original order."""
    monkeypatch.setattr(retriever, "completion", fake_completion("I cannot rank these."))
    chunks = make_chunks(4)

    assert rerank("question", chunks, top_k=2) == chunks[:2]


def test_rerank_skips_the_model_when_there_is_nothing_to_choose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify no model call is made when candidates <= top_k."""
    calls: list = []
    monkeypatch.setattr(retriever, "completion", fake_completion("[1, 2]", calls))
    chunks = make_chunks(2)

    assert rerank("question", chunks, top_k=5) == chunks
    assert calls == []


class FakeCollection:
    """A Chroma collection that records the n_results it was asked for."""

    def __init__(self) -> None:
        self.requested: list[int] = []

    def query(self, query_embeddings: list, n_results: int) -> dict:
        self.requested.append(n_results)
        chunks = make_chunks(n_results)
        return {
            "documents": [[c["text"] for c in chunks]],
            "metadatas": [[{"source": c["source"]} for c in chunks]],
        }


@pytest.fixture
def collection(monkeypatch: pytest.MonkeyPatch) -> FakeCollection:
    """Patch retriever to use a fake Chroma collection and a fake embedding."""
    fake = FakeCollection()
    client = SimpleNamespace(get_collection=lambda name: fake)
    monkeypatch.setattr(retriever, "PersistentClient", lambda path: client)
    monkeypatch.setattr(retriever, "embed", lambda text: [0.0])
    return fake


def test_query_fetches_extra_candidates_and_reranks_them(
    collection: FakeCollection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify query() asks Chroma for RERANK_CANDIDATES and returns the re-ranked top n_results."""
    monkeypatch.setattr(retriever, "RERANK_ENABLED", True)
    monkeypatch.setattr(retriever, "RERANK_CANDIDATES", 6)
    scores = [0, 0, 0, 0, 0, 9]
    monkeypatch.setattr(retriever, "completion", fake_completion(str(scores)))

    result = retriever.query("question", n_results=3)

    assert collection.requested == [6]
    assert len(result) == 3
    assert result[0]["source"] == "file5.md"


def test_query_without_reranking_returns_vector_order(
    collection: FakeCollection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify RERANK_ENABLED=0 fetches exactly n_results and never calls the model."""
    calls: list = []
    monkeypatch.setattr(retriever, "RERANK_ENABLED", False)
    monkeypatch.setattr(retriever, "completion", fake_completion("[]", calls))

    result = retriever.query("question", n_results=3)

    assert collection.requested == [3]
    assert [c["source"] for c in result] == ["file0.md", "file1.md", "file2.md"]
    assert calls == []
