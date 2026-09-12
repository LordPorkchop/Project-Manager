import datetime as dt
from pathlib import Path
import sys
import traceback

from src.config.config import (
    get_config as _get_config,
)  # Private import to prevent 'from logger import get_config'


class LogLevel:
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    EXCEPTION = 50

    _NAME_MAP = {
        DEBUG: "DBG",
        INFO: "INF",
        WARNING: "WRN",
        ERROR: "ERR",
        EXCEPTION: "EXC",
    }

    _FROM_STRING = {
        "DEBUG": DEBUG,
        "INFO": INFO,
        "WARNING": WARNING,
        "ERROR": ERROR,
        "EXCEPTION": EXCEPTION,
    }

    @classmethod
    def resolve(cls, value) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return cls._FROM_STRING.get(value.upper(), cls.DEBUG)
        return cls.DEBUG

    @classmethod
    def name(cls, level: int) -> str:
        return cls._NAME_MAP.get(level, "UNK")


class _Color:
    RESET = "\033[0m"
    DEBUG = "\033[90m"  # Light gray
    INFO = "\033[34m"  # Mid blue
    WARNING = "\033[33m"  # Amber / yellow
    ERROR = "\033[31m"  # Red
    EXCEPTION = "\033[35m"  # Purple

    _MAP = {
        LogLevel.DEBUG: DEBUG,
        LogLevel.INFO: INFO,
        LogLevel.WARNING: WARNING,
        LogLevel.ERROR: ERROR,
        LogLevel.EXCEPTION: EXCEPTION,
    }

    @classmethod
    def for_level(cls, level: int) -> str:
        return cls._MAP.get(level, "")


class Logger:
    def __init__(self, name: str):
        self.name = name
        self._config = _get_config()
        self._log_level = LogLevel.resolve(
            self._config.read("logLevel") or LogLevel.DEBUG
        )
        self._log_mode = self._config.read("logMode") or "console"
        self._log_location = self._config.read("logFilePath") or "./src/logs"

    def debug(self, msg: str):
        self._log(LogLevel.DEBUG, msg)

    def info(self, msg: str):
        self._log(LogLevel.INFO, msg)

    def warning(self, msg: str):
        self._log(LogLevel.WARNING, msg)

    def error(self, msg: str):
        self._log(LogLevel.ERROR, msg)

    def exception(self, msg: str):
        tb = traceback.format_exc()
        full_msg = msg if tb.strip() == "None" else f"{msg}\n{tb.rstrip()}"
        self._log(LogLevel.EXCEPTION, full_msg)

    def _log(self, level: int, message: str) -> None:
        if level < self._log_level:
            return

        now = dt.datetime.now()
        timestamp = (
            now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond // 1000:03d}"
        )
        level_name = LogLevel.name(level)
        plain_line = f"[{timestamp}][{level_name}][{self.name}] {message}"

        if self._log_mode in ("console", "both"):
            color = _Color.for_level(level)
            color_line = f"{color}{plain_line}{_Color.RESET}"
            stream = sys.stderr if level >= LogLevel.ERROR else sys.stdout
            print(color_line, file=stream)

        if self._log_mode in ("file", "both"):
            self._write_to_file(plain_line)

    def _write_to_file(self, plain_line: str):
        fp = Path(self._log_location) / "app.log"
        with open(fp, "a", encoding="utf-8") as file:
            file.write(plain_line)


def get_logger(name: str) -> Logger:
    return Logger(name)
