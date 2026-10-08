# RAG Strategy

## 1. Introduction

Cubik-Lite must ground its answers in the integral calculus reference material (`data/`) instead of relying
only on the model's general knowledge, and cite the specific source used in each answer. This requires an
**indexing** stage (once, over the documents) and a **retrieval** stage (on every student question).

---

## 2. Chosen strategy: Fixed-size chunking with overlap + ChromaDB

### How it works:

1. **Fixed-window chunking**: each file in `data/*.md` is split into chunks of `chunk_size` characters, with
   `overlap` characters shared between consecutive chunks, after normalizing whitespace.
2. **Persistent indexing**: each chunk is embedded with `llm_client.embed()` and stored in a ChromaDB
   collection persisted in `chroma_db/`, together with `source` metadata (the relative path of the source file).
3. **Similarity retrieval**: for each question, the question is embedded and the `RERANK_CANDIDATES` most
   similar chunks in the collection are queried (`n_results` if re-ranking is off).
4. **LLM re-ranking**: one call to the chat model scores each candidate from 0 to 10 against the question, and
   the `n_results` best are kept (ties keep the vector-search order). If the call fails or its reply can't be
   read, the vector-search order is kept, so retrieval never breaks.
5. **Grounded answer**: the retrieved chunks (with their source) are prepended to the student's question before
   it is sent to the LLM; the system prompt instructs the model to answer only based on that context and to
   cite the source in the `"source"` field of the response.

---

## 3. Why fixed-size chunking + ChromaDB?

- **Small, structured corpus**: ~24k characters across 11 topic files (rules, techniques, applications). It
  does not justify the complexity of a semantic chunker.
- **Content with LaTeX formulas**: a generous `chunk_size` and `overlap` (600/100) reduce the likelihood of
  cutting a formula in half between two chunks, which is especially costly in a mathematical domain where a
  truncated formula changes the meaning of the answer.
- **ChromaDB over FAISS**: persistence and metadata filtering (`source`) with a simple API, without having to
  implement index saving or the chunk-to-source mapping by hand.
- **`n_results=5`**: with `chunk_size=600`/`overlap=100` over ~24k characters, each file produces ~5 chunks on
  average. A lower `n_results` (e.g. 3) risks not covering a complete topic from a single file, and questions
  that combine information from two chunks or two related files (e.g. an integration technique applied to an
  area problem) need that margin.
- **Re-ranking on top of the vector search**: embeddings return chunks that are "similar", not necessarily the
  most useful. For "what is the integral of 2x dx?" three of the five vector results were unrelated (integration
  by parts of `ln(x)`, a radical substitution, the Fundamental Theorem). Fetching 15 candidates and letting the
  model pick the best 5 moves the rules that answer the question to the top and drops most of that noise. It is
  not a correctness check: results and verdicts still come from SymPy (`math_tools.py`).
- **Why an LLM and not a cross-encoder**: the project already calls the chat model through `litellm` (Gemini or
  Ollama), so re-ranking adds no dependency and works with either provider. A cross-encoder needs
  `sentence-transformers` and `torch`, heavy for 54 chunks.

---

## 4. Alternatives considered

| Strategy | Description | Advantages | Disadvantages | Decision |
|---|---|---|---|---|
| **Semantic chunking** (by heading/section) | Split while respecting the markdown structure of each file. | More thematically coherent chunks. | Requires a markdown parser and additional logic; the corpus is already well segmented by file/topic. | **Discarded**: unnecessary complexity for the current scope. |
| **Chunking without overlap** | `overlap=0`. | Fewer chunks, less storage. | Higher risk of cutting a formula or an explanation in half. | **Discarded**: the corpus is dense in LaTeX. |
| **FAISS instead of ChromaDB** | In-memory/flat-file vector index. | Very fast, lightweight dependency. | No built-in persistence or source metadata; they have to be built by hand. | **Discarded**: ChromaDB already solves both. |
| **Low `n_results` (2-3)** | Retrieve fewer chunks per question. | Shorter context, more focused answers. | May not cover questions that require two chunks or two related files. | **Discarded**: insufficient for questions that combine sources. |
| **Cross-encoder re-ranking** | A local model (e.g. `sentence-transformers`) scores each (question, chunk) pair. | Deterministic, no extra model call per query. | Adds `sentence-transformers` and `torch`; one more model to download and run. | **Discarded**: too heavy for a 54-chunk corpus. |
| **No re-ranking** | Use the vector-search order as is. | No extra call, deterministic. | Unrelated chunks reach the model and the agents' "answer only from the chunks" rule. | **Discarded**: observed noise in the top 5. |
| **Fixed-size chunking + ChromaDB, `n_results=5`, LLM re-ranking of 15 candidates** | See section 2. | Simple, covers complete topics and cross-topic questions, persistent, better top 5. | One more model call per retrieval (latency and cost); LLM scores are not fully deterministic. | **Selected**. |

---

## 5. Configuration parameters

| Parameter | Type | Default value | Description |
|---|---|---|---|
| `chunk_size` | `int` | `600` | Maximum characters per chunk. |
| `overlap` | `int` | `100` | Characters shared between consecutive chunks. |
| `n_results` | `int` | `5` | Chunks returned per question (after re-ranking). |
| `RERANK_CANDIDATES` | `int` (env var) | `15` | Chunks fetched from the vector search for the re-ranker to choose from. |
| `RERANK_ENABLED` | `bool` (env var) | `1` | `0`/`false`/`no`/`off` skips re-ranking and returns the vector-search top `n_results`. |
| Embedding model | `str` | `gemini/gemini-embedding-001` (Gemini) or `ollama/nomic-embed-text` (local) | Selected automatically by `llm_client.py` depending on whether `GEMINI_API_KEY` is set. |

---

## 6. Implementation

- **Indexing and retrieval**: [`retriever.py`](../../retriever.py) — `chunk_text()`, `ingest()`, `query()`,
  and the re-ranking helpers `rerank()` and `_parse_scores()`. Every consumer goes through `query()`: `main.py`
  and the `search_knowledge_base` tool shared by `cubik_tutor` and the team's theory, solver and verifier
  agents, so none of them changed.
- **Chat integration**: [`main.py`](../../main.py) — `send_message()` retrieves context and prepends it to the
  current turn before calling the LLM, without inflating the history managed by `SlidingWindowManager`
  (see [`context_strategy.md`](context_strategy.md)).
- **Citation contract**: [`prompts/system_prompt.txt`](../../prompts/system_prompt.txt), GROUNDING section and
  `"source"` field.
- **Unit tests**: [`test_retriever.py`](../../tests/test_retriever.py) covers `chunk_text()` and re-ranking
  (score parsing, ordering, fallbacks, candidate count) with the model call and Chroma faked; actual indexing
  and retrieval (which depend on an active embedding provider) are verified manually with
  `python retriever.py` and `python main.py`.

### Notes from trying it with Gemini
- The model's scores vary a little between runs, even with `temperature=0`, so the exact order of the weaker
  chunks (positions 4-5) can change. The best three were the same in every run for the example question above.
- Gemini sometimes answers 503 under load; the fallback then returns the plain vector-search order and logs a
  warning.
- The solver and verifier prompts ask the agents to search with a short Spanish phrase naming the technique
  ("integración por partes") instead of SymPy syntax like `x*exp(x)`, which makes a poor query for both the
  embeddings and the re-ranker.
