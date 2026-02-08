"""Tests for claude_runner module."""

import json

import pytest

from second_brain_kit.claude_runner import ClaudeResponse, ClaudeRunner


class TestClaudeResponse:
    def test_defaults(self) -> None:
        r = ClaudeResponse(text="hi", session_id="s1", cost_usd=0.0, duration_secs=0.0)
        assert r.is_error is False


class TestBuildCommand:
    def test_basic_command(self) -> None:
        runner = ClaudeRunner(model="sonnet", max_budget_usd=1.0)
        cmd = runner._build_command("hello")
        assert cmd[1:3] == ["-p", "hello"]
        assert "--output-format" in cmd
        assert "json" in cmd
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "sonnet"

    def test_custom_model_override(self) -> None:
        runner = ClaudeRunner(model="sonnet")
        cmd = runner._build_command("hello", model="opus")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "opus"

    def test_session_resume(self) -> None:
        runner = ClaudeRunner()
        cmd = runner._build_command("hello", session_id="sess-123")
        assert "--resume" in cmd
        idx = cmd.index("--resume")
        assert cmd[idx + 1] == "sess-123"

    def test_no_resume_without_session(self) -> None:
        runner = ClaudeRunner()
        cmd = runner._build_command("hello")
        assert "--resume" not in cmd

    def test_system_prompt(self) -> None:
        runner = ClaudeRunner()
        cmd = runner._build_command("hello", system_prompt="Be helpful")
        assert "--system-prompt" in cmd
        idx = cmd.index("--system-prompt")
        assert cmd[idx + 1] == "Be helpful"

    def test_allowed_tools(self) -> None:
        runner = ClaudeRunner(allowed_tools=["Read", "Write"])
        cmd = runner._build_command("hello")
        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        assert cmd[idx + 1] == "Read,Write"

    def test_budget(self) -> None:
        runner = ClaudeRunner(max_budget_usd=5.0)
        cmd = runner._build_command("hello")
        assert "--max-budget-usd" in cmd
        idx = cmd.index("--max-budget-usd")
        assert cmd[idx + 1] == "5.0"

    def test_budget_override(self) -> None:
        runner = ClaudeRunner(max_budget_usd=1.0)
        cmd = runner._build_command("hello", max_budget_usd=3.0)
        idx = cmd.index("--max-budget-usd")
        assert cmd[idx + 1] == "3.0"


class TestParseOutput:
    def test_valid_json(self) -> None:
        runner = ClaudeRunner()
        data = {
            "result": "Hello!",
            "session_id": "sess-1",
            "total_cost_usd": 0.05,
            "duration_ms": 1500,
            "is_error": False,
        }
        resp = runner._parse_output(json.dumps(data), None)
        assert resp.text == "Hello!"
        assert resp.session_id == "sess-1"
        assert resp.cost_usd == 0.05
        assert abs(resp.duration_secs - 1.5) < 1e-9
        assert resp.is_error is False

    def test_empty_input(self) -> None:
        runner = ClaudeRunner()
        resp = runner._parse_output("", None)
        assert resp.is_error is True
        assert "No response" in resp.text

    def test_whitespace_input(self) -> None:
        runner = ClaudeRunner()
        resp = runner._parse_output("   \n  ", None)
        assert resp.is_error is True

    def test_invalid_json_with_braces(self) -> None:
        runner = ClaudeRunner()
        raw = 'Some prefix text {"result": "ok", "session_id": "s1"} trailing'
        resp = runner._parse_output(raw, "fallback")
        assert resp.text == "ok"
        assert resp.session_id == "s1"

    def test_invalid_json_no_braces(self) -> None:
        runner = ClaudeRunner()
        resp = runner._parse_output("just plain text", "fb-sess")
        assert resp.text == "just plain text"
        assert resp.session_id == "fb-sess"

    def test_fallback_session_id(self) -> None:
        runner = ClaudeRunner()
        data = {"result": "hi"}
        resp = runner._parse_output(json.dumps(data), "fallback-id")
        assert resp.session_id == "fallback-id"

    def test_alternative_field_names(self) -> None:
        runner = ClaudeRunner()
        data = {"text": "Hello", "cost_usd": 0.02}
        resp = runner._parse_output(json.dumps(data), None)
        assert resp.text == "Hello"
        assert resp.cost_usd == 0.02

    def test_error_flag(self) -> None:
        runner = ClaudeRunner()
        data = {"result": "Error occurred", "is_error": True}
        resp = runner._parse_output(json.dumps(data), None)
        assert resp.is_error is True


class TestKillAndRunning:
    def test_kill_no_procs(self) -> None:
        runner = ClaudeRunner()
        assert runner.kill() == 0

    def test_kill_specific_channel_no_proc(self) -> None:
        runner = ClaudeRunner()
        assert runner.kill(channel_id=100) == 0

    def test_is_running_empty(self) -> None:
        runner = ClaudeRunner()
        assert runner.is_running() is False
        assert runner.is_running(channel_id=100) is False

    def test_running_count_empty(self) -> None:
        runner = ClaudeRunner()
        assert runner.running_count == 0


class TestRunAsync:
    @pytest.mark.asyncio
    async def test_run_command_not_found(self) -> None:
        runner = ClaudeRunner()
        # Use a binary that doesn't exist
        import second_brain_kit.claude_runner as mod

        original = mod._CLAUDE_BIN
        mod._CLAUDE_BIN = "/nonexistent/claude-binary"
        try:
            resp = await runner.run("hello", channel_id=1)
            assert resp.is_error is True
            assert "Claude CLI" in resp.text
        finally:
            mod._CLAUDE_BIN = original
