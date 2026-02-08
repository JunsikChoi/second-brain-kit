"""Configuration loaded from environment variables."""

from dataclasses import dataclass, field
from os import environ
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    discord_token: str
    owner_id: int
    vault_path: Path
    claude_model: str = "sonnet"
    max_budget_usd: float = 1.00
    allowed_tools: list[str] = field(default_factory=list)
    download_dir: Path = Path("/tmp/second-brain-kit-files")

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "Config":
        load_dotenv(env_path)

        token = environ.get("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN is required")

        owner_id = environ.get("OWNER_ID")
        if not owner_id:
            raise ValueError("OWNER_ID is required")

        vault_path_str = environ.get("VAULT_PATH")
        if not vault_path_str:
            raise ValueError("VAULT_PATH is required")
        vault_path = Path(vault_path_str).expanduser().resolve()
        if not vault_path.is_dir():
            raise ValueError(f"VAULT_PATH does not exist: {vault_path}")

        allowed_tools_raw = environ.get("ALLOWED_TOOLS", "")
        allowed_tools = [t.strip() for t in allowed_tools_raw.split(",") if t.strip()]

        download_dir = Path(environ.get("DOWNLOAD_DIR", "/tmp/second-brain-kit-files"))
        download_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            discord_token=token,
            owner_id=int(owner_id),
            vault_path=vault_path,
            claude_model=environ.get("CLAUDE_MODEL", "sonnet"),
            max_budget_usd=float(environ.get("MAX_BUDGET_USD", "1.00")),
            allowed_tools=allowed_tools,
            download_dir=download_dir,
        )
