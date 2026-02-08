"""CLI installer for Second Brain Kit (Linux).

Interactive wizard that:
1. Checks system requirements (Python 3.11+, Claude Code CLI)
2. Verifies Obsidian installation
3. Creates vault structure with starter templates
4. Configures Discord bot credentials (.env)
5. Registers a systemd user service
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

# ── ANSI helpers ─────────────────────────────────────────────────────

_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {_GREEN}✓{_RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}⚠{_RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {_RED}✗{_RESET} {msg}")


def _heading(msg: str) -> None:
    print(f"\n{_BOLD}{_CYAN}{'─' * 50}")
    print(f"  {msg}")
    print(f"{'─' * 50}{_RESET}\n")


def _ask(prompt: str, default: str = "") -> str:
    """Prompt user for input with an optional default value."""
    suffix = f" [{default}]" if default else ""
    value = input(f"  {prompt}{suffix}: ").strip()
    return value or default


def _confirm(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    value = input(f"  {prompt} ({hint}): ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes")


# ── Check results ────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """Result of a single pre-flight check."""

    name: str
    passed: bool
    message: str
    hint: str = ""


# ── Step 1: System checks ───────────────────────────────────────────


def check_python_version() -> CheckResult:
    """Verify Python >= 3.11."""
    v = sys.version_info
    ok = v >= (3, 11)
    msg = f"Python {v.major}.{v.minor}.{v.micro}"
    hint = "Install Python 3.11+ from https://python.org" if not ok else ""
    return CheckResult("Python 3.11+", ok, msg, hint)


def check_claude_cli() -> CheckResult:
    """Verify Claude Code CLI is installed and accessible."""
    path = shutil.which("claude")
    if path:
        return CheckResult("Claude Code CLI", True, f"Found at {path}")
    return CheckResult(
        "Claude Code CLI",
        False,
        "Not found in PATH",
        "Install: https://docs.anthropic.com/en/docs/claude-code/getting-started",
    )


def check_obsidian() -> CheckResult:
    """Check if Obsidian is installed (binary, AppImage, Flatpak, or Snap)."""
    # Direct binary
    if shutil.which("obsidian"):
        return CheckResult("Obsidian", True, "Found in PATH")

    # Flatpak
    try:
        result = subprocess.run(
            ["flatpak", "list", "--app"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "obsidian" in result.stdout.lower():
            return CheckResult("Obsidian", True, "Found via Flatpak")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Snap
    snap_path = Path("/snap/obsidian")
    if snap_path.exists():
        return CheckResult("Obsidian", True, "Found via Snap")

    # AppImage in common locations
    for search_dir in [Path.home(), Path.home() / "Applications"]:
        if search_dir.is_dir():
            for f in search_dir.iterdir():
                if f.is_file() and "obsidian" in f.name.lower() and f.suffix == ".AppImage":
                    return CheckResult("Obsidian", True, f"AppImage: {f}")

    return CheckResult(
        "Obsidian",
        False,
        "Not found",
        "Install from https://obsidian.md/download (AppImage, Flatpak, or Snap)",
    )


def run_preflight_checks() -> list[CheckResult]:
    """Run all pre-flight checks and return results."""
    return [
        check_python_version(),
        check_claude_cli(),
        check_obsidian(),
    ]


# ── Step 2: Vault scaffold ──────────────────────────────────────────

#: Default directory structure for a new vault.
VAULT_DIRS = [
    "Inbox",
    "Notes",
    "Projects",
    "Templates",
    "Archive",
]

#: Starter template notes.
VAULT_TEMPLATES: dict[str, str] = {
    "Templates/Note.md": textwrap.dedent("""\
        ---
        type: note
        tags: []
        created: {{date}}
        ---

        # {{title}}

        """),
    "Templates/TIL.md": textwrap.dedent("""\
        ---
        type: til
        tags:
          - til
        created: {{date}}
        ---

        # TIL: {{title}}

        ## Problem

        ## Cause

        ## Solution

        """),
    "Templates/Meeting.md": textwrap.dedent("""\
        ---
        type: note
        tags:
          - meeting
        created: {{date}}
        ---

        # Meeting: {{title}}

        ## Attendees

        ## Agenda

        ## Notes

        ## Action Items
        - [ ]

        """),
    "Home.md": textwrap.dedent("""\
        ---
        type: moc
        tags:
          - moc
        created: {{date}}
        ---

        # Home

        Welcome to your Second Brain!

        ## Quick Links
        - [[Inbox/]] — Drop anything here
        - [[Notes/]] — Processed knowledge
        - [[Projects/]] — Active projects

        ## Recent
        (Your AI assistant will help keep this updated.)
        """),
}


def create_vault_structure(vault_path: Path) -> list[str]:
    """Create vault directories and starter templates.

    Returns a list of created paths (relative to vault_path).
    """
    created: list[str] = []
    vault_path.mkdir(parents=True, exist_ok=True)

    for d in VAULT_DIRS:
        dir_path = vault_path / d
        dir_path.mkdir(exist_ok=True)
        created.append(f"{d}/")

    from datetime import date

    today = date.today().isoformat()

    for rel, content in VAULT_TEMPLATES.items():
        file_path = vault_path / rel
        if file_path.exists():
            continue  # Never overwrite existing files
        file_path.parent.mkdir(parents=True, exist_ok=True)
        rendered = content.replace("{{date}}", today)
        file_path.write_text(rendered, encoding="utf-8")
        created.append(rel)

    return created


# ── Step 3: Discord bot configuration ───────────────────────────────

_DISCORD_GUIDE = """\
  To create a Discord bot:
  1. Go to https://discord.com/developers/applications
  2. Click "New Application" → name it (e.g. "Second Brain")
  3. Go to "Bot" tab → click "Reset Token" → copy the token
  4. Enable "Message Content Intent" under Privileged Intents
  5. Go to "OAuth2" → "URL Generator"
     - Scopes: bot, applications.commands
     - Permissions: Send Messages, Embed Links, Attach Files, Read Message History
  6. Copy the generated URL and open it to invite the bot to your server

  To get your Owner ID:
  - Enable Developer Mode in Discord (Settings → Advanced)
  - Right-click your username → "Copy User ID"
