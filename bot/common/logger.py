import logging


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger("my-hosting-bot")
