from __future__ import annotations

import enum
import logging
import logging.config
import sys
import traceback
from typing import Any, Dict, List

_queue: Any = None
_pendings: List[Dict[str, Any]] = []


class MpLogFormatter(logging.Formatter):
    def __init__(self, fmt: Any = None, datefmt: Any = None, style: Any = "%",) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def format_dict(self, record: Any) -> Dict[str, Any]:
        record.message = record.getMessage()

        d = {}
        d["levelno"] = record.levelno
        d["msg"] = self.formatMessage(record)
        if record.exc_info:
            d["exc"] = self.formatException(record.exc_info)

        if record.stack_info:
            d["stack"] = self.formatStack(record.stack_info)

        return d


class MpLogHandler(logging.Handler):
    def __init__(self, level: int = logging.NOTSET) -> None:
        super().__init__(level=level)
        self.dictformatter = MpLogFormatter()

    def emit(self, record: Any) -> None:
        try:
            msg = self.dictformatter.format_dict(record)
            _pendings.append(msg)

        except RecursionError:
            raise
        except Exception:
            traceback.print_exc()
            self.handleError(record)

    def __repr__(self) -> str:
        level = logging.getLevelName(self.level)
        return "<%s(%s)>" % (self.__class__.__name__, level)


def init_mp_logging(queue: Any) -> None:
    global _queue
    _queue = queue

    global _pendings
    _pendings = []

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {"": {"level": "DEBUG", "handlers": ["streamhandler"]},},
        "handlers": {
            "streamhandler": {"()": lambda: MpLogHandler(level=logging.DEBUG)}
        },
    }

    logging.config.dictConfig(LOGGING)


def flush_mp_logging() -> None:
    global _pendings
    if _pendings:
        _queue.put(("LOGS", _pendings))
        _pendings = []


class Color(enum.Enum):
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


IS_ATTY = sys.stdout.isatty()


class ParentFormatter(logging.Formatter):
    def format(self, record: Any) -> str:
        red = IS_ATTY and (record.levelno >= logging.ERROR)
        msgdict = getattr(record, "msgdict", None)

        if not msgdict:
            ret = super().format(record)
            if red:
                ret = Color.RED.value + ret + Color.RESET.value
            return ret

        s: str = msgdict["msg"]

        exc = msgdict.get("exc")
        if exc:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + exc

        stack = msgdict.get("stack")
        if stack:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + stack

        if red:
            s = Color.RED.value + s + Color.RESET.value
        return s


def init_logging() -> None:

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {"": {"level": "DEBUG", "handlers": ["default"]},},
        "handlers": {
            "default": {
                "level": "INFO",
                "formatter": "berief",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            }
        },
        "formatters": {"berief": {"()": lambda: ParentFormatter()}},
    }

    logging.config.dictConfig(LOGGING)
