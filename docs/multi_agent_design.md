# Diseño multiagente (Corte 2)

Este documento define el equipo de agentes que reemplaza al tutor único de
[`agents/cubik_tutor/`](../agents/cubik_tutor/agent.py) para Corte 2. Refina la propuesta de
[PROPOSAL.md](../PROPOSAL.md) (un agente de triage más agentes que resuelven) con los patrones de la semana 8:
handoff con `sub_agents`, `AgentTool` y workflow agents.

El problema no cambia: tutoría de cálculo integral fundamentada en `data/` mediante RAG. Cambian dos cosas:

- Cada agente tiene una instrucción y unas tools más acotadas, en lugar de un solo prompt que cubre todos los
  casos.
- Los resultados matemáticos ya no dependen del modelo: se calculan y se comprueban con **SymPy**. El LLM explica
  y redacta el paso a paso, pero la respuesta final y el veredicto de si una respuesta es correcta salen de un
  cálculo simbólico.

## 1. Equipo

Un coordinador clasifica cada mensaje y lo envía a uno de cuatro especialistas. Las `description` van en inglés
porque son el texto exacto que ADK le muestra al modelo para enrutar.

| Agente | Responsabilidad | `description` | Tools |
|---|---|---|---|
| `cubik_coordinator` (raíz) | Clasifica el mensaje, rechaza lo que está fuera de alcance y guarda la preferencia de detalle. | Entry point of the integral calculus tutor: classifies each student message and routes it to the right specialist. | `set_explanation_level`, `AgentTool(progress_agent)` |
| `theory_agent` | Responde preguntas conceptuales. | Explains integral calculus concepts, definitions and theorems (e.g. why +C, the Fundamental Theorem), citing the knowledge base. Does not solve or check specific exercises. | `search_knowledge_base` |
| `solver_agent` | Resuelve un ejercicio que el estudiante trae sin respuesta. | Solves a specific integral the student asks to be solved, step by step, naming the technique and the rule behind each step. Does not answer theory questions or check the student's own answers. | `search_knowledge_base`, `solve_integral`, `check_antiderivative`, `check_definite_integral`, `log_practice_attempt` |
| `verifier_agent` | Revisa la respuesta (o el paso a paso) que trae el estudiante. | Checks the student's own answer to a specific integral against an exact SymPy computation, and explains the mistake if it is wrong. Does not solve exercises the student has not attempted. | `check_antiderivative`, `check_definite_integral`, `search_knowledge_base`, `log_practice_attempt` |
| `progress_agent` | Resume el progreso o reinicia el registro de práctica. | Summarizes the student's practice progress per technique, or resets their practice log. | `get_progress_summary`, `reset_practice_log` |

La frontera entre `solver_agent` y `verifier_agent` es qué trae el estudiante:

- Solo el ejercicio ("resuelve ∫ x·e^x dx") → `solver_agent`.
- El ejercicio **y su respuesta o su paso a paso** ("¿está bien? ∫ x·e^x dx = x·e^x − e^x + C") →
  `verifier_agent`.

`search_knowledge_base`, `set_explanation_level`, `log_practice_attempt`, `get_progress_summary` y
`reset_practice_log` son las tools de `agents/cubik_tutor/agent.py`. Se importan de ahí, no se duplican. Las tools
de SymPy son nuevas (sección 3).

## 2. Tipo de delegación

| Especialista | Delegación | Por qué |
|---|---|---|
| `theory_agent` | `sub_agents` (handoff) | Las preguntas de teoría traen preguntas de seguimiento, así que el especialista habla directamente con el estudiante. |
| `solver_agent` | `sub_agents` (handoff) | Resolver es una conversación de varios turnos: el control se queda con el solver hasta terminar el ejercicio. |
| `verifier_agent` | `sub_agents` (handoff) | El estudiante le habla directamente y suele seguir con "¿dónde me equivoqué?", así que el control se queda con el verificador. |
| `progress_agent` | `AgentTool`, llamado por el coordinador | Devuelve datos cortos que el coordinador incluye en su respuesta. Con un handoff quedaría como agente activo para el siguiente mensaje. |

El solver no necesita al verificador como agente para revisar su propio resultado: llama directamente a la
función `check_antiderivative` o `check_definite_integral`, que es determinista y no gasta llamadas al modelo.

