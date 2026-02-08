"""Async wrapper around the Claude Code CLI."""

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_CLAUDE_BIN = shutil.which("claude") or "claude"


@dataclass
class ClaudeResponse:
    text: str
    session_id: str
    cost_usd: float
    duration_secs: float
    is_error: bool = False


class ClaudeRunner:
    """Runs `claude -p` as an async subprocess and parses JSON output."""

    def __init__(
        self,
        model: str = "sonnet",
        max_budget_usd: float = 1.00,
        allowed_tools: list[str] | None = None,
        cwd: Path | None = None,
    ) -> None:
        self.model = model
        self.max_budget_usd = max_budget_usd
        self.allowed_tools = allowed_tools or []
        self.cwd = cwd or Path.home()
        self._running_procs: dict[int, asyncio.subprocess.Process] = {}

    async def run(
        self,
        prompt: str,
        *,
        channel_id: int = 0,
        model: str | None = None,
        session_id: str | None = None,
        system_prompt: str | None = None,
        max_budget_usd: float | None = None,
        cwd: Path | None = None,
    ) -> ClaudeResponse:
        cmd = self._build_command(
            prompt,
            model=model,
            session_id=session_id,
            system_prompt=system_prompt,
            max_budget_usd=max_budget_usd,
        )
        log.info("Running (ch=%d): %s", channel_id, " ".join(cmd[:6]) + " ...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd or self.cwd),
            )
            self._running_procs[channel_id] = proc
            stdout, stderr = await proc.communicate()
            self._running_procs.pop(channel_id, None)
        except Exception as e:
            self._running_procs.pop(channel_id, None)
            return ClaudeResponse(
                text=f"Failed to run Claude CLI: {e}",
                session_id=session_id or "",
                cost_usd=0.0,
                duration_secs=0.0,
                is_error=True,
            )

        raw_stdout = stdout.decode(errors="replace")
        raw_stderr = stderr.decode(errors="replace")
        raw = raw_stdout if raw_stdout.strip() else raw_stderr

        return self._parse_output(raw, session_id)

    def kill(self, channel_id: int | None = None) -> int:
        if channel_id is not None:
            proc = self._running_procs.pop(channel_id, None)
            if proc and proc.returncode is None:
                proc.kill()
                return 1
            return 0

        killed = 0
        for cid in list(self._running_procs):
            proc = self._running_procs.pop(cid)
            if proc.returncode is None:
                proc.kill()
                killed += 1
        return killed

    def is_running(self, channel_id: int | None = None) -> bool:
        if channel_id is not None:
            proc = self._running_procs.get(channel_id)
            return proc is not None and proc.returncode is None
        return any(p.returncode is None for p in self._running_procs.values())

    @property
    def running_count(self) -> int:
        return sum(1 for p in self._running_procs.values() if p.returncode is None)

    def _build_command(
        self,
        prompt: str,
        *,
        model: str | None = None,
        session_id: str | None = None,
        system_prompt: str | None = None,
        max_budget_usd: float | None = None,
    ) -> list[str]:
        cmd = [
            _CLAUDE_BIN,
            "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "--model", model or self.model,
            "--max-budget-usd", str(max_budget_usd or self.max_budget_usd),
        ]
        if session_id:
            cmd.extend(["--resume", session_id])
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])
        if self.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self.allowed_tools)])
        return cmd

    def _parse_output(self, raw: str, fallback_session_id: str | None) -> ClaudeResponse:
        if not raw.strip():
            return ClaudeResponse(
                text="(No response from Claude)",
                session_id=fallback_session_id or "",
                cost_usd=0.0,
                duration_secs=0.0,
                is_error=True,
            )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(raw[start:end])
                except json.JSONDecodeError:
                    return ClaudeResponse(
                        text=raw[:2000],
                        session_id=fallback_session_id or "",
                        cost_usd=0.0,
                        duration_secs=0.0,
                    )
            else:
                return ClaudeResponse(
                    text=raw[:2000],
                    session_id=fallback_session_id or "",
                    cost_usd=0.0,
                    duration_secs=0.0,
                )

        result_text = data.get("result", data.get("text", str(data)))
        session_id_val = data.get("session_id", fallback_session_id or "")
        cost_usd = data.get("total_cost_usd", data.get("cost_usd", 0.0)) or 0.0
        duration_ms = data.get("duration_ms", 0) or 0
        is_error = data.get("is_error", False)

        return ClaudeResponse(
            text=result_text,
            session_id=session_id_val,
            cost_usd=cost_usd,
            duration_secs=duration_ms / 1000.0,
            is_error=is_error,
        )
