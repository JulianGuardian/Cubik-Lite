"""Main entry point for the Cubik-Lite Integral Calculus Tutor.

Interactive terminal chatbot that uses litellm (Gemini or a local Ollama
model, see llm_client.py), the SlidingWindowManager for conversation history
management, and retriever.py to ground answers in data/ via RAG.
"""

from json import JSONDecodeError, loads
from pathlib import Path

from context_manager import SlidingWindowManager
from litellm import completion
from llm_client import CHAT_MODEL, USING_GEMINI
from retriever import query as retrieve

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"
with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

manager = SlidingWindowManager(
    system_prompt=SYSTEM_PROMPT,
    max_turns=10,
    max_chars=12000,
)


def send_message(user_input: str) -> str:
    """Retrieve grounding context and send a message to the LLM.

    The conversation history keeps the student's original question, but the
    turn actually sent to the LLM is augmented with retrieved knowledge base
    chunks so answers stay grounded in data/.

    Args:
        user_input: The student's question or message.

    Returns:
        The assistant's response text.
    """
    manager.add_user_message(user_input)

    chunks = retrieve(user_input)
    print("\n📚 Contexto recuperado:")
    for chunk in chunks:
        print(f"   [{chunk['source']}] {chunk['text'][:80]}...")

    context_block = "\n\n---\n\n".join(
        f"[Fuente: {c['source']}]\n{c['text']}" for c in chunks
    )
    augmented_question = (
        f"Contexto recuperado:\n{context_block}\n\n"
        f"Pregunta del estudiante: {user_input}"
    )

    messages = manager.get_messages()
    messages[-1] = {"role": "user", "content": augmented_question}

    response = completion(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.3,
    )

    assistant_text = response.choices[0].message.content
    manager.add_assistant_message(assistant_text)
    return assistant_text


def format_response(raw: str) -> str:
    """Try to pretty-print the JSON response from the tutor.

    Args:
        raw: The raw response string from the assistant.

    Returns:
        A formatted string for terminal display.
    """
    try:
        data = loads(raw)
        lines = []
        lines.append(f"\n📝 Respuesta: {data.get('answer', 'N/A')}")
        if data.get("rule"):
            lines.append(f"📐 Regla/Técnica: {data['rule']}")
        if data.get("confidence") is not None:
            lines.append(f"🎯 Confianza: {data['confidence']}")
        steps = data.get("steps", [])
        if steps:
            lines.append("\n📋 Pasos:")
            for i, step in enumerate(steps, 1):
                lines.append(f"   {i}. {step}")
        if data.get("source"):
            lines.append(f"\n📖 Fuente: {data['source']}")
        return "\n".join(lines)
    except (JSONDecodeError, TypeError):
        return f"\n{raw}"


def main() -> None:
    """Run the interactive terminal chatbot."""
    print("=" * 60)
    print("🧮  Cubik-Lite — Tutor de Cálculo Integral")
    provider = "Gemini" if USING_GEMINI else "Ollama local"
    print(f"⚙️  Usando {provider}-({CHAT_MODEL})")
    print("=" * 60)
    print("Escribe tu pregunta de cálculo integral.")
    print("Comandos: 'salir' para terminar, 'limpiar' para reiniciar.\n")

    while True:
        try:
            user_input = input("🧑‍🎓 Tú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 ¡Hasta luego! Sigue practicando integrales.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("salir", "exit", "quit"):
            print("\n👋 ¡Hasta luego! Sigue practicando integrales.")
            break

        if user_input.lower() in ("limpiar", "clear"):
            manager.clear()
            print("🗑️  Historial limpiado.\n")
            continue

        print("🤖 Pensando...")
        try:
            raw_response = send_message(user_input)
            formatted = format_response(raw_response)
            print(formatted)
            print(f"\n   [Turnos en contexto: {manager.turn_count}]\n")
        except Exception as e:
            print(f"\n❌ Error al contactar la API: {e}\n")


if __name__ == "__main__":
    main()
