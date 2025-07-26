from typing import Optional
import os

import pytest

from modules.deploy.git import File
from modules.deploy.git import FileOperation
from modules.deploy.upload import config_uploader


class TestUploadConfigs:
    @staticmethod
    def test_no_staged_files(tempdir):
        u = uploader()
        u.upload(tempdir)

    @staticmethod
    def test_not_a_path():
        u = uploader()

        with pytest.raises(ValueError):
            u.upload("/no/way/this/exists")

    @staticmethod
    def test_basic(tempdir):
        u = uploader(
            staged_files=[
                File(
                    name="fileA",
                    operation=FileOperation.ADDED,
                ),
                File(
                    name="fileB",
                    operation=FileOperation.MODIFIED,
                ),
                File(
                    name="fileC",
                    operation=FileOperation.DELETED,
                ),
            ]
        )

        changes = u.upload(tempdir)
        assert [
            "scp fileA homeassistant@/fileA",

            # NOTE: The test doesn't copy /bin/mv because the stub doesn't raise a
            # CalledProcessError.
            "ssh homeassistant test -e /fileB.bak",
            "scp fileB homeassistant@/fileB",

            "ssh homeassistant test -e /fileC.bak",
        ] == u.conn.commands

        u.conn.commands = []
        changes.revert()
        assert u.conn.commands == [
            "ssh homeassistant test -e /fileB.bak",
            "ssh homeassistant /bin/mv /fileB.bak /fileB",
            "ssh homeassistant test -e /fileC.bak",
            "ssh homeassistant /bin/mv /fileC.bak /fileC",
            "ssh homeassistant rm -f /fileA",
        ]

        u.conn.commands = []
        changes.commit()
        assert u.conn.commands == [
            "ssh homeassistant rm -f /fileB.bak /fileC.bak",
        ]


def uploader(
    staged_files: Optional[list[File]] = None,
):
    if not staged_files:
        staged_files = []

    return config_uploader(
        g=mock_git(staged_files),
        conn=spy(),
    )


class mock_git:
    def __init__(self, files: list[File]):
        self._files = files

    @property
    def staged_files(self) -> list[File]:
        return self._files


@pytest.fixture(autouse=True)
def setup_mock_git(tempdir):
    mock_git.root = tempdir


class spy:
    def __init__(self):
        self.commands: list[str] = []

    def do(self, *args: str) -> None:
        self.commands.append(" ".join(["ssh", "homeassistant", *args]))

    def copy(self, src: str, dest: str) -> None:
        self.commands.append(" ".join(["scp", src, f"homeassistant@{dest}"]))
