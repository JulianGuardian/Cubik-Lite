"""LLM/embedding provider selection for the Cubik-Lite Integral Calculus Tutor.

If GEMINI_API_KEY is set (and not the placeholder), Gemini is used for both
chat and embeddings so teammates with an API key get the "real" models.
Otherwise this falls back to a local Ollama setup (qwen2.5:14b + nomic-embed-text)
so the assistant can be developed and tested without any API key.
"""

from os import getenv

from dotenv import load_dotenv
from litellm import completion, embedding

load_dotenv()

_GEMINI_API_KEY = getenv("GEMINI_API_KEY")
USING_GEMINI = bool(_GEMINI_API_KEY) and _GEMINI_API_KEY != "PEGA_TU_API_KEY_AQUI"

if USING_GEMINI:
    CHAT_MODEL = getenv("GEMINI_CHAT_MODEL", "gemini/gemini-3.6-flash")
    EMBED_MODEL = getenv("GEMINI_EMBED_MODEL", "gemini/gemini-embedding-001")
else:
    CHAT_MODEL = getenv("LOCAL_CHAT_MODEL", "ollama_chat/qwen2.5:14b")
    EMBED_MODEL = getenv("LOCAL_EMBED_MODEL", "ollama/nomic-embed-text")


def embed(text: str) -> list[float]:
    """Embed a single string using the active provider's embedding model.

    Args:
        text: The text to embed.

    Returns:
        The embedding vector as a list of floats.
    """
    result = embedding(model=EMBED_MODEL, input=text)
    return result.data[0]["embedding"]


if __name__ == "__main__":
    provider = "Gemini" if USING_GEMINI else "Ollama local"
    print(f"Proveedor activo: {provider}")
    print(f"  CHAT_MODEL  = {CHAT_MODEL}")
    print(f"  EMBED_MODEL = {EMBED_MODEL}")

    print("\nProbando chat...")
    response = completion(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": "Responde solo con: ok"}],
    )
    print("  Respuesta:", response.choices[0].message.content.strip())

    print("\nProbando embeddings...")
    vector = embed("La integral de 2x dx es x^2 + C.")
    print(f"  Vector de dimension {len(vector)} generado correctamente.")
