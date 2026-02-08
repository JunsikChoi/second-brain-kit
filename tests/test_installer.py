"""Tests for the CLI installer module."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from second_brain_kit.installer import (
    VAULT_DIRS,
    VAULT_TEMPLATES,
    CheckResult,
    check_claude_cli,
    check_obsidian,
    check_python_version,
    create_systemd_service,
    create_vault_structure,
    enable_systemd_service,
    run_preflight_checks,
    write_env_file,
)

# ── Pre-flight checks ───────────────────────────────────────────────


class TestCheckPythonVersion:
    def test_current_python_passes(self) -> None:
        result = check_python_version()
        # We're running on 3.11+, so this should pass
        assert result.passed is True
        assert "Python" in result.message

    def test_old_python_fails(self) -> None:
        fake_info = MagicMock(major=3, minor=10, micro=0)
        fake_info.__ge__ = lambda self, other: (3, 10) >= other  # type: ignore[assignment]
        with patch("second_brain_kit.installer.sys") as mock_sys:
            mock_sys.version_info = fake_info
            result = check_python_version()
        assert result.passed is False
        assert result.hint  # Should have install hint


class TestCheckClaudeCli:
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_found(self, _: MagicMock) -> None:
        result = check_claude_cli()
        assert result.passed is True
        assert "/usr/local/bin/claude" in result.message

    @patch("shutil.which", return_value=None)
    def test_not_found(self, _: MagicMock) -> None:
        result = check_claude_cli()
        assert result.passed is False
        assert result.hint


class TestCheckObsidian:
    @patch("shutil.which", return_value="/usr/bin/obsidian")
    def test_found_in_path(self, _: MagicMock) -> None:
        result = check_obsidian()
        assert result.passed is True

    @patch("shutil.which", return_value=None)
    def test_found_via_flatpak(self, _: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "md.obsidian.Obsidian\t1.5.0\n"
        with patch("subprocess.run", return_value=mock_result):
            result = check_obsidian()
        assert result.passed is True
        assert "Flatpak" in result.message

    @patch("shutil.which", return_value=None)
    def test_found_via_snap(self, _: MagicMock) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch.object(Path, "exists", return_value=True):
                result = check_obsidian()
        assert result.passed is True
        assert "Snap" in result.message

    @patch("shutil.which", return_value=None)
    def test_not_found(self, _: MagicMock) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Path, "is_dir", return_value=False):
                    result = check_obsidian()
        assert result.passed is False
        assert result.hint


class TestRunPreflightChecks:
    def test_returns_three_checks(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/obsidian"):
            results = run_preflight_checks()
        assert len(results) == 3
        assert all(isinstance(r, CheckResult) for r in results)


# ── Vault scaffold ───────────────────────────────────────────────────


class TestCreateVaultStructure:
    def test_creates_directories(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        create_vault_structure(vault)

        for d in VAULT_DIRS:
            assert (vault / d).is_dir(), f"Missing directory: {d}"

    def test_creates_template_files(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        create_vault_structure(vault)

        for rel in VAULT_TEMPLATES:
            assert (vault / rel).is_file(), f"Missing template: {rel}"

    def test_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()

        # Pre-create a template file with custom content
        home = vault / "Home.md"
        home.write_text("my custom home", encoding="utf-8")

        create_vault_structure(vault)

        assert home.read_text(encoding="utf-8") == "my custom home"

    def test_returns_created_paths(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        created = create_vault_structure(vault)

        assert len(created) > 0
        # Should include directories and template files
        dir_entries = [c for c in created if c.endswith("/")]
        file_entries = [c for c in created if not c.endswith("/")]
        assert len(dir_entries) == len(VAULT_DIRS)
        assert len(file_entries) == len(VAULT_TEMPLATES)

    def test_templates_contain_valid_frontmatter(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        create_vault_structure(vault)

        for rel in VAULT_TEMPLATES:
            content = (vault / rel).read_text(encoding="utf-8")
            assert content.startswith("---\n"), f"{rel} missing frontmatter"
            assert "\n---\n" in content[4:], f"{rel} frontmatter not closed"

    def test_date_placeholder_replaced(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        create_vault_structure(vault)

        for rel in VAULT_TEMPLATES:
            content = (vault / rel).read_text(encoding="utf-8")
            assert "{{date}}" not in content, f"{rel} still has {{{{date}}}} placeholder"


# ── .env file ────────────────────────────────────────────────────────


class TestWriteEnvFile:
    def test_writes_all_fields(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        write_env_file(
            env,
            discord_token="tok_abc123",
            owner_id="999888777",
            vault_path="/home/user/vault",
            claude_model="opus",
        )

        content = env.read_text(encoding="utf-8")
        assert "DISCORD_TOKEN=tok_abc123" in content
        assert "OWNER_ID=999888777" in content
        assert "VAULT_PATH=/home/user/vault" in content
        assert "CLAUDE_MODEL=opus" in content
        assert "MAX_BUDGET_USD=1.00" in content

    def test_default_model_is_sonnet(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        write_env_file(
            env,
            discord_token="tok",
            owner_id="123",
            vault_path="/vault",
        )
        content = env.read_text(encoding="utf-8")
        assert "CLAUDE_MODEL=sonnet" in content


# ── systemd service ──────────────────────────────────────────────────


class TestCreateSystemdService:
    def test_creates_service_file(self, tmp_path: Path) -> None:
        with patch("second_brain_kit.installer.Path.home", return_value=tmp_path):
            service_path = create_systemd_service(
                project_dir=Path("/opt/sbk"),
                env_file=Path("/opt/sbk/.env"),
                venv_python=Path("/opt/sbk/.venv/bin/python"),
            )

        assert service_path.exists()
        content = service_path.read_text(encoding="utf-8")
        assert "ExecStart=/opt/sbk/.venv/bin/python -m second_brain_kit" in content
        assert "WorkingDirectory=/opt/sbk" in content
        assert "EnvironmentFile=/opt/sbk/.env" in content

    def test_uses_system_python_without_venv(self, tmp_path: Path) -> None:
        with patch("second_brain_kit.installer.Path.home", return_value=tmp_path):
            service_path = create_systemd_service(
                project_dir=Path("/opt/sbk"),
                env_file=Path("/opt/sbk/.env"),
            )

        content = service_path.read_text(encoding="utf-8")
        assert sys.executable in content

    def test_service_file_location(self, tmp_path: Path) -> None:
        with patch("second_brain_kit.installer.Path.home", return_value=tmp_path):
            service_path = create_systemd_service(
                project_dir=Path("/opt/sbk"),
                env_file=Path("/opt/sbk/.env"),
            )

        expected = tmp_path / ".config" / "systemd" / "user" / "second-brain-kit.service"
        assert service_path == expected


class TestEnableSystemdService:
    @patch("subprocess.run")
    def test_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        assert enable_systemd_service() is True
        assert mock_run.call_count == 2  # daemon-reload + enable

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_systemctl_not_found(self, _: MagicMock) -> None:
        assert enable_systemd_service() is False

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "systemctl"))
    def test_command_failure(self, _: MagicMock) -> None:
        assert enable_systemd_service() is False

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("systemctl", 10))
    def test_timeout(self, _: MagicMock) -> None:
        assert enable_systemd_service() is False
