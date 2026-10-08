# Agente de Google ADK

## 1. Qué cambia respecto a `main.py`

`agents/cubik_tutor/` es el mismo tutor de `main.py` (mismo system prompt, mismo RAG sobre `data/`, mismo
switch Gemini/Ollama de `llm_client.py`), pero corriendo como agente de Google ADK:

| | `main.py` | Agente ADK |
|---|---|---|
| Recuperación | `main.py` llama a `retriever.query()` y antepone el bloque "Contexto recuperado" a cada pregunta. | El modelo decide llamar a la tool `search_knowledge_base`, que envuelve `retriever.query()`. |
| Historial | `SlidingWindowManager` en memoria del proceso. | `SessionService` de ADK: eventos y estado por sesión. |
| Loop | Una sola llamada a `completion()` por turno. | El `Runner` ejecuta el ciclo modelo → tool → modelo hasta la respuesta final. |
| Modelo | `litellm.completion(CHAT_MODEL)` | Gemini nativo de ADK si hay `GEMINI_API_KEY`; si no, `LiteLlm` hacia Ollama. |
| Salida | JSON del system prompt. | El mismo JSON (el agente reutiliza `prompts/system_prompt.txt`). |

`main.py` no se tocó: el chat de Corte 1 sigue funcionando igual.

## 2. Tools y alcance del estado

ADK arma el esquema de cada tool a partir de sus type hints y su docstring. `tool_context` lo inyecta ADK y no
se expone al modelo.

| Tool | Clave de estado | Alcance | Por qué ese alcance |
|---|---|---|---|
| `search_knowledge_base` | `temp:last_sources` | Turno | Las fuentes recuperadas solo importan para la respuesta actual; en el siguiente turno se vuelve a buscar. |
| `set_explanation_level` | `user:explanation_level` | Usuario (todas sus sesiones) | Es una preferencia del estudiante, no de una conversación ni de todos los estudiantes. |
| `log_practice_attempt` | `practice_log` | Sesión | El registro de práctica pertenece a esta conversación; una sesión nueva empieza de cero. |
| `log_practice_attempt` | `app:total_attempts_all_users` | App (todos los usuarios) | Es un contador global del tutor, compartido por todos. |
| `get_progress_summary` | lee las anteriores | — | Solo lectura. |
| `reset_practice_log` | `practice_log` | Sesión | Limpia únicamente la sesión; no toca `user:` ni `app:`. Pide aprobación si hay intentos registrados. |

La instrucción del agente inyecta `{user:explanation_level?}` para ajustar el detalle de los `steps`. El `?`
hace que la variable sea opcional: si el estudiante aún no eligió nivel, se reemplaza por vacío en vez de
fallar.

### Aprobación antes de reiniciar la práctica

`reset_practice_log` borra el registro de práctica de la sesión y no se puede deshacer, así que es la tool con un
punto de interrupción (*human-in-the-loop*): ADK pausa la ejecución y le pide al estudiante que apruebe antes de
correrla.

- **Cómo:** `agent.py` la envuelve en `SpanishConfirmationTool` (`reset_practice_log_tool`), una subclase mínima
  de `FunctionTool` con `require_confirmation=has_practice_attempts`. `has_practice_attempts` lee `practice_log`
  del estado, así que **solo se pide aprobación si hay algo que perder**; con el registro vacío se ejecuta sin
  preguntar. ADK llama a la condición con los mismos argumentos que a la tool, por eso su parámetro se llama
  `tool_context`.
- **Mensaje en español:** ADK escribe el texto de la solicitud en inglés dentro de `FunctionTool.run_async` y no
  ofrece una opción para cambiarlo. `SpanishConfirmationTool` solo reemplaza ese primer paso, pedir la
  aprobación con `tool_context.request_confirmation(hint=...)`, y el resto (aprobada, rechazada, ejecutar) lo sigue
  haciendo `super().run_async`. `reset_confirmation_hint` arma el texto con la cantidad de intentos que se
  borrarían.
- **Qué pasa:** la primera llamada no ejecuta la función. ADK emite un evento `adk_request_confirmation` y el
  modelo recibe `This tool call requires confirmation`. El cliente responde `confirmed: true` o `false`. Si
  aprueba, la tool corre; si rechaza, devuelve `This tool call is rejected.` y el registro queda intacto.
- **Prompt:** la instrucción le dice al modelo que llame la tool de inmediato y que no pida confirmación en su
  propio mensaje. Si lo hace, la "aprobación" la maneja el texto del modelo y no el mecanismo de ADK.
- **Equipo multiagente:** el coordinador de `cubik_team` tiene esta misma tool directamente; ver
  [multi_agent_design.md](multi_agent_design.md), sección 6.
- **Cómo probarlo:** `adk run agents/cubik_tutor` (o `agents/cubik_team`). Pide "Verifica mi respuesta: la integral
  de x^2 dx es x^3/3 + C" para registrar un intento y luego "quiero empezar mi práctica de nuevo". La terminal
  muestra `[HITL confirm]` y espera `yes`; cualquier otra respuesta rechaza. En `adk web` aparece como una
  tarjeta `adk_request_confirmation` con la casilla «Confirmed» y el botón «Submit».
- **Limitaciones:** solo el mensaje está en español. Las etiquetas de la UI web ("Confirmed", "Submit",
  "Payload") y la línea `Type "yes" to confirm` del CLI son de ADK y no se pueden cambiar desde el agente; por eso
  el mensaje nombra esos botones. La confirmación de tools está marcada como experimental en ADK 2.9.

`tests/test_adk_tools.py` cubre la condición y los cuatro casos (registro vacío, aprobación pendiente, aprobada y
rechazada) con el contexto simulado.

## 3. Cómo correrlo

Desde la raíz del repo, con el índice de RAG ya construido (`python retriever.py`):

```bash
adk web agents
```

Prueba de alcances en la UI:

1. "Prefiero explicaciones detalladas. ¿Cuál es la integral de x·e^x dx?" → el trace muestra
   `set_explanation_level` y `search_knowledge_base`, y la respuesta cita `techniques/integration_by_parts.md`.
2. "Ya lo resolví, anótalo" → `log_practice_attempt`.
3. Abre una **sesión nueva con el mismo usuario**: `user:explanation_level` y `app:total_attempts_all_users`
   siguen ahí, y `practice_log` está vacío.

Con el `InMemorySessionService` por defecto, todo se pierde al reiniciar `adk web`. Para conservarlo:
`adk web agents --session_service_uri sqlite:///adk_sessions.db`.

`agent.py` agrega la raíz del repo a `sys.path` porque `adk` solo agrega `agents/`, y el agente necesita
importar `retriever.py` y `llm_client.py`. El agente vive en `agents/` y no en la raíz para que el selector de
`adk web` no liste `tests/` (que tiene `__init__.py`) como si fuera un agente.

## 4. Relación con la propuesta de Corte 2

[PROPOSAL.md](../../PROPOSAL.md) plantea un **triage agent** que clasifica la pregunta y **solver agents** por
técnica. Este agente es la base de ese diseño:

- `cubik_tutor` pasa a ser el solver genérico. Los solvers por técnica serían copias con una instrucción más
  angosta y la misma tool `search_knowledge_base`.
- El triage se agrega como `root_agent` con estos agentes en `sub_agents` (semana 8, multiagente).
- `practice_log` y `get_progress_summary` le dan al triage información sobre qué técnicas practica el
  estudiante y en cuáles falla.
