import os
import sys

from .connection import Connection
from .git import git
from .logger import logger
from .homeassistant import ConfigurationError
from .homeassistant import homeassistant
from .upload import upload_configs


def run(
    commit_msg: str,
    host: str = "homeassistant",
    dry_run: bool = True,
):
    """
    :param host: ssh target to connect to
    """
    if not git.staged_files:
        print("no staged files to deploy", file=sys.stderr)
        return

    conn = Connection(host=host)
    ha = homeassistant(conn=conn)

    # TODO: We should probably push this into config_uploader, when we need to handle more than
    # automations.
    has_failed = False
    for path in synchronized_paths(git.root):
        changes = upload_configs(
            conn=conn,
            path=path,
        )

        try:
            ha.check_configs()
        except ConfigurationError as e:
            has_failed = True
            logger.error(str(e))
            changes.revert()
            continue

        if dry_run:
            has_failed = True
            changes.revert()
            return

        changes.commit()
        ha.reload()

    if not has_failed:
        git.commit(commit_msg)
        git.merge()


def synchronized_paths(root: str) -> list[str]:
    return [
        os.path.join(git.root, "automations"),
    ]