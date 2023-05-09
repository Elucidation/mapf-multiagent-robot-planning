"""Helper for creating loggers."""
import logging
import logging.handlers
import os


def create_warehouse_logger(name, folder='logs/curr/'):
    if not os.path.exists(folder):
        os.makedirs(folder)
    root_logger = logging.getLogger()
    file_path = f'{folder}{name}.log'
    rotating_handler = logging.handlers.TimedRotatingFileHandler(
        filename=file_path, when='H')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rotating_handler.setLevel(logging.DEBUG)
    rotating_handler.setFormatter(formatter)
    root_logger.addHandler(rotating_handler)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    stream_logger = logging.StreamHandler()
    stream_logger.setLevel(logging.INFO)
    logger.addHandler(stream_logger)
    return logger
