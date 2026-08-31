# Estrategia de RAG

## 1. Introducción

Cubik-Lite debe fundamentar sus respuestas en el material de referencia de cálculo integral (`data/`) en lugar
de depender solo del conocimiento general del modelo, y citar la fuente concreta usada en cada respuesta. Esto
exige una etapa de **indexación** (una vez, sobre los documentos) y una de **recuperación** (en cada pregunta
del estudiante).

---

## 2. Estrategia elegida: Chunking de tamaño fijo con overlap + ChromaDB

### Mecánica de funcionamiento:

1. **Chunking de ventana fija**: cada archivo de `data/*.md` se trocea en fragmentos de `chunk_size` caracteres,
   con `overlap` caracteres compartidos entre fragmentos consecutivos, tras normalizar espacios en blanco.
2. **Indexación persistente**: cada chunk se embebe con `llm_client.embed()` y se guarda en una colección de
   ChromaDB persistida en `chroma_db/`, junto con metadata `source` (la ruta relativa del archivo de origen).
3. **Recuperación por similitud**: ante cada pregunta, se embebe la pregunta y se consultan los `n_results`
   chunks más similares de la colección.
4. **Respuesta fundamentada**: los chunks recuperados (con su fuente) se anteponen a la pregunta del estudiante
   antes de enviarla al LLM; el system prompt instruye a responder solo con base en ese contexto y a citar la
   fuente en el campo `"source"` de la respuesta.

---

## 3. ¿Por qué chunking de tamaño fijo + ChromaDB?

- **Corpus pequeño y estructurado**: ~24k caracteres en 11 archivos temáticos (reglas, técnicas, aplicaciones).
  No justifica la complejidad de un chunker semántico.
- **Contenido con fórmulas LaTeX**: un `chunk_size` y `overlap` generosos (600/100) reducen la probabilidad de
  cortar una fórmula a la mitad entre dos chunks, algo especialmente costoso en un dominio matemático donde una
  fórmula truncada cambia el significado de la respuesta.
- **ChromaDB sobre FAISS**: persistencia y filtrado por metadata (`source`) con una API simple, sin tener que
  implementar el guardado del índice ni el mapeo chunk-a-fuente a mano.
- **`n_results=5`**: con `chunk_size=600`/`overlap=100` sobre ~24k caracteres, cada archivo produce en promedio
  ~5 chunks. Un `n_results` más bajo (p. ej. 3) arriesga no cubrir un tema completo de un solo archivo, y las
  preguntas que combinan información de dos chunks o dos archivos relacionados (p. ej. una técnica de
  integración aplicada a un problema de área) necesitan ese margen. Con un corpus tan pequeño, 5 resultados no
  meten ruido significativo.

---

## 4. Alternativas consideradas

| Estrategia | Descripción | Ventajas | Desventajas | Decisión |
|---|---|---|---|---|
| **Chunking semántico** (por encabezado/sección) | Trocear respetando la estructura markdown de cada archivo. | Chunks temáticamente más coherentes. | Requiere un parser markdown y lógica adicional; el corpus ya está bien segmentado por archivo/tema. | **Descartada**: complejidad innecesaria para el alcance actual. |
| **Chunking sin overlap** | `overlap=0`. | Menos chunks, menos almacenamiento. | Mayor riesgo de cortar una fórmula o una explicación a la mitad. | **Descartada**: el corpus es denso en LaTeX. |
| **FAISS en vez de ChromaDB** | Índice vectorial en memoria/archivo plano. | Muy rápido, dependencia ligera. | Sin persistencia ni metadata de fuente integradas; hay que construirlas a mano. | **Descartada**: ChromaDB ya resuelve ambas. |
| **`n_results` bajo (2-3)** | Recuperar menos chunks por pregunta. | Contexto más corto, respuestas más enfocadas. | Puede no cubrir preguntas que requieren dos chunks o dos archivos relacionados. | **Descartada**: insuficiente para el caso de preguntas que combinan fuentes. |
| **Chunking de tamaño fijo + ChromaDB, `n_results=5`** | Ver sección 2. | Simple, determinista, cubre temas completos y preguntas cruzadas, persistente. | No es tan preciso como un chunking semántico en corpus más grandes. | **Seleccionada**. |

---

## 5. Parámetros de configuración

| Parámetro | Tipo | Valor por defecto | Descripción |
|---|---|---|---|
| `chunk_size` | `int` | `600` | Caracteres máximos por chunk. |
| `overlap` | `int` | `100` | Caracteres compartidos entre chunks consecutivos. |
| `n_results` | `int` | `5` | Chunks recuperados por pregunta. |
| Modelo de embeddings | `str` | `gemini/gemini-embedding-001` (Gemini) o `ollama/nomic-embed-text` (local) | Seleccionado automáticamente por `llm_client.py` según haya o no `GEMINI_API_KEY`. |

---

## 6. Implementación

- **Indexación y recuperación**: [`retriever.py`](../retriever.py) — `chunk_text()`, `ingest()`, `query()`.
- **Integración en el chat**: [`main.py`](../main.py) — `send_message()` recupera contexto y lo antepone al
  turno actual antes de llamar al LLM, sin inflar el historial gestionado por `SlidingWindowManager`
  (ver [`context_strategy.md`](context_strategy.md)).
- **Contrato de citación**: [`prompts/system_prompt.txt`](../prompts/system_prompt.txt), sección GROUNDING y
  campo `"source"`.
- **Pruebas unitarias**: [`test_retriever.py`](../tests/test_retriever.py) cubre `chunk_text()`; la indexación y
  recuperación reales (que dependen de un proveedor de embeddings activo) se verifican a mano con
  `python retriever.py` y `python main.py`.
