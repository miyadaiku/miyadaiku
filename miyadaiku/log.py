from __future__ import annotations


from typing import Any

import logging, logging.config
import traceback


class MpLogFormatter(logging.Formatter):
    def format(self, record):  # type: ignore
        record.message = record.getMessage()

        d = {}
        d["msg"] = self.formatMessage(record)
        if record.exc_info:
            d["exc"] = self.formatException(record.exc_info)

        if record.stack_info:
            d["stack"] = self.formatStack(record.stack_info)

        return d


class MpLogHandler(logging.Handler):
    def __init__(self, queue: Any, level: int = logging.NOTSET) -> None:
        super().__init__(level=level)
        self.queue = queue
        self.formatter = MpLogFormatter()

    def emit(self, record: Any) -> None:
        try:
            msg = self.format(record)
            self.queue.put(("LOG", (record.levelname, msg)))
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            traceback.print_exc()
            self.handleError(record)

    def __repr__(self) -> str:
        level = logging.getLevelName(self.level)
        return "<%s(%s)>" % (self.__class__.__name__, level)


def init_mp_logging(queue: Any) -> None:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {"": {"level": "DEBUG", "handlers": ["streamhandler"]},},
        "handlers": {
            "streamhandler": {
                "()": lambda: MpLogHandler(level=logging.DEBUG, queue=queue)
            }
        },
    }

    logging.config.dictConfig(LOGGING)
