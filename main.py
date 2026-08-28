"""Main entry point for the Cubik-Lite Integral Calculus Tutor.

Interactive terminal chatbot that uses the Gemini API and the
SlidingWindowManager for conversation history management.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from context_manager import SlidingWindowManager

# ── Setup ───────────────────────────────────────────────────────────────────

# Load environment variables from .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY or API_KEY == "PEGA_TU_API_KEY_AQUI":
    print("❌ Error: Configura tu GEMINI_API_KEY en el archivo .env")
    print("   1. Ve a https://aistudio.google.com/apikey")
    print("   2. Crea una API key")
    print("   3. Pégala en el archivo .env")
    sys.exit(1)

# Load system prompt
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"
with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Initialize Gemini client
client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.0-flash"

# Initialize context manager (sliding window: 10 turns, 12k chars)
manager = SlidingWindowManager(
    system_prompt=SYSTEM_PROMPT,
    max_turns=10,
    max_chars=12000,
)


def send_message(user_input: str) -> str:
    """Send a message to the Gemini API using the managed conversation history.

    Args:
        user_input: The student's question or message.

    Returns:
        The assistant's response text.
    """
    manager.add_user_message(user_input)
    messages = manager.get_messages()

    # Build contents for the Gemini API
    # The first message is the system prompt (handled via system_instruction)
    # The rest are the conversation history
    history_contents = []
    for msg in messages[1:]:  # Skip system prompt
        role = "user" if msg["role"] == "user" else "model"
        history_contents.append(
            genai.types.Content(
                role=role,
                parts=[genai.types.Part(text=msg["content"])],
            )
        )

    response = client.models.generate_content(
        model=MODEL,
        contents=history_contents,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )

    assistant_text = response.text
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
        data = json.loads(raw)
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
        return "\n".join(lines)
    except (json.JSONDecodeError, TypeError):
        # If not valid JSON, return as-is
        return f"\n{raw}"


def main() -> None:
    """Run the interactive terminal chatbot."""
    print("=" * 60)
    print("🧮  Cubik-Lite — Tutor de Cálculo Integral")
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
