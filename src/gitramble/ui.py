from __future__ import annotations

import logging
import webbrowser

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Checkbox, Footer, Header, Label, Static

from gitramble.app_data import AppData, CommitInfo
from gitramble.git_utils import run_git_checkout_branch

BRANCH_PREFIX = "gitramble-"


class Commit(Static):
    def __init__(self, commit_info: CommitInfo) -> None:
        super().__init__()
        self.commit_info = commit_info
        self.id = f"c-{commit_info.abbrev_hash}"

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            with Horizontal(id="panel-select"):
                yield Checkbox()
                yield Label(self.commit_info.when_str(), id="date")
            with Horizontal(id="panel-buttons"):
                yield Button(self.commit_info.abbrev_hash, id="btn-browser")
                yield Button("Checkout", id="btn-checkout")
        yield Static(self.commit_info.subject_msg, id="descr")

    def on_mount(self) -> None:
        if not self.app.app_data.repo_url:
            self.query_one("#btn-browser").disabled = True
        if self.commit_info.selected:
            self.add_class("selected")
            self.query_one(Checkbox).value = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-browser":
            self.open_at_url()
        elif event.button.id == "btn-checkout":
            self.checkout()

    @on(Checkbox.Changed)
    def update_selected(self) -> None:
        if self.query_one(Checkbox).value:
            self.add_class("selected")
            self.app.app_data.set_selected(self.commit_info.abbrev_hash, 1)
        else:
            self.remove_class("selected")
            self.app.app_data.set_selected(self.commit_info.abbrev_hash, 0)

    def open_at_url(self) -> None:
        url = self.app.app_data.repo_url
        if not url:
            return
        url = f"{url}/commit/{self.commit_info.abbrev_hash}"
        try:
            webbrowser.open(url)
        except Exception:
            self.query_one("#btn-browser").disabled = True

    def checkout(self) -> None:
        branch_name = f"{BRANCH_PREFIX}{self.commit_info.abbrev_hash}"
        logging.info(f"Checking out {branch_name}")
        output, errors = run_git_checkout_branch(
            self.app.app_data.run_path, branch_name, self.commit_info.abbrev_hash
        )
        logging.info(output)
        if errors:
            errors = f"Checkout failed for {self.commit_info.abbrev_hash}:\n{errors}"
            logging.error(errors)


class UI(App):
    def __init__(self, app_data: AppData) -> None:
        self.app_data = app_data
        self.selected_only = False
        super().__init__()

    CSS_PATH = "ui.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Dark on/off"),
        ("f", "filter_selected", "Filter on/off"),
        ("x", "exit_app", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(id="commits")
        yield Footer()

    def on_mount(self) -> None:
        for commit in self.app_data.get_commits_current():
            new_commit = Commit(commit_info=commit)
            self.query_one("#commits").mount(new_commit)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_filter_selected(self) -> None:
        self.selected_only = not self.selected_only
        commits = self.query(Commit)
        for commit in commits:
            if self.selected_only and not commit.has_class("selected"):
                commit.add_class("hidden")
            else:
                commit.remove_class("hidden")

    def action_exit_app(self) -> None:
        self.exit()
