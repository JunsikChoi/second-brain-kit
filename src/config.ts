import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { parse as parseYaml } from "yaml";
import dotenv from "dotenv";

export type ClaudeProvider = "cli" | "api";

export interface Config {
  /** How to connect to Claude: "cli" (Claude Code) or "api" (Anthropic API) */
  claudeProvider: ClaudeProvider;

  /** Path to claude CLI binary (for cli provider, default: "claude") */
  claudePath: string;

  /** Anthropic API key (for api provider) */
  claudeApiKey: string | null;

  /** Claude model to use */
  claudeModel: string;

  /** Per-turn budget in USD */
  maxBudgetUsd: number;

  /** Discord bot token */
  discordToken: string;

  /** Discord owner user ID (only this user can interact) */
  ownerId: string;

  /** Path to Obsidian vault */
  vaultPath: string;

  /** Path to download directory for attachments */
  downloadDir: string;

  /** Log level */
  logLevel: string;
}

const DEFAULTS = {
  claudeProvider: "cli" as ClaudeProvider,
  claudePath: "claude",
  claudeModel: "sonnet",
  maxBudgetUsd: 1.0,
  downloadDir: "/tmp/second-brain-kit-files",
  logLevel: "info",
};

/**
 * Load config from config.yaml, .env, and environment variables.
 * Priority: env vars > .env > config.yaml > defaults
 */
export function loadConfig(configPath?: string): Config {
  dotenv.config();

  let yamlConfig: Record<string, unknown> = {};
  const yamlPath = configPath ?? resolve(process.cwd(), "config.yaml");
  if (existsSync(yamlPath)) {
    const raw = readFileSync(yamlPath, "utf-8");
    yamlConfig = (parseYaml(raw) as Record<string, unknown>) ?? {};
  }

  const get = (envKey: string, yamlKey: string): string | undefined =>
    process.env[envKey] ?? (yamlConfig[yamlKey] as string | undefined);

  const discordToken = get("DISCORD_TOKEN", "discord_token");
  if (!discordToken) {
    throw new Error(
      "DISCORD_TOKEN is required. Set it in .env, config.yaml, or environment.",
    );
  }

  const ownerId = get("OWNER_ID", "owner_id");
  if (!ownerId) {
    throw new Error(
      "OWNER_ID is required. Set it in .env, config.yaml, or environment.",
    );
  }

  const vaultPath = get("VAULT_PATH", "vault_path");
  if (!vaultPath) {
    throw new Error(
      "VAULT_PATH is required. Set it in .env, config.yaml, or environment.",
    );
  }

  const provider =
    (get("CLAUDE_PROVIDER", "claude_provider") as ClaudeProvider) ??
    DEFAULTS.claudeProvider;

  const claudeApiKey = get("CLAUDE_API_KEY", "claude_api_key") ?? null;

  if (provider === "api" && !claudeApiKey) {
    throw new Error(
      'CLAUDE_API_KEY is required when claude_provider is "api".',
    );
  }

  return {
    claudeProvider: provider,
    claudePath:
      get("CLAUDE_PATH", "claude_path") ?? DEFAULTS.claudePath,
    claudeApiKey,
    claudeModel:
      get("CLAUDE_MODEL", "claude_model") ?? DEFAULTS.claudeModel,
    maxBudgetUsd: Number(
      get("MAX_BUDGET_USD", "max_budget_usd") ?? DEFAULTS.maxBudgetUsd,
    ),
    discordToken,
    ownerId,
    vaultPath: resolve(vaultPath),
    downloadDir:
      get("DOWNLOAD_DIR", "download_dir") ?? DEFAULTS.downloadDir,
    logLevel: get("LOG_LEVEL", "log_level") ?? DEFAULTS.logLevel,
  };
}
