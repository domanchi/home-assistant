import os
import tempfile

import pytest

from deploy import logger


@pytest.fixture
def tempdir():
    with tempfile.TemporaryDirectory() as name:
        yield os.path.abspath(name)


@pytest.fixture(autouse=True)
def disable_logging():
    logger.configure_verbosity(0)
