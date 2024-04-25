from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class GitLogItem:
    commit_hash: str
    abbrev_hash: str
    author_date: str
    subject_msg: str

    def when_str(self) -> datetime:
        return datetime.fromisoformat(self.author_date).strftime("%Y-%m-%d %H:%M")


def parse_git_log_output(stdout: str) -> list[GitLogItem]:
    log_fields = []
    for line in stdout.splitlines():
        fields = line.strip('"').split(" ", 3)
        if len(fields) == 4:  # noqa: PLR2004
            log_fields.append(
                GitLogItem(
                    commit_hash=fields[0],
                    abbrev_hash=fields[1],
                    author_date=fields[2],
                    subject_msg=fields[3],
                )
            )

    return log_fields


def run_git(run_path: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run a 'git' command.

    Args:
        run_path (Path): Path to the Git repository.
        args (list[str]): List of command-line arguments.

    Returns:
        subprocess.CompletedProcess: Result of the command.
    """
    git_exe = shutil.which("git")

    if git_exe is None:
        sys.stderr.write(
            "ERROR - Cannot find 'git' command. Make sure Git is installed.\n"
        )
        sys.exit(1)

    cmds = [git_exe, *args]

    return subprocess.run(
        cmds,  # noqa: S603
        cwd=str(run_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def run_git_log(run_path: Path) -> tuple[str, str]:
    """Run 'git log' command to get commit history.

    Args:
        run_path (Path): Path to the Git repository.

    Returns:
        tuple[str, str]: Output and error messages.
    """
    result = run_git(
        run_path,
        [
            "log",
            "--topo-order",
            "--reverse",
            "--date=iso-strict",
            '--pretty=format:"%H %h %ad %s"',
        ],
    )

    #  --pretty=format:
    #  %H  = Commit hash
    #  %h  = Abbreviated commit hash
    #  %ad = Author date
    #  %s  = Subject (commit message)

    output = ""
    errors = ""

    if result is None:
        errors += "ERROR: Failed to run git command."
    elif result.returncode == 0:
        output = result.stdout.strip()
    else:
        errors += f"ERROR ({result.returncode})\n"
        if result.stderr is not None:
            errors += f"STDERR:\n{result.stderr}\n"
        if result.stdout is not None:
            errors += f"STDOUT:\n{result.stdout}\n"

    return output, errors


def run_git_checkout_branch(
    run_path: Path, branch_name: str, commit_hash: str
) -> tuple[str, str]:
    """Create a new branch from a specific commit hash.

    Args:
        run_path (Path): Path to the Git repository.
        branch_name (str): Name of the new branch.
        commit_hash (str): Commit hash to create the branch from.

    Returns:
        tuple[str, str]: Output and error messages.
    """
    result = run_git(
        run_path,
        ["checkout", "-b", branch_name, commit_hash],
    )

    if result is None:
        return "", "ERROR: Failed to run git command."
    if result.returncode == 0:
        return result.stdout.strip(), ""

    errors = f"ERROR ({result.returncode})\n"
    if result.stderr is not None:
        errors += f"STDERR:\n{result.stderr}\n"
    if result.stdout is not None:
        errors += f"STDOUT:\n{result.stdout}\n"

    return "", errors


def run_git_status(run_path: Path) -> tuple[str, str]:
    """Run 'git status' command.

    Args:
        run_path (Path): Path to the Git repository.

    Returns:
        tuple[str, str]: Output and error messages.
    """
    result = run_git(run_path, ["status", "--porcelain"])

    output = ""
    errors = ""

    if result is None:
        errors += "ERROR: Failed to run git command."
    elif result.returncode == 0:
        output = result.stdout.strip()
    else:
        errors += f"ERROR ({result.returncode})\n"
        if result.stderr is not None:
            errors += f"STDERR:\n{result.stderr}\n"
        if result.stdout is not None:
            errors += f"STDOUT:\n{result.stdout}\n"

    return output, errors


def git_status_clean(run_path: Path) -> bool:
    """Check if the Git repository is clean.

    Args:
        run_path (Path): Path to the Git repository.

    Returns:
        bool: True if the repository is clean and there were no errors.
    """
    output, errors = run_git_status(run_path)
    return not output and not errors
