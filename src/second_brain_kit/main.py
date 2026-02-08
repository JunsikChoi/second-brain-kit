"""Entry point for Second Brain Kit."""

import logging
import sys

from .bot import SecondBrainBot
from .config import Config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    try:
        config = Config.from_env()
    except ValueError as e:
        logging.error("Configuration error: %s", e)
        sys.exit(1)

    bot = SecondBrainBot(config)
    bot.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
