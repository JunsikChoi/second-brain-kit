import type { Config } from "../config.js";
import type { ClaudeProvider } from "./types.js";
import { CliProvider } from "./cli-provider.js";
import { ApiProvider } from "./api-provider.js";

export type { ClaudeProvider, ClaudeResponse, RunOptions } from "./types.js";

/**
 * Create a Claude provider based on config.
 *
 * - "cli" (default): Uses Claude Code CLI. Supports vault access, MCP, file operations.
 * - "api": Uses Anthropic API directly. Chat only — no local file access.
 */
export function createClaudeProvider(config: Config): ClaudeProvider {
  switch (config.claudeProvider) {
    case "cli":
      return new CliProvider(config);
    case "api":
      return new ApiProvider(config);
    default:
      throw new Error(
        `Unknown claude_provider: "${config.claudeProvider}". Use "cli" or "api".`,
      );
  }
}
