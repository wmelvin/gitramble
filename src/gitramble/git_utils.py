from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

APP_BRANCH_PREFIX = "gitramble-"


@dataclass
class GitLogItem:
    commit_hash: str
    abbrev_hash: str
    author_date: str
    subject_msg: str


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


def run_git_checkout_new_branch(
    run_path: Path, branch_name: str, commit_hash: str
) -> tuple[str, str]:
    """Create a new branch from a specific commit hash.

    Do not create the branch if the repository is not clean.

    Args:
        run_path (Path): Path to the Git repository.
        branch_name (str): Name of the new branch.
        commit_hash (str): Commit hash to create the branch from.

    Returns:
        tuple[str, str]: Output and error messages.
    """
    out, err = run_git_status(run_path)
    if out:
        return "", "The repository is not clean. Commit or stash changes first."
    if err:
        return "", err

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


def run_git_checkout_existing_branch(
    run_path: Path, branch_name: str
) -> tuple[str, str]:
    """Checkout an existing branch.

    Do not run checkout if the repository is not clean.

    Args:
        run_path (Path): Path to the Git repository.
        branch_name (str): Name of the branch to checkout.

    Returns:
        tuple[str, str]: Output and error messages.
    """
    out, err = run_git_status(run_path)
    if out:
        return "", "The repository is not clean. Commit or stash changes first."
    if err:
        return "", err

    result = run_git(run_path, ["checkout", branch_name])

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


def run_git_branch_list(run_path: Path) -> tuple[str, str]:
    """Run 'git branch --list' command.

    Args:
        run_path (Path): Path to the Git repository.

    Returns:
        tuple[str, str]: Output and error messages.
    """
    result = run_git(run_path, ["branch", "--list"])

    output = ""
    errors = ""

    if result is None:
        errors += "ERROR: Failed to run git command."
    elif result.returncode == 0:
        output = result.stdout
    else:
        errors += f"ERROR ({result.returncode})\n"
        if result.stderr is not None:
            errors += f"STDERR:\n{result.stderr}\n"
        if result.stdout is not None:
            errors += f"STDOUT:\n{result.stdout}\n"

    return output, errors


def get_branch_info(run_path: Path) -> tuple[list[str], str, str]:
    """Get a list of branches in the repository.

    Args:
        run_path (Path): Path to the Git repository.

    Returns:
        tuple[list[str], str, str]: List of branches, current branch,
        and error messages.
    """
    output, errors = run_git_branch_list(run_path)
    branches = output.splitlines()
    out_branches = []
    current_branch = ""
    for b in branches:
        if b.startswith("*"):
            current_branch = b[1:].strip()
            out_branches.append(current_branch)
        else:
            out_branches.append(b.strip())

    return out_branches, current_branch, errors


def delete_gitramble_branch(run_path: Path, branch_name: str) -> tuple[str, str]:
    if not branch_name.startswith(APP_BRANCH_PREFIX):
        return "", "Can only delete branches created by this application."

    result = run_git(run_path, ["branch", "-d", branch_name])

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
