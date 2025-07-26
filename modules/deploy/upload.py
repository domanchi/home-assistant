"""
This file manages uploads with the following mental model:

1.  The server is assumed to be in the same state as the local client.

2.  Target files are determined through the set intersection between git staged files
    and tracked directories (as defined in config.py).

3.  For a deploy to be successful, it needs a "double commit": the first "commit" is through
    uploading the file, and the second "commit" is by not reverting it.

4.  Depending on the nature of the change, the file may undergo one of the following workstreams:

      |  Change Type  |    On Upload    | On Revert |   On Commit
    A |    NEW FILE   |      Upload     |   Delete  |      Noop
    B |    MODIFIED   |  Backup, Upload |  Restore  | Delete Backup
    C |    DELETED    |      Backup     |  Restore  | Delete Backup
"""
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


def modified_files(path: str):
    """Returns the set intersection between git staged files and tracked directories."""
    return _modified_files(git, path)


def _modified_files(g: Git, path: str):
    path = os.path.join(g.root, path)
    if not os.path.isdir(path) and not os.path.isfile(path):
        raise ValueError(f"no such path: '{path}'")

    root = g.root
    if not path.startswith(root):
        raise ValueError(f"path '{path}' not in git directory '{root}'")

    path = path[len(root.rstrip("/") + "/"):].rstrip("/")

    for file in g.staged_files:
        if os.path.commonpath([path, file.name]) != path:
            continue

        yield file


class config_uploader:
    """This is used so that we can do better testing."""
    def __init__(self, g: Git, conn: Connection) -> None:
        # Public for easier testing.
        self.conn = conn

        self._git = g

    def upload(self, path: str) -> "stage":
        """
        :param path: relative path (compared to git root) to upload to remote host
        :raises: ValueError
        """
        # NOTE: We assume that the `/config` directory is a mirror copy of local env.
        staged: list[File] = []
        for file in _modified_files(self._git, path):
            staged.append(file)
            if file.operation != FileOperation.ADDED:
                try:
                    self.conn.do("test", "-e", f"/{file.name}.bak")
                except subprocess.CalledProcessError:
                    # Don't override backups with potentially tainted files.
                    self.conn.do(
                        "/bin/mv", f"/{file.name}", f"/{file.name}.bak",
                    )

            if file.operation == FileOperation.DELETED:
                continue

            try:
                self.conn.copy(file.name, f"/{file.name}")
            except subprocess.CalledProcessError as e:
                logger.error(e.stderr.decode())
                raise

        if staged:
            logger.info("files uploaded to server")

        return stage(conn=self.conn, staged=staged)


class stage:
    """
    We perform our upload in two steps:
        1.  Initial files
        2.  Commit/revert changes

    This is so that we can perform validation on the production server, before merging it.
    This class handles that second step, and assumes that all files have already been uploaded.
    Now it's a question of whether we keep the changes.
    """
    def __init__(self, conn: Connection, staged: list[File]) -> None:
        self.conn = conn
        self._files = staged

    @property
    def files(self) -> list[str]:
        """Returns a list of all filenames."""
        return [f.name for f in self._files]

    @property
    def new_files(self) -> list[str]:
        """Returns a list of newly added/modified files."""
        return [
            f.name
            for f in self._files

            # NOTE: Won't be able to read files if it is deleted.
            if f.operation != FileOperation.DELETED
        ]

    def commit(self) -> None:
        """
        Commit verifies the change, and removes backups.
        """
        to_delete: list[str] = []
        for file in self._files:
            if file.operation == FileOperation.ADDED:
                continue
            else:
                to_delete.append(f"/{file.name}.bak")

        self._delete(*to_delete)
        logger.info("changes committed to server")

    def revert(self) -> bool:
        """
        During revert, new files are removed, and backups are restored.

        :rtype: true if any files were modified.
        """
        has_changes = False

        to_delete: list[str] = []
        for file in self._files:
            if file.operation == FileOperation.ADDED:
                to_delete.append(f"/{file.name}")
                continue

            try:
                self.conn.do("test", "-e", f"/{file.name}.bak")
                self.conn.do("/bin/mv", f"/{file.name}.bak", f"/{file.name}")
                has_changes = True
            except subprocess.CalledProcessError:
                # If no backup exist, nothing to restore.
                pass
        
        if to_delete:
            has_changes = True
            self._delete(*to_delete)

        if has_changes:
            logger.info("changes reverted from server")

        return has_changes

    def _delete(self, *files: str) -> None:
        """
        Prefer to specify multiple paths to minimize on transaction costs.
        """
        if not files:
            return

        # NOTE: Use -f here, so that we can ignore errors that are thrown if the
        # file is missing.
        self.conn.do("rm", "-f", *files)
