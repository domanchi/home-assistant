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
    should_commit: bool = True,
):
    """
    :param host: ssh target to connect to
    """
    if not git.staged_files:
        print("no staged files to deploy", file=sys.stderr)
        return

    conn = Connection(host=host)
    ha = homeassistant(base="control.home")

    # TODO: We should probably push this into config_uploader, when we need to handle more than
    # automations.
    has_failed = False
    for path in synchronized_paths(git.root):
        changes = upload_configs(
            conn=conn,
            path=path,
        )
        if not changes.files:
            continue

        try:
            ha.check_configs(*changes.files)
        except ConfigurationError as e:
            has_failed = True
            for error in e.args[0]:
                logger.error(error)

            changes.revert()
            continue

        if dry_run:
            has_failed = True
            changes.revert()
            return

        changes.commit()
        ha.reload()

    if not has_failed and should_commit:
        git.commit(commit_msg)
        git.merge()


def synchronized_paths(root: str) -> list[str]:
    return [
        os.path.join(git.root, "config/automations"),
        os.path.join(git.root, "config/scripts"),
    ]