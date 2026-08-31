# Cubik-Lite — Tutor de Cálculo Integral

Asistente conversacional de tutoría para cálculo integral. Responde preguntas de teoría y guía la resolución de
ejercicios paso a paso, citando la regla o técnica aplicada, y fundamenta sus respuestas en una base de
conocimiento propia mediante RAG en vez de depender solo del conocimiento general del modelo. Ver
[PROPOSAL.md](PROPOSAL.md) para el alcance completo.

## Arquitectura

| Pieza | Archivo | Qué hace |
|---|---|---|
| Chat | [`main.py`](main.py) | Loop interactivo de terminal. |
| Selección de modelo | [`llm_client.py`](llm_client.py) | Gemini si hay `GEMINI_API_KEY`, si no un modelo local vía Ollama. |
| Contexto conversacional | [`context_manager.py`](context_manager.py) | Ventana deslizante de turnos + presupuesto de caracteres. Ver [docs/context_strategy.md](docs/context_strategy.md). |
| RAG | [`retriever.py`](retriever.py) | Indexa `data/` en ChromaDB y recupera los chunks más relevantes por pregunta. Ver [docs/rag_strategy.md](docs/rag_strategy.md). |
| System prompt | [`prompts/system_prompt.txt`](prompts/system_prompt.txt) | Rol, alcance, reglas de rechazo y formato de salida JSON. |
| Base de conocimiento | [`data/`](data/README.md) | Reglas, técnicas y aplicaciones de integración, en Markdown. |

## Setup

1. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Copia `.env.example` a `.env`:

   ```bash
   cp .env.example .env
   ```

   `GEMINI_API_KEY` es **opcional**. Si la defines (consigue una key gratis en
   https://aistudio.google.com/apikey), el asistente usa la API de Gemini para chat y embeddings. Si la dejas
   vacía o con el placeholder, cae automáticamente a un modelo local vía [Ollama](https://ollama.com/):

   ```bash
   ollama pull qwen2.5:14b
   ollama pull nomic-embed-text
   ```

3. Construye el índice de RAG (hay que rehacerlo si cambia el contenido de `data/`):

   ```bash
   python retriever.py
   ```

4. Corre el chat:

   ```bash
   python main.py
   ```

   Comandos dentro del chat: `salir` para terminar, `limpiar` para reiniciar el historial.

## Tests

```bash
pytest tests/
```

Cubre el gestor de contexto (`context_manager.py`) y el chunking del RAG (`retriever.py`). La indexación y
recuperación reales, que dependen de un proveedor de embeddings activo (Gemini o Ollama), se verifican a mano
corriendo `python retriever.py` y `python main.py`.
