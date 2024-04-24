from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

APP_DATA_DIR = ".gitramble"


@dataclass
class CommitInfo:
    abbrev_hash: str
    selected: bool
    note: str


class AppData:
    def __init__(self, run_path: Path, repo_url: str) -> None:
        self.repo_url = repo_url
        self.data_dir = run_path / APP_DATA_DIR
        if not self.data_dir.exists():
            self.data_dir.mkdir()
            (self.data_dir / ".gitignore").write_text(
                "# Automatically created by gitramble.\n*\n"
            )
        self.settings_file = self.data_dir / "settings.csv"
        self.commits_file = self.data_dir / "commits.csv"
        self.commits: list[CommitInfo] = []
        self.load_settings()
        self.save_settings()

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
                reader = csv.reader(f)
                for row in reader:
                    self.commits.append(CommitInfo(*row))

    def save_commits(self) -> None:
        with self.commits_file.open("w") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            for commit in self.commits:
                writer.writerow([commit.abbrev_hash, commit.selected, commit.note])
