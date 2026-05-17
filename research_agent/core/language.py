"""Language-related prompt helpers."""


def build_language_instruction(response_language: str) -> str:
    """Return an output-language instruction for prompts when needed."""
    language = (response_language or "any").strip().lower()
    if language in {"", "any", "all", "*"}:
        return ""

    return (
        "\n\nOutput language requirement: "
        f"write the final answer strictly in '{language}'."
    )
