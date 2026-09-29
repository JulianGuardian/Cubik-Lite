# Project Proposal

This project is a conversational assistant for calculus tutoring. It answers theoretical questions and walks through worked exercises step by step, citing the specific rule or theorem behind each step rather than just giving a final answer. It targets students taking an introductory calculus course who need on-demand practice and explanations outside of class hours. The knowledge base will be built from calculus lecture notes and textbook chapters covering limits, derivatives, and integrals, retrieved via RAG so that answers stay grounded in the assigned course material instead of the model's general knowledge. Given a student's exercise or question, the assistant returns both the final answer and the step-by-step reasoning behind it.

For Corte 1, the assistant's scope has been narrowed to **integral calculus** (indefinite/definite integrals, integration techniques, and applications). See [prompts/system_prompt.txt](prompts/system_prompt.txt) for the full system prompt defining its role, scope, refusal behavior, and output format.

## Example Questions

With RAG grounding answers in [data/](data/README.md) (see [README.md](README.md) for setup), the assistant can answer questions such as:

- What is the integral of x·e^x dx, and which technique applies?
- Find the area under the curve y = sin(x) from 0 to π.
- Why do we add a constant of integration (+C) to indefinite integrals?

## Corte 2: Multi-Agent Candidate

For Corte 2, the plan is to extend Cubik-Lite into a multi-agent system (built with Google ADK or LangGraph) that keeps solving the same real problem — grounded calculus tutoring — but splits the work across specialized agents instead of one monolithic prompt. A **triage agent** would first classify the student's input (theory question vs. worked exercise, and which technique it likely involves) and route it accordingly; one or more **solver/specialist agents** would then handle the actual step-by-step resolution for their assigned technique (substitution, integration by parts, partial fractions, etc.), pulling grounding context from the existing RAG pipeline over `data/`. This split lets each agent carry a narrower, technique-specific prompt instead of one system prompt trying to cover every case, and leaves room to add a verification role later. This will be refined once multi-agent patterns are covered in Week 8.
