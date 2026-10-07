# Project Proposal

This project is a conversational assistant for calculus tutoring. It answers theoretical questions and walks through worked exercises step by step, citing the specific rule or theorem behind each step rather than just giving a final answer. It targets students taking an introductory calculus course who need on-demand practice and explanations outside of class hours. The knowledge base will be built from calculus lecture notes and textbook chapters covering limits, derivatives, and integrals, retrieved via RAG so that answers stay grounded in the assigned course material instead of the model's general knowledge. Given a student's exercise or question, the assistant returns both the final answer and the step-by-step reasoning behind it.

For Corte 1, the assistant's scope has been narrowed to **integral calculus** (indefinite/definite integrals, integration techniques, and applications). See [prompts/system_prompt.txt](prompts/system_prompt.txt) for the full system prompt defining its role, scope, refusal behavior, and output format.

## Example Questions

With RAG grounding answers in [data/](data/README.md) (see [README.md](README.md) for setup), the assistant can answer questions such as:

- What is the integral of x·e^x dx, and which technique applies?
- Find the area under the curve y = sin(x) from 0 to π.
- Why do we add a constant of integration (+C) to indefinite integrals?

## Corte 2: Multi-Agent Candidate

For Corte 2, Cubik-Lite becomes a multi-agent system built with Google ADK that keeps solving the same real problem — grounded calculus tutoring — but splits the work across specialized agents instead of one monolithic prompt. A **coordinator** receives every student message and routes it to a **theory**, **solver** or **verifier** specialist, and asks a **progress** agent for the student's practice summary. The solver and verifier get their results from SymPy instead of the model: the solver computes the integral exactly, and the verifier checks the student's own answer by differentiating it (or comparing the exact value of a definite integral). Theory and solver stay grounded in the RAG pipeline over `data/`.

See [docs/en/multi_agent_design.md](docs/en/multi_agent_design.md) for the team, the delegation type of each agent, and the design decisions behind it, and [`agents/cubik_team/`](agents/cubik_team/agent.py) for the implementation.