## 3. Tools de SymPy

Viven en un módulo nuevo, `math_tools.py`, en la raíz del repo (junto a `retriever.py`). Reciben las
expresiones como texto en sintaxis de SymPy (`x*exp(x)`, `sin(x)**2`). El LLM se encarga de convertir la
notación del estudiante a esa sintaxis.

| Tool | Entrada | Criterio | Salida |
|---|---|---|---|
| `solve_integral` | integrando, variable y, opcionalmente, límites | `sympy.integrate` | La antiderivada o el valor, o un aviso si SymPy no encuentra forma cerrada. |
| `check_antiderivative` | integrando, respuesta candidata, variable | `simplify(diff(candidata, x) − integrando) == 0` | `correct: true/false`, y la derivada de la candidata para explicar el error. |
| `check_definite_integral` | integrando, límites, valor candidato | `simplify(candidato − integrate(integrando, (x, a, b))) == 0` | `correct: true/false` y el valor exacto. |

Estos son los "parámetros" con los que se decide si una respuesta está bien: derivar la antiderivada y comparar
con el integrando, o comparar con el valor exacto de la integral definida. La constante de integración no
afecta la comprobación, porque su derivada es 0.

Al principio solo se comprueba la **respuesta final**. Para señalar *en qué paso* está el error, el LLM tendría
que convertir cada paso del estudiante en una expresión, y SymPy tendría que comprobar que cada una es
equivalente a la anterior. Queda como mejora posterior.

## 4. Diagrama

```
                         ┌──────────────────────┐
                         │  cubik_coordinator   │  (triage + set_explanation_level)
                         └──────────┬───────────┘
        ┌──────────────────┬────────┴─────────┬──────────────────────┐
   [sub_agents]       [sub_agents]       [sub_agents]           [AgentTool]
        │                  │                  │                      │
┌───────▼──────┐   ┌───────▼──────┐   ┌───────▼────────┐     ┌───────▼────────┐
│ theory_agent │   │ solver_agent │   │ verifier_agent │     │ progress_agent │
│ (RAG search) │   │ (RAG, SymPy  │   │ (SymPy check,  │     │ (state tools)  │
│              │   │  solve/check)│   │  RAG)          │     │                │
└──────────────┘   └──────────────┘   └────────────────┘     └────────────────┘
```

## 5. Cambio de tema dentro de una conversación

Con `sub_agents`, ADK no devuelve el control al coordinador al final de cada turno. El siguiente mensaje lo
recibe el último agente que respondió, si puede transferir (`Runner._find_agent_to_run`). Ejemplos:

- Una pregunta de teoría seguida de un ejercicio: el ejercicio llega primero a `theory_agent`.
- Un ejercicio resuelto seguido de "¿y esto que hice yo está bien?": llega primero a `solver_agent`.
- Una verificación seguida de "¿cómo voy?": llega primero a `verifier_agent`.

Cada especialista puede llamar a `transfer_to_agent` hacia sus pares o hacia el coordinador; ADK agrega esos
destinos por defecto (`disallow_transfer_to_parent` y `disallow_transfer_to_peers` quedan en `False`). Para que
la transferencia ocurra:

- Las `description` dicen qué **no** hace cada especialista, porque el especialista también las lee para elegir
  a quién transferir.
- La instrucción de cada especialista dice explícitamente a quién transferir cuando el pedido no le toca:

| Si el pedido es... | `theory_agent` | `solver_agent` | `verifier_agent` |
|---|---|---|---|
| Teoría | — | → `theory_agent` | → `theory_agent` |
| Resolver un ejercicio | → `solver_agent` | — | → `solver_agent` |
| Revisar la respuesta del estudiante | → `verifier_agent` | → `verifier_agent` | — |
| Progreso, nivel de detalle u otra cosa | → `cubik_coordinator` | → `cubik_coordinator` | → `cubik_coordinator` |

`progress_agent` no tiene este problema: como es `AgentTool`, nunca queda como agente activo.

## 6. Estado

