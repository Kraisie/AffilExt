import logging
import multiprocessing
from logging import handlers

import util


# based on https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes


def configure_process_logger(log_queue: multiprocessing.Queue) -> None:
    logger = logging.getLogger()
    logger.setLevel(util.LOG_LEVEL)
    handler = logging.handlers.QueueHandler(log_queue)
    logger.addHandler(handler)


def _logger_thread(log_queue: multiprocessing.Queue) -> None:
    util.configure_logger(logging.getLogger())
    while True:
        log_record = log_queue.get()
        if log_record is None:  # check for sentinel value
            break

        logger = logging.getLogger(log_record.name)
        logger.handle(log_record)


def start_logging_thread(log_queue: multiprocessing.Queue):
    # based on https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes
    # multiprocess.Process instead of threading.Thread due to issues with deadlocks when using a multiprocess.Pool
    # https://stackoverflow.com/questions/65080123/python-multiprocessing-pool-some-process-in-deadlock-when-forked-but-runs-when-s
    logging_thread = multiprocessing.Process(target=_logger_thread, args=[log_queue], daemon=True)
    logging_thread.start()
    return logging_thread
