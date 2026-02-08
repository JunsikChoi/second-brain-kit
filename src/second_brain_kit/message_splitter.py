"""Split long messages for Discord's 2000-char limit, preserving code blocks."""

DISCORD_MAX = 2000
SAFE_MAX = DISCORD_MAX - 20


def split_message(text: str) -> list[str]:
    if len(text) <= DISCORD_MAX:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= DISCORD_MAX:
            chunks.append(remaining)
            break

        split_at = _find_split_point(remaining)
        chunk = remaining[:split_at]
        remaining = remaining[split_at:]
        chunk, remaining = _fix_code_blocks(chunk, remaining)
        chunks.append(chunk)

    return chunks


def _find_split_point(text: str) -> int:
    search_start = max(0, SAFE_MAX - 200)
    last_newline = text.rfind("\n", search_start, SAFE_MAX)
    if last_newline > 0:
        return last_newline + 1
    return SAFE_MAX


def _fix_code_blocks(chunk: str, remaining: str) -> tuple[str, str]:
    fence_count = chunk.count("```")
    if fence_count % 2 == 1:
        last_fence = chunk.rfind("```")
        after_fence = chunk[last_fence + 3:].split("\n", 1)[0].strip()
        lang = after_fence if after_fence else ""
        chunk += "\n```"
        remaining = f"```{lang}\n{remaining}"
    return chunk, remaining
