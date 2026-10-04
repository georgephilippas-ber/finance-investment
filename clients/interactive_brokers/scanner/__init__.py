from logging import LogRecord, getLogger


def _is_not_scanner_cancellation(record: LogRecord) -> bool:
    return "API scanner subscription cancelled" not in record.getMessage()


getLogger("ib_async.wrapper").addFilter(_is_not_scanner_cancellation)
