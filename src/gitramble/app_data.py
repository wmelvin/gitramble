from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gitramble.git_utils import GitLogItem

APP_DATA_DIR = ".gitramble"


@dataclass
class CommitInfo:
    abbrev_hash: str = ""
    author_date: str = ""
    subject_msg: str = ""
    current: int = 0
    selected: int = 0
    note: str = ""

    def when_str(self) -> datetime:
        return datetime.fromisoformat(self.author_date).strftime("%Y-%m-%d %H:%M")


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
            with self.settings_file.open() as f:
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
            with self.commits_file.open() as f:
                reader = csv.DictReader(f)
                for row in reader:
                    commit = CommitInfo()
                    commit.abbrev_hash = row["abbrev_hash"]  # Required field.
                    commit.author_date = row.get("author_date", "")
                    commit.subject_msg = row.get("subject_msg", "")
                    commit.current = int(row.get("current", 0))
                    commit.selected = int(row.get("selected", 0))
                    commit.note = row.get("note", "")
                    self.commits_data[commit.abbrev_hash] = commit

    def save_commits(self) -> None:
        with self.commits_file.open("w") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "abbrev_hash",
                    "author_date",
                    "subject_msg",
                    "current",
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
                        "selected": commit.selected,
                        "note": commit.note,
                    }
                )

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
        for log_item in log_items:
            if log_item.abbrev_hash in self.commits_data:
                commit = self.commits_data[log_item.abbrev_hash]
                commit.subject_msg = log_item.subject_msg
                commit.current = 1
            else:
                self.commits_data[log_item.abbrev_hash] = CommitInfo(
                    abbrev_hash=log_item.abbrev_hash,
                    author_date=log_item.author_date,
                    subject_msg=log_item.subject_msg,
                    current=1,
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
