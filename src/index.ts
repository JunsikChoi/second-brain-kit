import { loadConfig } from "./config.js";
import { createClaudeProvider } from "./claude/index.js";
import { createLogger } from "./logger.js";

const logger = createLogger("main");

async function main() {
  logger.info("Starting Second Brain Kit...");

  const config = loadConfig();
  logger.info(`Provider: ${config.claudeProvider}`);
  logger.info(`Model: ${config.claudeModel}`);
  logger.info(`Vault: ${config.vaultPath}`);

  const claude = createClaudeProvider(config);
  logger.info(`Claude provider ready (${config.claudeProvider})`);

  // TODO: Initialize modules
  // - Discord bot (discord.js)
  // - Vault manager (read/write/search markdown)
  // - MCP manager (install/configure MCP servers)

  // Keep reference to prevent GC
  void claude;
}

main().catch((err) => {
  logger.error("Fatal error:", err);
  process.exit(1);
});
