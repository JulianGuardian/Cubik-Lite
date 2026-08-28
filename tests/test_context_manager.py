"""Tests for SlidingWindowManager context manager."""

from context_manager import SlidingWindowManager


def test_system_prompt_always_present() -> None:
    """Verify system prompt is always the first message in get_messages()."""
    system_prompt = "You are an Integral Calculus Tutor Assistant."
    manager = SlidingWindowManager(system_prompt=system_prompt)

    messages = manager.get_messages()
    assert len(messages) == 1
    assert messages[0] == {"role": "system", "content": system_prompt}

    manager.add_user_message("How do I integrate x * exp(x)?")
    messages = manager.get_messages()
    assert len(messages) == 2
    assert messages[0] == {"role": "system", "content": system_prompt}


def test_add_messages() -> None:
    """Verify messages are added in the correct order."""
    manager = SlidingWindowManager(system_prompt="System Prompt")
    manager.add_user_message("What is the integral of 2x?")
    manager.add_assistant_message("The integral of 2x dx is x^2 + C.")

    messages = manager.get_messages()
    assert len(messages) == 3
    assert messages[0] == {"role": "system", "content": "System Prompt"}
    assert messages[1] == {"role": "user", "content": "What is the integral of 2x?"}
    assert messages[2] == {
        "role": "assistant",
        "content": "The integral of 2x dx is x^2 + C.",
    }


def test_sliding_window_trims_oldest() -> None:
    """Verify adding 3 complete turns with max_turns=2 trims the oldest turn."""
    manager = SlidingWindowManager(system_prompt="System Prompt", max_turns=2)

    # Turn 1
    manager.add_user_message("Turn 1 User")
    manager.add_assistant_message("Turn 1 Assistant")
    # Turn 2
    manager.add_user_message("Turn 2 User")
    manager.add_assistant_message("Turn 2 Assistant")
    # Turn 3
    manager.add_user_message("Turn 3 User")
    manager.add_assistant_message("Turn 3 Assistant")

    assert manager.turn_count == 2
    messages = manager.get_messages()
    # Expect system prompt + Turn 2 + Turn 3 = 5 messages total
    assert len(messages) == 5
    assert messages[0] == {"role": "system", "content": "System Prompt"}
    assert messages[1] == {"role": "user", "content": "Turn 2 User"}
    assert messages[2] == {"role": "assistant", "content": "Turn 2 Assistant"}
    assert messages[3] == {"role": "user", "content": "Turn 3 User"}
    assert messages[4] == {"role": "assistant", "content": "Turn 3 Assistant"}


def test_char_budget_trims() -> None:
    """Verify that exceeding max_chars triggers trimming of oldest complete turns."""
    # Set max_chars to 100 with max_turns=10
    manager = SlidingWindowManager(
        system_prompt="System Prompt", max_turns=10, max_chars=100
    )

    # Turn 1: 30 chars user + 30 chars assistant = 60 chars
    manager.add_user_message("U1" * 15)
    manager.add_assistant_message("A1" * 15)
    assert manager.turn_count == 1

    # Turn 2: 30 chars user + 30 chars assistant = 60 chars (total would be 120 > 100)
    manager.add_user_message("U2" * 15)
    manager.add_assistant_message("A2" * 15)

    # Turn 1 should be trimmed to fit within the 100-character budget
    assert manager.turn_count == 1
    messages = manager.get_messages()
    assert len(messages) == 3
    assert messages[0] == {"role": "system", "content": "System Prompt"}
    assert messages[1] == {"role": "user", "content": "U2" * 15}
    assert messages[2] == {"role": "assistant", "content": "A2" * 15}


def test_clear_keeps_system_prompt() -> None:
    """Verify clear() clears message history while preserving the system prompt."""
    system_prompt = "You are an Integral Calculus Tutor Assistant."
    manager = SlidingWindowManager(system_prompt=system_prompt)

    manager.add_user_message("User question")
    manager.add_assistant_message("Assistant response")
    assert manager.turn_count == 1

    manager.clear()
    assert manager.turn_count == 0
    messages = manager.get_messages()
    assert len(messages) == 1
    assert messages[0] == {"role": "system", "content": system_prompt}


def test_turn_count() -> None:
    """Verify turn_count property tracks complete turns accurately."""
    manager = SlidingWindowManager(system_prompt="System Prompt")
    assert manager.turn_count == 0

    manager.add_user_message("User 1")
    assert manager.turn_count == 0

    manager.add_assistant_message("Assistant 1")
    assert manager.turn_count == 1

    manager.add_user_message("User 2")
    assert manager.turn_count == 1

    manager.add_assistant_message("Assistant 2")
    assert manager.turn_count == 2


def test_incomplete_turn_not_counted() -> None:
    """Verify an incomplete turn (user message with no response) is not counted or trimmed."""
    manager = SlidingWindowManager(system_prompt="System Prompt", max_turns=2)

    # Turn 1
    manager.add_user_message("Turn 1 User")
    manager.add_assistant_message("Turn 1 Assistant")
    # Turn 2
    manager.add_user_message("Turn 2 User")
    manager.add_assistant_message("Turn 2 Assistant")
    # Incomplete turn (User 3 only)
    manager.add_user_message("Turn 3 User")

    # turn_count should still be 2 (complete turns only)
    assert manager.turn_count == 2

    # Incomplete user message should not be trimmed
    messages = manager.get_messages()
    assert len(messages) == 6
    assert messages[0] == {"role": "system", "content": "System Prompt"}
    assert messages[1] == {"role": "user", "content": "Turn 1 User"}
    assert messages[2] == {"role": "assistant", "content": "Turn 1 Assistant"}
    assert messages[3] == {"role": "user", "content": "Turn 2 User"}
    assert messages[4] == {"role": "assistant", "content": "Turn 2 Assistant"}
    assert messages[5] == {"role": "user", "content": "Turn 3 User"}
