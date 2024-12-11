import os
import subprocess

from .connection import Connection
from .git import git
from .git import Git
from .git import File
from .git import FileOperation
from .logger import logger


def upload_configs(conn: Connection, path: str) -> "stage":
    """
    Uploads configuration that is git staged.

    :param path: absolute path to configuration directory to upload.
    :raises: ValueError
    """
    return config_uploader(git, conn=conn).upload(path)


class config_uploader:
    """This is used so that we can do better testing."""
    def __init__(self, g: Git, conn: Connection) -> None:
        # Public for easier testing.
        self.conn = conn

        self._git = g

    def upload(self, path: str) -> "stage":
        """
        :param path: absolute directory (prefix) to upload to remote host
        :raises: ValueError
        """
        if not os.path.isdir(path):
            raise ValueError(f"no such path: '{path}'")

        root = self._git.root
        if not path.startswith(root):
            raise ValueError(f"path '{path}' not in git directory '{root}'")

        path = path[len(root.rstrip("/") + "/"):].rstrip("/")

        staged: list[File] = []
        for file in self._git.staged_files:
            if os.path.commonpath([path, file.name]) != path:
                continue

            staged.append(file)
            if file.operation == FileOperation.DELETED:
                continue

            if file.operation == FileOperation.MODIFIED:
                self.conn.do("mv", f"/{file.name}", f"/{file.name}.bak")

            try:
                self.conn.copy(file.name, f"/{file.name}")
            except subprocess.CalledProcessError as e:
                logger.error(e.stderr.decode())
                raise

        logger.info("files uploaded to server")
        return stage(conn=self.conn, staged=staged)


class stage:
    """
    We perform our upload in two steps:
        1.  Initial files
        2.  Commit/revert changes

    This is so that we can perform validation on the production server, before merging it.
    """
    def __init__(self, conn: Connection, staged: list[File]) -> None:
        self.conn = conn
        self.files = staged

    def commit(self) -> None:
        """During commit, old files are deleted."""
        to_delete: list[str] = []
        for file in self.files:
            if file.operation == FileOperation.ADDED:
                continue

            elif file.operation == FileOperation.MODIFIED:
                to_delete.append(f"/{file.name}.bak")

            elif file.operation == FileOperation.DELETED:
                to_delete.append(f"/{file.name}")

        self._delete(*to_delete)
        logger.info("changes committed to server")

    def revert(self) -> None:
        """During revert, new files are removed, and backups are restored."""
        to_delete: list[str] = []
        for file in self.files:
            if file.operation == FileOperation.DELETED:
                continue

            elif file.operation == FileOperation.MODIFIED:
                self.conn.do("mv", f"/{file.name}.bak", f"/{file.name}")
            
            elif file.operation == FileOperation.ADDED:
                to_delete.append(f"/{file.name}")
        
        self._delete(*to_delete)
        logger.info("changes reverted from server")

    def _delete(self, *files: str) -> None:
        """
        Prefer to specify multiple paths to minimize on transaction costs.
        """
        if not files:
            return

        self.conn.do("rm", *files)
