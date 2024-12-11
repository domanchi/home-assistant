from typing import Optional
import os

import pytest

from deploy.git import File
from deploy.git import FileOperation
from deploy.upload import config_uploader


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
            "scp fileA homeassistant@/config/fileA",

            "ssh homeassistant mv /config/fileB /config/fileB.bak",
            "scp fileB homeassistant@/config/fileB",
        ] == u.conn.commands

        u.conn.commands = []
        changes.revert()
        assert u.conn.commands == [
            "ssh homeassistant mv /config/fileB.bak /config/fileB",
            "ssh homeassistant rm /config/fileA",
        ]

        u.conn.commands = []
        changes.commit()
        assert u.conn.commands == [
            "ssh homeassistant rm /config/fileB.bak /config/fileC",
        ]

    @staticmethod
    def test_bulk_delete(tempdir):
        u = uploader(
            staged_files=[
                File(
                    name="fileA",
                    operation=FileOperation.DELETED,
                ),
                File(
                    name="fileB",
                    operation=FileOperation.DELETED,
                ),
            ],
        )

        changes = u.upload(tempdir)
        assert not u.conn.commands

        changes.revert()
        assert not u.conn.commands


        changes.commit()
        assert u.conn.commands == [
            "ssh homeassistant rm /config/fileA /config/fileB",
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
