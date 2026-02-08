"""Handle Discord file attachments: download inbound, detect outbound paths."""

import re
import time
from pathlib import Path

import discord

_ABSOLUTE_PATH_PATTERN = re.compile(
    r"[`\"'(\s]?(/(?:tmp|home)/[\w./\-]+\.\w{1,10})[`\"').,\s]?"
)


async def download_attachments(
    attachments: list[discord.Attachment], download_dir: Path
) -> list[Path]:
    download_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for att in attachments:
        dest = download_dir / att.filename
        counter = 1
        while dest.exists():
            stem = dest.stem.rsplit("_", 1)[0] if "_" in dest.stem else dest.stem
            dest = download_dir / f"{stem}_{counter}{dest.suffix}"
            counter += 1
        await att.save(dest)
        paths.append(dest)

    return paths


def detect_output_files(text: str, max_age_secs: int = 120) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    now = time.time()

    for match in _ABSOLUTE_PATH_PATTERN.finditer(text):
        p = Path(match.group(1))
        if p in seen:
            continue
        seen.add(p)
        if (
            p.exists()
            and p.is_file()
            and p.stat().st_size < 25 * 1024 * 1024
            and (now - p.stat().st_mtime) < max_age_secs
        ):
            paths.append(p)
    return paths


def build_file_prompt(file_paths: list[Path]) -> str:
    if not file_paths:
        return ""
    lines = ["\n\n아래 첨부 파일들을 Read 도구로 읽고 내용을 분석해줘:"]
    for p in file_paths:
        lines.append(f"- {p}")
    return "\n".join(lines)
