/** Response from a Claude interaction */
export interface ClaudeResponse {
  /** Claude's text response */
  text: string;

  /** Session ID for conversation continuity (CLI provider only) */
  sessionId: string | null;

  /** Cost of this turn in USD */
  costUsd: number;

  /** Duration in milliseconds */
  durationMs: number;

  /** Whether this response is an error */
  isError: boolean;
}

/** Common interface for Claude providers */
export interface ClaudeProvider {
  /**
   * Send a prompt to Claude and get a response.
   *
   * @param prompt - User message text
   * @param options - Additional options
   * @returns Claude's response
   */
  run(prompt: string, options?: RunOptions): Promise<ClaudeResponse>;

  /**
   * Kill any running Claude process for the given channel.
   * Only applicable for CLI provider.
   */
  kill(channelId: string): Promise<void>;
}

export interface RunOptions {
  /** Channel ID for process tracking (CLI provider) */
  channelId?: string;

  /** Resume a previous session (CLI provider) */
  sessionId?: string;

  /** Override the default model */
  model?: string;

  /** System prompt */
  systemPrompt?: string;

  /** Working directory for file operations */
  cwd?: string;

  /** Conversation history for context (API provider) */
  messages?: Array<{ role: "user" | "assistant"; content: string }>;
}
