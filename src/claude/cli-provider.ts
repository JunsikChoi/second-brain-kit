import { spawn, type ChildProcess } from "node:child_process";
import type { Config } from "../config.js";
import { createLogger } from "../logger.js";
import type { ClaudeProvider, ClaudeResponse, RunOptions } from "./types.js";

const logger = createLogger("claude-cli");

/**
 * Claude provider using Claude Code CLI (`claude -p`).
 * Uses the user's existing Claude Code subscription — no API key needed.
 */
export class CliProvider implements ClaudeProvider {
  private runningProcs = new Map<string, ChildProcess>();

  constructor(private config: Config) {}

  async run(prompt: string, options?: RunOptions): Promise<ClaudeResponse> {
    const start = Date.now();
    const args = this.buildArgs(prompt, options);

    logger.debug(`Running: ${this.config.claudePath} ${args.join(" ")}`);

    const channelId = options?.channelId ?? "default";

    return new Promise((resolve, reject) => {
      const proc = spawn(this.config.claudePath, args, {
        cwd: options?.cwd,
        env: { ...process.env },
      });

      this.runningProcs.set(channelId, proc);

      let stdout = "";
      let stderr = "";

      proc.stdout?.on("data", (data: Buffer) => {
        stdout += data.toString();
      });

      proc.stderr?.on("data", (data: Buffer) => {
        stderr += data.toString();
      });

      proc.on("error", (err) => {
        this.runningProcs.delete(channelId);
        reject(
          new Error(
            `Failed to run Claude CLI: ${err.message}. Is Claude Code installed?`,
          ),
        );
      });

      proc.on("close", (code) => {
        this.runningProcs.delete(channelId);
        const durationMs = Date.now() - start;

        const raw = stdout || stderr;
        try {
          const response = this.parseOutput(raw, durationMs);
          if (code !== 0 && !response.text) {
            reject(new Error(`Claude CLI exited with code ${code}: ${raw}`));
          } else {
            resolve(response);
          }
        } catch (err) {
          reject(
            new Error(
              `Failed to parse Claude CLI output: ${err instanceof Error ? err.message : err}`,
            ),
          );
        }
      });
    });
  }

  async kill(channelId: string): Promise<void> {
    const proc = this.runningProcs.get(channelId);
    if (proc) {
      proc.kill("SIGTERM");
      this.runningProcs.delete(channelId);
      logger.info(`Killed Claude process for channel ${channelId}`);
    }
  }

  private buildArgs(prompt: string, options?: RunOptions): string[] {
    const args = [
      "-p",
      prompt,
      "--output-format",
      "json",
      "--dangerously-skip-permissions",
      "--model",
      options?.model ?? this.config.claudeModel,
      "--max-budget-usd",
      String(this.config.maxBudgetUsd),
    ];

    if (options?.sessionId) {
      args.push("--resume", options.sessionId);
    }

    if (options?.systemPrompt) {
      args.push("--system-prompt", options.systemPrompt);
    }

    return args;
  }

  private parseOutput(raw: string, durationMs: number): ClaudeResponse {
    // Extract JSON from potentially mixed output
    const jsonStart = raw.indexOf("{");
    const jsonEnd = raw.lastIndexOf("}");

    if (jsonStart === -1 || jsonEnd === -1) {
      // No JSON found — treat raw output as text response
      return {
        text: raw.trim(),
        sessionId: null,
        costUsd: 0,
        durationMs,
        isError: true,
      };
    }

    const jsonStr = raw.slice(jsonStart, jsonEnd + 1);
    const parsed = JSON.parse(jsonStr) as Record<string, unknown>;

    return {
      text: (parsed.result ?? parsed.text ?? "") as string,
      sessionId: (parsed.session_id ?? null) as string | null,
      costUsd: Number(parsed.total_cost_usd ?? parsed.cost_usd ?? 0),
      durationMs: Number(parsed.duration_ms ?? durationMs),
      isError: Boolean(parsed.is_error),
    };
  }
}
