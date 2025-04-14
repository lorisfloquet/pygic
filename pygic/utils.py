import logging
import sys
from enum import Enum

from termcolor import colored


class ColorFormatter(logging.Formatter):
    """A formatter that colors the log messages based on their level."""

    BASE_FORMAT: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: colored(BASE_FORMAT, "cyan"),
        logging.INFO: colored(BASE_FORMAT, "green"),
        logging.WARNING: colored(BASE_FORMAT, "yellow"),
        logging.ERROR: colored(BASE_FORMAT, "red"),
        logging.CRITICAL: colored(BASE_FORMAT, "red", attrs=["bold"]),
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.BASE_FORMAT)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class LoggingLevel(Enum):
    """Logging level possible values."""

    DEBUG: int = logging.DEBUG
    INFO: int = logging.INFO
    WARNING: int = logging.WARNING
    ERROR: int = logging.ERROR
    CRITICAL: int = logging.CRITICAL


def setup_logging(log_level: LoggingLevel | int | None = None) -> None:
    """Setup logging for the application.

    Args:
        log_level (LoggingLevel | int | None, optional): The log level to set.
            If None, the default logging level is WARNING. Defaults to None.
    """

    if log_level is not None:
        if isinstance(log_level, int):
            log_level = LoggingLevel(log_level)
        _log_level = log_level.value
    else:
        # Default to WARNING level
        _log_level = logging.WARNING

    # Root logger
    logger = logging.getLogger()

    # Set the log level
    logger.setLevel(_log_level)

    # Console handler with color formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_log_level)
    console_handler.setFormatter(ColorFormatter())
    logger.addHandler(console_handler)
