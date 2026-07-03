import logging
import os


def setup_logger(name, log_file=None, level=logging.INFO, verbose=False):
    """Set up an idempotent console/file logger."""
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else level)
    logger.propagate = False

    console_level = logging.DEBUG if verbose else logging.INFO
    has_console = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in logger.handlers
    )
    if not has_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(console_level)
        logger.addHandler(console_handler)
    else:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handler.setLevel(console_level)

    if log_file:
        target_path = os.path.abspath(log_file)
        has_file = any(
            isinstance(handler, logging.FileHandler) and handler.baseFilename == target_path
            for handler in logger.handlers
        )
        if not has_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            logger.addHandler(file_handler)

    return logger
