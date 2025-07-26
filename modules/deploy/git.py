from dataclasses import dataclass
from enum import Enum
import subprocess

from .logger import logger


class Git:
    """Stub-able interface to interact with `git`."""

    def __init__(self, root: str = "") -> None:
        """
        :param root: optionally specify the root directory of where git should operate.
            If not provided, will perform git operations on current directory.
        """
        self._root = root
        self._staged: list["File"] = []

    @property
    def root(self) -> str:
        """Returns the root of the git directory."""
        if not self._root:
            self._root = self.do("rev-parse", "--show-toplevel").strip()

        return self._root

    @property
    def staged_files(self) -> list["File"]:
        """
        :raises: CalledProcessError on git operation failure
        """
        if self._staged:
            return self._staged

        result = self.do("diff", "--staged", "--name-status")
        files: list["File"] = []
        for line in result.splitlines():
            parts = line.split("\t")
            if parts[0][0] == "R":
                # Handle renames
                files.extend([
                    File(
                        name=parts[1],
                        operation=FileOperation.DELETED,
                    ),
                    File(
                        name=parts[2],
                        operation=FileOperation.ADDED,
                    ),
                ])

            else:
                files.append(
                    File(
                        name=parts[1],
                        operation=FileOperation.parse(parts[0]),
                    ),
                )

        self._staged = files
        return files

    def commit(self, msg: str) -> None:
        """
        Commits staged files.

        :raises: CalledProcessError on git operation failure.
        """
        logger.info("committing staged files")
        self.do("commit", "--message", msg)
        self._staged = []

    def merge(self) -> None:
        """Pushes to master branch."""
        logger.info("merging changes to git")
        print("git pull origin master")
        print("git push origin HEAD")
        # TODO: enable
        # subprocess.call("git push origin HEAD".split())

    def do(self, *args) -> str:
        """
        :raises: CalledProcessError on git operation failure
        """
        if self._root:
            args = ["-C", self._root, *args]

        self._staged = []   # can't assume anything about "do" operations
        logger.debug(" ".join(["/usr/bin/git", *args]))
        return subprocess.run(
            ["/usr/bin/git", *args],
            capture_output=True,
            text=True,
            check=True,
        ).stdout


git = Git()


@dataclass
class File:
    name: str
    operation: "FileOperation"


class FileOperation(Enum):
    ADDED = 1
    MODIFIED = 2
    DELETED = 3

    @classmethod
    def parse(cls, letter: str) -> "FileOperation":
        """
        :raises: KeyError on invalid letter
        """
        # See https://git-scm.com/docs/git-diff#Documentation/git-diff.txt---diff-filterACDMRTUXB82308203
        # for more details.
        return {
            "A": FileOperation.ADDED,
            "M": FileOperation.MODIFIED,
            "D": FileOperation.DELETED,
        }[letter]