Se mantienen los alcances de la semana 7 (ver [adk_agent.md](adk_agent.md#2-tools-y-alcance-del-estado)).

| Clave | Quién escribe | Quién lee |
|---|---|---|
| `user:explanation_level` | Coordinador (`set_explanation_level`) | `theory_agent`, `solver_agent` y `verifier_agent` en su instrucción; `progress_agent` |
| `practice_log`, `app:total_attempts_all_users` | `solver_agent` y `verifier_agent` (`log_practice_attempt`); `progress_agent` (`reset_practice_log`) | `progress_agent` (`get_progress_summary`) |
| `temp:last_sources` | Los agentes que llaman a `search_knowledge_base` | — |

Quién registra cada intento:

- **`verifier_agent`**: siempre que revisa una respuesta del estudiante. `solved` es el resultado de la
  comprobación de SymPy, así que el registro de progreso deja de depender de lo que opine el modelo.
- **`solver_agent`**: cuando guía al estudiante en un ejercicio y el estudiante participa en la resolución, igual
  que el tutor de la semana 7.

`AgentTool` ejecuta al sub-agente en una sesión aparte, pero copia el estado de la sesión principal al empezar y
devuelve sus cambios (`state_delta`) al terminar. Por eso `progress_agent` puede leer y reiniciar
`practice_log` de la sesión real.

## 7. Formato de salida

- **Hablan con el estudiante:** `cubik_coordinator`, `theory_agent`, `solver_agent` y `verifier_agent`. Usan
  `prompts/system_prompt.txt` más un bloque con su rol en el equipo, así que su mensaje final sigue siendo el
  JSON de siempre (`answer`, `steps`, `rule`, `confidence`, `source`). El coordinador solo responde así cuando
  rechaza un mensaje fuera de alcance o reporta el progreso.
- **Respuesta interna:** `progress_agent` le devuelve al coordinador el resumen en texto, sin el JSON del
  estudiante.
- Cuando el resultado viene de SymPy, `confidence` refleja la comprobación: alta si SymPy confirmó la respuesta,
  baja si no encontró forma cerrada o no pudo demostrar la equivalencia.

## 8. Implementación prevista

- `math_tools.py` con las tres tools de SymPy, y `sympy` en `requirements.txt`.
- Agente nuevo en `agents/cubik_team/agent.py` con `root_agent = cubik_coordinator`. `agents/cubik_tutor/` no se
  toca: los dos aparecen en `adk web agents` y se pueden comparar.
- Mismo modelo y mismo switch Gemini/Ollama de `llm_client.py` que el tutor de la semana 7.
- Tests sin modelo:
  - `tests/test_math_tools.py`: respuestas correctas, incorrectas, con distinta constante de integración,
    equivalentes pero escritas distinto, integrales definidas y expresiones que SymPy no puede leer.
  - `tests/test_cubik_team.py`: estructura del árbol (hijos del coordinador, qué tools y `AgentTool` tiene cada
    agente) y que las tools compartidas sean las de `cubik_tutor`.
- Pruebas manuales en `adk web agents`: un mensaje por especialista, una sesión con cambio de tema (teoría →
  ejercicio → "¿está bien lo que hice?" → "¿cómo voy?") y una respuesta incorrecta del estudiante.

## 9. Riesgos

- **Conversión de notación.** El LLM tiene que traducir lo que escribe el estudiante a sintaxis de SymPy. Si
  traduce mal, SymPy comprueba otra expresión. La tool debe devolver la expresión que interpretó, para que el
  agente se la muestre al estudiante y se pueda detectar el error.
- **Equivalencias que `simplify` no demuestra.** Algunas expresiones trigonométricas equivalentes no se
  simplifican a 0. En ese caso la tool debe responder "no se pudo confirmar" en lugar de "incorrecto", para no
  marcar como errónea una respuesta correcta.
- **Integrales sin forma cerrada.** Si `sympy.integrate` devuelve la integral sin evaluar, el solver lo dice en
  lugar de inventar un resultado.
- **Transferencias que dependen del modelo.** Si un especialista responde fuera de su alcance en vez de
  transferir, por ejemplo `solver_agent` revisando la respuesta del estudiante sin pasarla al verificador, ese
  intento no queda registrado con el criterio de SymPy. Con un modelo local como `qwen2.5:14b` esto es más
  probable que con Gemini.
