import os
import subprocess

import pytest

from modules.deploy.git import Git
from modules.deploy.git import FileOperation


class TestGit:
    @staticmethod
    def test_root(git, tempdir):
        # NOTE: We use .endswith because MacOS prefixes the /tmp directory with `/private`.
        assert git.root.endswith(tempdir)

    @staticmethod
    def test_staged_files(git, tempdir):
        with open(os.path.join(tempdir, "fileA"), "w") as f:
            f.write("does-not-matter")
        with open(os.path.join(tempdir, "fileB"), "w") as f:
            f.write("does-not-matter")

        # Not yet staged.
        assert len(git.staged_files) == 0

        # Check newly added files.
        git.do("add", "fileA")
        files = git.staged_files
        assert len(files) == 1
        assert files[0].name == "fileA"
        assert files[0].operation == FileOperation.ADDED

        # Reset.
        git.do("add", "fileB")
        git.commit("does-not-matter")
        assert len(git.staged_files) == 0

        # Make modifications.
        git.do("rm", "fileA")
        with open(os.path.join(tempdir, "fileB"), "w") as f:
            f.write("something-else")

        git.do("add", "fileB")

        # Test modifications
        files = git.staged_files
        assert len(files) == 2
        assert files[0].name == "fileA"
        assert files[0].operation == FileOperation.DELETED
        assert files[1].name == "fileB"
        assert files[1].operation == FileOperation.MODIFIED

    @staticmethod
    def test_directory(git, tempdir):
        # Setup
        os.mkdir(os.path.join(tempdir, "foo"))
        with open(os.path.join(tempdir, "foo/bar"), "w") as f:
            f.write("content")

        git.do("add", "foo/bar")

        # Assertions
        files = git.staged_files
        assert len(files) == 1
        assert files[0].name == "foo/bar"

    @staticmethod
    def test_file_move(git, tempdir):
        # Setup
        with open(os.path.join(tempdir, "foo"), "w") as f:
            f.write("does-not-matter")

        git.do("add", "foo")
        git.commit("adding file")

        subprocess.call(["mv", os.path.join(tempdir, "foo"), os.path.join(tempdir, "bar")])

        git.do("add", "foo")
        git.do("add", "bar")

        files = git.staged_files
        assert len(files) == 2
        assert files[0].name == "foo"
        assert files[0].operation == FileOperation.DELETED
        assert files[1].name == "bar"
        assert files[1].operation == FileOperation.ADDED


@pytest.fixture
def git(tempdir):
    subprocess.run(
        ["/usr/bin/git", "-C", tempdir, "init"],
        check=True,
    )

    g = Git(root=tempdir)

    g.do("config", "user.email", "me@example.com")
    g.do("config", "user.name", "Aaron Loo")

    yield g
