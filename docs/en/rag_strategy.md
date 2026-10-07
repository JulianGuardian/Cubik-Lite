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
3. **Similarity retrieval**: for each question, the question is embedded and the `n_results` most similar
   chunks in the collection are queried.
4. **Grounded answer**: the retrieved chunks (with their source) are prepended to the student's question before
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
  area problem) need that margin. With such a small corpus, 5 results do not add significant noise.

---

## 4. Alternatives considered

| Strategy | Description | Advantages | Disadvantages | Decision |
|---|---|---|---|---|
| **Semantic chunking** (by heading/section) | Split while respecting the markdown structure of each file. | More thematically coherent chunks. | Requires a markdown parser and additional logic; the corpus is already well segmented by file/topic. | **Discarded**: unnecessary complexity for the current scope. |
| **Chunking without overlap** | `overlap=0`. | Fewer chunks, less storage. | Higher risk of cutting a formula or an explanation in half. | **Discarded**: the corpus is dense in LaTeX. |
| **FAISS instead of ChromaDB** | In-memory/flat-file vector index. | Very fast, lightweight dependency. | No built-in persistence or source metadata; they have to be built by hand. | **Discarded**: ChromaDB already solves both. |
| **Low `n_results` (2-3)** | Retrieve fewer chunks per question. | Shorter context, more focused answers. | May not cover questions that require two chunks or two related files. | **Discarded**: insufficient for questions that combine sources. |
| **Fixed-size chunking + ChromaDB, `n_results=5`** | See section 2. | Simple, deterministic, covers complete topics and cross-topic questions, persistent. | Not as precise as semantic chunking on larger corpora. | **Selected**. |

---

## 5. Configuration parameters

| Parameter | Type | Default value | Description |
|---|---|---|---|
| `chunk_size` | `int` | `600` | Maximum characters per chunk. |
| `overlap` | `int` | `100` | Characters shared between consecutive chunks. |
| `n_results` | `int` | `5` | Chunks retrieved per question. |
| Embedding model | `str` | `gemini/gemini-embedding-001` (Gemini) or `ollama/nomic-embed-text` (local) | Selected automatically by `llm_client.py` depending on whether `GEMINI_API_KEY` is set. |

---

## 6. Implementation

- **Indexing and retrieval**: [`retriever.py`](../../retriever.py) — `chunk_text()`, `ingest()`, `query()`.
- **Chat integration**: [`main.py`](../../main.py) — `send_message()` retrieves context and prepends it to the
  current turn before calling the LLM, without inflating the history managed by `SlidingWindowManager`
  (see [`context_strategy.md`](context_strategy.md)).
- **Citation contract**: [`prompts/system_prompt.txt`](../../prompts/system_prompt.txt), GROUNDING section and
  `"source"` field.
- **Unit tests**: [`test_retriever.py`](../../tests/test_retriever.py) covers `chunk_text()`; actual indexing
  and retrieval (which depend on an active embedding provider) are verified manually with
  `python retriever.py` and `python main.py`.
