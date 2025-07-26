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
from .upload import modified_files
from .upload import stage
from .upload import upload_configs


class PersistanceMode(Enum):
    ENABLED = 1
    """ENABLED indicates that all changes will persist on the host, and in change control."""

    ONLY_HOST = 2
    """ONLY_HOST indicates that changes will only persist on the host (and not in change control.)"""

    DISABLED = 3
    """DISABLED indicates that changes will not persist."""

    REVERT = 4
    """REVERT is the inverse of ONLY_HOST, and restores backups without uploading any changes."""


def run(
    commit_msg: str,
    host: str = "homeassistant",
    mode: PersistanceMode = PersistanceMode.ENABLED,
):
    """
    :param host: ssh target to connect to
    """
    r = runner(
        conn=Connection(host=host),
        ha=homeassistant(base="control.home"),
        mode=mode,
    )
    if mode == PersistanceMode.REVERT:
        r.restore(*synchronized_files)
    else:
        has_changes = r.deploy(*synchronized_files)
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
        services_to_reload = set()
        for cfg in cfgs:
            # TODO(2025-07-25): There's a strange edge case here where running with
            # PersistanceMode.DISABLED right after PersistenceMode.ONLY_HOST would cause a
            # revert without a system reload. Perhaps a better way to do this is to prevent
            # executions with PersistanceMode.DISABLED until PersistanceMode.REVERT is run.
            changes = upload_configs(conn=self._conn, path=cfg.path)
            if not changes.files:
                # Nothing to do!
                continue

            try:
                warnings = cfg.validate(self._ha, *changes.new_files)
                if warnings:
                    logger.warning(warnings)
                    if not force:
                        raise ConfigurationError(warnings)

            except ConfigurationError as e:
                logger.error(str(e))

                changes.revert()
                continue

            if self.mode == PersistanceMode.ENABLED:
                changes.commit()

            if self.mode != PersistanceMode.DISABLED:
                # ONLY_HOST and ENABLED should reload services.
                if cfg.service:
                    services_to_reload.add(cfg.service)
            else:
                changes.revert()

        if not services_to_reload:
            return False

        self._ha.reload(*list(services_to_reload))
        return True

    def restore(self, *cfgs: SynchronizedConfig) -> bool:
        # Flatten files
        staged: list[File] = []
        services_to_reload: list[str] = []
        for cfg in cfgs:
            # TODO(2025-07-25): We can probably do better here. The issue is that stage.revert() is
            # the only time when we identify if there are any changes. However, we want to feed it
            # all the files (so we can delete in bulk), yet want to be able to not feed it all the
            # files (so that we can determine which services to reload).
            if cfg.service:
                services_to_reload.append(cfg.service)

            staged.extend(modified_files(cfg.path))

        stage(conn=self._conn, staged=staged).revert()
        self._ha.reload(*services_to_reload)
