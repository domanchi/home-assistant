import shlex
import subprocess

from .logger import logger


class Connection:
    """Houses logic for interacting with remote server."""
    def __init__(self, host: str):
        self._host = host

    def do(self, *args: str) -> bytes:
        """
        :raises: CalledProcessError on ssh failure
        """
        # NOTE: We don't capture logging because we don't want to accidentally capture API keys.
        command = ["ssh", self._host, shlex.join(args)]
        logger.debug(shlex.join(command))
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        return result.stdout

    def copy(self, src: str, dest: str) -> None:
        """
        :raises: CalledProcessError on git operation failure
        """
        command = ["scp", src, f"{self._host}:{dest}"]
        logger.debug(shlex.join(command))

        return subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
