from logging import LogRecord, getLogger


def _is_not_scanner_cancellation(record: LogRecord) -> bool:
    # IBKR answers every scanner cancel with error 162; ib_async cancels after each one-shot scan.
    return "API scanner subscription cancelled" not in record.getMessage()


getLogger("ib_async.wrapper").addFilter(_is_not_scanner_cancellation)
