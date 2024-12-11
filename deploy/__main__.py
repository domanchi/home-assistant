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
        help="If specified, will not make any persistent changes",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.v:
        logger.configure_verbosity(args.v)
    if not args.dry_run and not args.message:
        raise argparse.ArgumentError(None, message="commit message must be specified")

    run(commit_msg=args.message, dry_run=args.dry_run)
