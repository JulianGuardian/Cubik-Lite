"""Context manager module for the Cubik-Lite Integral Calculus Tutor.

This module provides conversation history management with sliding window and
character budget constraints to maintain relevant context while staying within
LLM token and context window limits.
"""


class SlidingWindowManager:
    """Manages conversation history using a sliding window and character budget.

    Strategy:
    1. System Prompt Preservation: The system prompt is always prepended as the
       first message when preparing messages for LLM API calls.
    2. Turn-Based Sliding Window: Conversation history is limited to the most
       recent `max_turns` complete turns (where 1 turn = 1 user message + 1
       assistant message). Incomplete turns (e.g. a trailing user message waiting
       for a response) are preserved and not counted against the turn limit.
    3. Character Budget: If the total character count of non-system messages
       exceeds `max_chars`, the oldest complete turns are trimmed until the
       conversation history fits within budget.
    """

    def __init__(
        self,
        system_prompt: str,
        max_turns: int = 10,
        max_chars: int = 12000,
    ) -> None:
        """Initialize the sliding window manager.

        Args:
            system_prompt: The base instructions defining the assistant role.
            max_turns: Maximum number of complete conversation turns to keep.
            max_chars: Maximum character budget for non-system messages.
        """
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.max_chars = max_chars
        self._messages: list[dict[str, str]] = []

    @property
    def turn_count(self) -> int:
        """Return the number of complete turns in conversation history.

        A complete turn consists of a user message followed by an assistant message.
        """
        count = 0
        i = 0
        while i < len(self._messages) - 1:
            if (
                self._messages[i]["role"] == "user"
                and self._messages[i + 1]["role"] == "assistant"
            ):
                count += 1
                i += 2
            else:
                i += 1
        return count

    def add_user_message(self, text: str) -> None:
        """Append a user message to the conversation history.

        Args:
            text: The content of the user message.
        """
        self._messages.append({"role": "user", "content": text})
        self._trim_to_window()
        self._trim_to_budget()

    def add_assistant_message(self, text: str) -> None:
        """Append an assistant message to the conversation history.

        Args:
            text: The content of the assistant message.
        """
        self._messages.append({"role": "assistant", "content": text})
        self._trim_to_window()
        self._trim_to_budget()

    def _total_chars(self) -> int:
        """Calculate total character count across all stored non-system messages."""
        return sum(len(msg["content"]) for msg in self._messages)

    def _trim_to_window(self) -> None:
        """Ensure conversation has at most max_turns complete turns.

        Trims the oldest complete turns first. Incomplete turns are retained.
        """
        while self.turn_count > self.max_turns:
            for i in range(len(self._messages) - 1):
                if (
                    self._messages[i]["role"] == "user"
                    and self._messages[i + 1]["role"] == "assistant"
                ):
                    del self._messages[: i + 2]
                    break
            else:
                break

    def _trim_to_budget(self) -> None:
        """Remove oldest complete turns if total non-system characters exceed max_chars."""
        while self._total_chars() > self.max_chars and self.turn_count > 0:
            for i in range(len(self._messages) - 1):
                if (
                    self._messages[i]["role"] == "user"
                    and self._messages[i + 1]["role"] == "assistant"
                ):
                    del self._messages[: i + 2]
                    break
            else:
                break

    def get_messages(self) -> list[dict[str, str]]:
        """Return the formatted message list for an LLM API call.

        Applies sliding window and character budget constraints, prepending
        the system prompt as the first message.

        Returns:
            List of message dictionaries with 'role' and 'content' keys.
        """
        self._trim_to_window()
        self._trim_to_budget()
        return [
            {"role": "system", "content": self.system_prompt}
        ] + [dict(msg) for msg in self._messages]

    def clear(self) -> None:
        """Clear conversation history while keeping the system prompt."""
        self._messages.clear()