"""


def write_env_file(
    env_path: Path,
    *,
    discord_token: str,
    owner_id: str,
    vault_path: str,
    claude_model: str = "sonnet",
) -> None:
    """Write a .env configuration file."""
    content = textwrap.dedent(f"""\
        # Second Brain Kit configuration
        # Generated by: sbk install

        # Required
        DISCORD_TOKEN={discord_token}
        OWNER_ID={owner_id}
        VAULT_PATH={vault_path}

        # Optional
        CLAUDE_MODEL={claude_model}
        MAX_BUDGET_USD=1.00
        ALLOWED_TOOLS=
        DOWNLOAD_DIR=/tmp/second-brain-kit-files
    """)
    env_path.write_text(content, encoding="utf-8")


# ── Step 4: systemd user service ─────────────────────────────────────

_SERVICE_TEMPLATE = """\
[Unit]
Description=Second Brain Kit — AI-powered knowledge assistant
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={exec_start}
WorkingDirectory={work_dir}
Restart=on-failure
RestartSec=10
EnvironmentFile={env_file}

[Install]
WantedBy=default.target
"""


def create_systemd_service(
    *,
    project_dir: Path,
    env_file: Path,
    venv_python: Path | None = None,
) -> Path:
    """Create a systemd user service file.

    Returns the path to the created service file.
    """
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_path = service_dir / "second-brain-kit.service"

    # Prefer venv python, fall back to system python
    python = str(venv_python) if venv_python else sys.executable
    exec_start = f"{python} -m second_brain_kit"

    content = _SERVICE_TEMPLATE.format(
        exec_start=exec_start,
        work_dir=str(project_dir),
        env_file=str(env_file),
    )
    service_path.write_text(content, encoding="utf-8")
    return service_path


def enable_systemd_service() -> bool:
    """Enable and start the systemd user service. Returns True on success."""
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["systemctl", "--user", "enable", "second-brain-kit.service"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ── Main wizard ──────────────────────────────────────────────────────


def run_installer(project_dir: Path | None = None) -> None:
    """Run the interactive installation wizard."""
    print(f"\n{_BOLD}Second Brain Kit — Installer{_RESET}")
    print("Set up your AI-powered second brain in minutes.\n")

    if project_dir is None:
        project_dir = Path.cwd()

    # ── Pre-flight checks ────────────────────────────────────────
    _heading("Step 1/4: System Requirements")

    checks = run_preflight_checks()
    all_ok = True
    for c in checks:
        if c.passed:
            _ok(f"{c.name}: {c.message}")
        else:
            _fail(f"{c.name}: {c.message}")
            if c.hint:
                print(f"          {_YELLOW}{c.hint}{_RESET}")
            all_ok = False

    if not all_ok:
        obsidian_only = all(
            c.passed for c in checks if c.name != "Obsidian"
        ) and not next(c for c in checks if c.name == "Obsidian").passed

        if obsidian_only:
            _warn("Obsidian is optional but recommended for browsing your vault.")
            if not _confirm("Continue without Obsidian?"):
                print("\nInstall Obsidian first, then re-run: sbk install")
                sys.exit(1)
        else:
            print(f"\n{_RED}Fix the issues above before continuing.{_RESET}")
            sys.exit(1)

    # ── Vault setup ──────────────────────────────────────────────
    _heading("Step 2/4: Vault Setup")

    default_vault = str(Path.home() / "SecondBrainVault")
    vault_path_str = _ask("Vault path", default_vault)
    vault_path = Path(vault_path_str).expanduser().resolve()

    if vault_path.is_dir() and any(vault_path.iterdir()):
        _warn(f"Directory exists and is not empty: {vault_path}")
        if _confirm("Use this existing directory? (templates won't overwrite existing files)"):
            created = create_vault_structure(vault_path)
        else:
            print("Choose a different path and re-run: sbk install")
            sys.exit(0)
    else:
        created = create_vault_structure(vault_path)

    _ok(f"Vault ready at {vault_path}")
    for item in created[:8]:
        print(f"      {item}")
    if len(created) > 8:
        print(f"      ... and {len(created) - 8} more")

    # ── Discord bot ──────────────────────────────────────────────
    _heading("Step 3/4: Discord Bot")
    print(_DISCORD_GUIDE)

    discord_token = _ask("Discord bot token")
    while not discord_token:
        _fail("Token is required.")
        discord_token = _ask("Discord bot token")

    owner_id = _ask("Your Discord user ID")
    while not owner_id or not owner_id.isdigit():
        _fail("Owner ID must be a numeric Discord user ID.")
        owner_id = _ask("Your Discord user ID")

    claude_model = _ask("Default Claude model", "sonnet")

    env_path = project_dir / ".env"
    write_env_file(
        env_path,
        discord_token=discord_token,
        owner_id=owner_id,
        vault_path=str(vault_path),
        claude_model=claude_model,
    )
    _ok(f".env written to {env_path}")

    # ── systemd service ──────────────────────────────────────────
    _heading("Step 4/4: Background Service")

    # Detect venv python
    venv_python: Path | None = None
    venv_marker = project_dir / ".venv" / "bin" / "python"
    if venv_marker.is_file():
        venv_python = venv_marker

    if _confirm("Register as systemd user service? (auto-start on login)"):
        service_path = create_systemd_service(
            project_dir=project_dir,
            env_file=env_path,
            venv_python=venv_python,
        )
        _ok(f"Service file: {service_path}")

        if enable_systemd_service():
            _ok("Service enabled (will start on next login)")
            print(f"\n  Start now:  {_CYAN}systemctl --user start second-brain-kit{_RESET}")
            print(f"  View logs:  {_CYAN}journalctl --user -u second-brain-kit -f{_RESET}")
        else:
            _warn("Could not enable service automatically.")
            print(f"  Run manually: {_CYAN}systemctl --user enable --now second-brain-kit{_RESET}")
    else:
        _ok("Skipped. Run manually with: second-brain-kit")

    # ── Done ─────────────────────────────────────────────────────
    print(f"\n{_BOLD}{_GREEN}{'─' * 50}")
    print("  Installation complete!")
    print(f"{'─' * 50}{_RESET}\n")
    print(f"  Vault:    {vault_path}")
    print(f"  Config:   {env_path}")
    print(f"  Run:      {_CYAN}second-brain-kit{_RESET}")
    print("  Commands: Talk to the bot in Discord, or use /help\n")


def main() -> None:
    """Entry point for ``sbk install``."""
    # Accept optional --project-dir argument
    project_dir: Path | None = None
    args = sys.argv[1:]
    if "--project-dir" in args:
        idx = args.index("--project-dir")
        if idx + 1 < len(args):
            project_dir = Path(args[idx + 1]).resolve()

    try:
        run_installer(project_dir)
    except KeyboardInterrupt:
        print(f"\n\n{_YELLOW}Installation cancelled.{_RESET}")
        sys.exit(130)


if __name__ == "__main__":
    main()
