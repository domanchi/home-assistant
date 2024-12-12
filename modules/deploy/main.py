import os
import sys
from enum import Enum

from .config import SynchronizedConfig
from .config import synchronized_files
from .connection import Connection
from .git import git
from .logger import logger
from .homeassistant import ConfigurationError
from .homeassistant import homeassistant
from .upload import upload_configs


class PersistanceMode(Enum):
    ENABLED = 1
    """ENABLED indicates that all changes will persist on the host, and in change control."""

    ONLY_HOST = 2
    """ONLY_HOST indicates that changes will only persist on the host (and not in change control.)"""

    DISABLED = 3
    """DISABLED indicates that changes will not persist."""


def run(
    commit_msg: str,
    host: str = "homeassistant",
    mode: PersistanceMode = PersistanceMode.ENABLED,
):
    """
    :param host: ssh target to connect to
    """
    has_changes = runner(
        conn=Connection(host=host),
        ha=homeassistant(base="control.home"),
    ).deploy(
        *synchronized_files,
    )

    if has_changes and mode == PersistanceMode.ENABLED:
        git.commit(commit_msg)
        git.merge()


class runner:
    """This is used so that we can do better testing."""
    def __init__(
        self,
        conn: Connection,
        ha: homeassistant,
        mode: PersistanceMode = PersistanceMode.ENABLED,
    ) -> None:
        self._conn = conn
        self._ha = ha

        self.mode = mode

    def deploy(self, *cfgs: SynchronizedConfig, force: bool = False) -> bool:
        """
        :returns: True if files have been deployed
        """
        has_changes = False
        for cfg in cfgs:
            changes = upload_configs(conn=self._conn, path=cfg.path)
            if not changes.files:
                # Nothing to upload!
                continue

            try:
                warnings = cfg.validate(self._ha, *changes.files)
                if warnings:
                    logger.warning(warnings)
                    if not force:
                        raise ConfigurationError(warnings)

            except ConfigurationError as e:
                logger.error(str(e))

                changes.revert()
                continue

            if self.mode != PersistanceMode.DISABLED:
                changes.commit()
                has_changes = True
            else:
                changes.revert()

        if not has_changes:
            return False

        self._ha.reload()
        return True
