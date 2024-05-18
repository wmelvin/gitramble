from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gitramble.git_utils import APP_BRANCH_PREFIX, GitLogItem

APP_DATA_DIR = ".gitramble"


@dataclass
class CommitInfo:
    abbrev_hash: str = ""
    author_date: str = ""
    subject_msg: str = ""
    current: int = 0
    sequence: int = 0
    selected: int = 0
    note: str = ""

    def when_str(self) -> datetime:
        return datetime.fromisoformat(self.author_date).strftime("%Y-%m-%d %H:%M")

    def get_branch_name(self) -> str:
        return f"{APP_BRANCH_PREFIX}-{self.sequence:04d}-{self.abbrev_hash[:4]}"


class AppData:
    def __init__(self, run_path: Path, repo_url: str) -> None:
        self.repo_url = repo_url
        self.run_path = run_path
        self.data_dir = run_path / APP_DATA_DIR
        if not self.data_dir.exists():
            self.data_dir.mkdir()
            (self.data_dir / ".gitignore").write_text(
                "# Automatically created by gitramble.\n*\n"
            )
        self.log_file = self.data_dir / "gitramble.log"
        self._init_logging()
        self.settings_file = self.data_dir / "settings.csv"
        self.commits_file = self.data_dir / "commits.csv"
        self.commits_data: dict[str, CommitInfo] = {}
        self._commits_changed: bool = False
        self.load_settings()
        self.save_settings()

    def _init_logging(self) -> None:
        """Set up logging to a file.

        This function will add a handler to the root logger.
        """
        if not self.log_file:
            return
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(str(self.log_file), encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    def load_settings(self) -> None:
        # TODO: This will need to work differently if more settings are added.
        if self.repo_url:
            # If we already have a repo URL, don't overwrite it.
            return
        if self.settings_file.exists():
            with self.settings_file.open(newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[0] == "repo_url":
                        self.repo_url = row[1]
                        break

    def save_settings(self) -> None:
        # TODO: This will need to work differently if more settings are added.
        if self.repo_url:
            self.settings_file.write_text(f'"repo_url","{self.repo_url}"\n')

    def load_commits(self) -> None:
        if self.commits_file.exists():
            with self.commits_file.open(newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    commit = CommitInfo()
                    commit.abbrev_hash = row["abbrev_hash"]  # Required field.
                    commit.author_date = row.get("author_date", "")
                    commit.subject_msg = row.get("subject_msg", "")
                    commit.current = int(row.get("current", 0))
                    commit.sequence = int(row.get("sequence", 0))
                    commit.selected = int(row.get("selected", 0))
                    commit.note = row.get("note", "")
                    self.commits_data[commit.abbrev_hash] = commit

    def save_commits(self) -> None:
        with self.commits_file.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "abbrev_hash",
                    "author_date",
                    "subject_msg",
                    "current",
                    "sequence",
                    "selected",
                    "note",
                ],
                quoting=csv.QUOTE_NONNUMERIC,
            )
            writer.writeheader()
            for commit in self.commits_data.values():
                writer.writerow(
                    {
                        "abbrev_hash": commit.abbrev_hash,
                        "author_date": commit.author_date,
                        "subject_msg": commit.subject_msg,
                        "current": commit.current,
                        "sequence": commit.sequence,
                        "selected": commit.selected,
                        "note": commit.note,
                    }
                )
        self._commits_changed = False

    def update_commits(self, log_items: list[GitLogItem]) -> None:
        """Update the commits dictionary from the current git log data.

        Args:
            log_items (list[GitLogItem]): List of GitLogItem objects with the latest
            commit.

        """

        # Load existing commits_data.
        self.load_commits()

        # Clear the current flag for all commits.
        for commit in self.commits_data.values():
            commit.current = 0

        # Update commits_data from the latest log data.
        for seq, log_item in enumerate(log_items, start=1):
            if log_item.abbrev_hash in self.commits_data:
                commit = self.commits_data[log_item.abbrev_hash]
                commit.subject_msg = log_item.subject_msg
                commit.current = 1
                if not commit.sequence:
                    commit.sequence = seq
            else:
                self.commits_data[log_item.abbrev_hash] = CommitInfo(
                    abbrev_hash=log_item.abbrev_hash,
                    author_date=log_item.author_date,
                    subject_msg=log_item.subject_msg,
                    current=1,
                    sequence=seq,
                    selected=0,
                )

        # Save the updated commits_data.
        self.save_commits()

    def get_commits_current(self) -> list[CommitInfo]:
        """Return a list of CommitInfo where current is set."""
        return [commit for commit in self.commits_data.values() if commit.current]

    def set_selected(self, commit_hash: str, selected: int) -> None:
        """Set the selected flag for a commit.

        Args:
            commit_hash (str): The abbreviated hash of the commit.
            selected (int): The value to set the selected flag to.

        """
        if commit_hash not in self.commits_data:
            return
        self.commits_data[commit_hash].selected = selected
        self.save_commits()

    def set_note(self, commit_hash: str, note: str) -> None:
        if commit_hash not in self.commits_data:
            return
        self.commits_data[commit_hash].note = note
        # This may be called for each change to the Input widget
        # (each character), so do not save to file here.
        self._commits_changed = True

    def save_pending_changes(self) -> None:
        if self._commits_changed:
            self.save_commits()

    def _commit_matching_branch_name(self, branch_name: str) -> CommitInfo | None:
        """Return the commit that matches the branch name.

        Args:
            branch_name (str): The branch name to match.

            Returns:
            CommitInfo | None: The CommitInfo object that matches the branch name,
            or None if no match is found.
        """
        for commit in self.commits_data.values():
            if branch_name == commit.get_branch_name():
                return commit
        return None

    def add_info_to_branch_names(self, branch_list: list[str]) -> list[str]:
        """Add commit information to each branch name in the list.

        Args:
            branch_list (list[str]): A list of branch names.

        Returns:
            list[str]: A list of branch names with commit information appended.
        """
        updated_list = []
        for bn in branch_list:
            upd_bn = bn
            cm = self._commit_matching_branch_name(bn)
            if cm:
                upd_bn += f" | {cm.note or cm.subject_msg}"
            updated_list.append(upd_bn)
        return updated_list
