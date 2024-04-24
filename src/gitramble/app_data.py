from __future__ import annotations

from pathlib import Path

APP_DATA_DIR = ".gitramble"


class AppData:
    def __init__(self, run_path: Path, repo_url: str) -> None:
        self.repo_url = repo_url
        self.data_dir = run_path / APP_DATA_DIR
        if not self.data_dir.exists():
            self.data_dir.mkdir()
            (self.data_dir / ".gitignore").write_text(
                "# Automatically created by gitramble.\n*\n"
            )
