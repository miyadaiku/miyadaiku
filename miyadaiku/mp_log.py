from __future__ import annotations


from typing import Any, List, Dict

import logging, logging.config
import traceback

_queue: Any = None
_pendings: List[Dict[str, Any]] = []


class MpLogFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: Any = None,
        datefmt: Any = None,
        style: Any = "%",
        validate: Any = True,
        traceback: bool = False,
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)
        self.traceback = traceback

    def format_dict(self, record: Any) -> Dict[str, Any]:
        record.message = record.getMessage()

        d = {}
        d["levelno"] = record.levelno
        d["msg"] = self.formatMessage(record)
        if record.exc_info:
            if self.traceback:
                d["exc"] = self.formatException(record.exc_info)
            else:
                d["exc"] = str(record.exc_info[1])

        if record.stack_info:
            if self.traceback:
                d["stack"] = self.formatStack(record.stack_info)
            else:
                d["stack"] = ""

        return d


class MpLogHandler(logging.Handler):
    def __init__(self, level: int = logging.NOTSET, traceback: bool = False) -> None:
        super().__init__(level=level)
        self.dictformatter = MpLogFormatter(traceback=traceback)

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


def init_mp_logging(traceback: bool, queue: Any) -> None:
    global _queue
    _queue = queue

    global _pendings
    _pendings = []

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {"": {"level": "DEBUG", "handlers": ["streamhandler"]},},
        "handlers": {
            "streamhandler": {
                "()": lambda: MpLogHandler(level=logging.DEBUG, traceback=traceback)
            }
        },
    }

    logging.config.dictConfig(LOGGING)


def flush_mp_logging() -> None:
    global _pendings
    if _pendings:
        _queue.put(("LOGS", _pendings))
        _pendings = []


class ParentFormatter(logging.Formatter):
    traceback: bool

    def __init__(
        self,
        fmt: Any = None,
        datefmt: Any = None,
        style: Any = "%",
        validate: Any = True,
        traceback: Any = False,
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)
        self.traceback = traceback

    def formatException(self, ei: Any) -> str:
        if self.traceback:
            return super().formatException(ei)
        return str(ei[1])

    def formatStack(self, stack_info: Any) -> str:
        if self.traceback:
            return super().formatStack(stack_info)
        return ""

    def format(self, record: Any) -> str:
        msgdict = getattr(record, "msgdict", None)
        if not msgdict:
            return super().format(record)

        s: str = msgdict["msg"]

        exc = msgdict.get("exc")
        if exc:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + exc

        if self.traceback:
            stack = msgdict.get("stack")
            if stack:
                if s[-1:] != "\n":
                    s = s + "\n"
                s = s + stack

        return s


def init_logging(traceback: bool = False) -> None:

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
        "formatters": {"berief": {"()": lambda: ParentFormatter(traceback=traceback)}},
    }

    logging.config.dictConfig(LOGGING)
