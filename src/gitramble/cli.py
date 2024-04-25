from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich import print as rprint

from gitramble.app_data import AppData
from gitramble.git_utils import parse_git_log_output, run_git_log
from gitramble.ui import UI


def get_args(arglist=None):
    ap = argparse.ArgumentParser(description="Explore git commit history...")

    ap.add_argument(
        "dir_name",
        nargs="?",
        help="Name of directory containing the Git repository.",
    )

    ap.add_argument(
        "-u",
        "--repo-url",
        dest="repo_url",
        type=str,
        action="store",
        help="GitHub repository URL.",
    )

    return ap.parse_args(arglist)


def get_opts(arglist=None) -> tuple[Path, str]:
    args = get_args(arglist)

    if args.dir_name is None:
        dir_path = Path.cwd()
    else:
        dir_path = Path(args.dir_name).expanduser().resolve()

    if not dir_path.is_dir():
        sys.stderr.write(f"ERROR - Not a directory: '{dir_path}'\n")
        sys.exit(1)

    repo_url = args.repo_url if args.repo_url else ""

    return dir_path, repo_url


def cli(arglist=None):
    run_path, repo_url = get_opts(arglist)

    app_data = AppData(run_path, repo_url)
    rprint(f"Data directory: {app_data.data_dir}")

    rprint(f"Running [b]git log[/b] in directory '{run_path}'")

    git_log_output, git_log_errors = run_git_log(run_path)

    if git_log_errors:
        rprint(f"\n[yellow][b]ERRORS:[/b][/yellow]\n{git_log_errors}\n")
        sys.exit(1)

    commits = parse_git_log_output(git_log_output)

    ui = UI(app_data, commits)
    ui.run()


if __name__ == "__main__":
    cli()
