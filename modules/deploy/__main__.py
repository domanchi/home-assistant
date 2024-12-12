import argparse

from . import logger
from .main import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="deploy",
        description="Uploads and tests modified code to server, before merging.",
    )

    parser.add_argument(
        "-m",
        "--message",
        type=str,
        help="Commit message used to commit changes to git",
    )
    parser.add_argument(
        "-v",
        action="count",
        help="Increases verbosity of logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "If specified, will not make any persistent changes. "
            "This is useful for performing static tests of configuration."
        ),
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help=(
            "If specified, will not commit code after applying changes. "
            "This is useful for performing dynamic tests of configuration, before merging to master."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.v:
        logger.configure_verbosity(args.v)
    if not args.message:
        if not args.dry_run and not args.no_commit:
            raise argparse.ArgumentError(None, message="commit message must be specified")

    run(commit_msg=args.message, dry_run=args.dry_run, should_commit=(not args.no_commit))
