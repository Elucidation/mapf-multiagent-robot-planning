"""Helper for creating loggers."""
import logging
import logging.handlers
import os
import sys


def create_warehouse_logger(name, folder='logs/curr/', log_to_file=False):
    if not os.path.exists(folder):
        os.makedirs(folder)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if log_to_file:
        # Root logger with time rotating file handler
        root_logger = logging.getLogger()
        file_path = f'{folder}{name}.log'
        rotating_handler = logging.handlers.TimedRotatingFileHandler(
            filename=file_path, when='H')
        rotating_handler.setLevel(logging.DEBUG)
        rotating_handler.setFormatter(formatter)
        root_logger.addHandler(rotating_handler)

    # Building the logger for this function
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # All messages up to info to stdout, including error messages
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Error messages to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    return logger
