import Anthropic from "@anthropic-ai/sdk";
import type { Config } from "../config.js";
import { createLogger } from "../logger.js";
import type { ClaudeProvider, ClaudeResponse, RunOptions } from "./types.js";

const logger = createLogger("claude-api");

/** Model name mapping: short name → full model ID */
const MODEL_MAP: Record<string, string> = {
  sonnet: "claude-sonnet-4-5-20250929",
  opus: "claude-opus-4-6",
  haiku: "claude-haiku-4-5-20251001",
};

/**
 * Claude provider using the Anthropic API directly.
 * Requires an API key; charges per token.
 */
export class ApiProvider implements ClaudeProvider {
  private client: Anthropic;

  constructor(private config: Config) {
    if (!config.claudeApiKey) {
      throw new Error("CLAUDE_API_KEY is required for API provider.");
    }
    this.client = new Anthropic({ apiKey: config.claudeApiKey });
  }

  async run(prompt: string, options?: RunOptions): Promise<ClaudeResponse> {
    const start = Date.now();
    const modelShort = options?.model ?? this.config.claudeModel;
    const model = MODEL_MAP[modelShort] ?? modelShort;

    logger.debug(`Calling API with model: ${model}`);

    const messages: Anthropic.MessageParam[] = [];

    // Add conversation history if provided
    if (options?.messages) {
      for (const msg of options.messages) {
        messages.push({ role: msg.role, content: msg.content });
      }
    }

    // Add current prompt
    messages.push({ role: "user", content: prompt });

    try {
      const response = await this.client.messages.create({
        model,
        max_tokens: 4096,
        system: options?.systemPrompt,
        messages,
      });

      const durationMs = Date.now() - start;
      const text = response.content
        .filter((block) => block.type === "text")
        .map((block) => {
          if (block.type === "text") return block.text;
          return "";
        })
        .join("\n");

      // Estimate cost (rough: input $3/M tokens, output $15/M tokens for Sonnet)
      const inputCost =
        (response.usage.input_tokens / 1_000_000) * 3;
      const outputCost =
        (response.usage.output_tokens / 1_000_000) * 15;

      return {
        text,
        sessionId: null, // API provider doesn't have session persistence
        costUsd: inputCost + outputCost,
        durationMs,
        isError: response.stop_reason !== "end_turn",
      };
    } catch (err) {
      const durationMs = Date.now() - start;
      const message =
        err instanceof Error ? err.message : "Unknown API error";
      logger.error(`API error: ${message}`);

      return {
        text: `Error: ${message}`,
        sessionId: null,
        costUsd: 0,
        durationMs,
        isError: true,
      };
    }
  }

  async kill(_channelId: string): Promise<void> {
    // API calls can't be killed mid-flight (AbortController could be added later)
    logger.warn("Kill not supported for API provider");
  }
}
