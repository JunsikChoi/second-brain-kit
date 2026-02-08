import winston from "winston";

const { combine, timestamp, printf, colorize } = winston.format;

const logFormat = printf(({ level, message, timestamp: ts, label }) => {
  return `${ts} [${label}] ${level}: ${message}`;
});

export function createLogger(label: string): winston.Logger {
  return winston.createLogger({
    level: process.env.LOG_LEVEL ?? "info",
    format: combine(
      timestamp({ format: "HH:mm:ss" }),
      winston.format.label({ label }),
      colorize(),
      logFormat,
    ),
    transports: [new winston.transports.Console()],
  });
}
