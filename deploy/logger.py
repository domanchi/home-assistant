import logging


logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)


def configure_verbosity(count: int) -> None:
    if count < 1:
        logger.level = logging.WARN
    elif count == 1:
        logger.level = logging.INFO
    else:
        logger.level = logging.DEBUG
