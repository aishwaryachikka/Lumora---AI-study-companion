"""Logging setup with a consistent application-wide format."""

import logging


def configure_logging(level: str) -> None:
    """Configure standard-library logging without recording secrets or payloads."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
