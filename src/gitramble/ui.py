from __future__ import annotations

import logging
import webbrowser

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Checkbox, Footer, Header, Label, Static

from gitramble.app_data import AppData
from gitramble.git_utils import GitLogItem, run_git_checkout_branch

BRANCH_PREFIX = "gitramble-"


class Commit(Static):
    def __init__(self, log_item: GitLogItem) -> None:
        super().__init__()
        self.log_item = log_item
        self.id = f"c-{log_item.abbrev_hash}"

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            with Horizontal(id="panel-select"):
                yield Checkbox()
                yield Label(self.log_item.when_str(), id="date")
            with Horizontal(id="panel-buttons"):
                yield Button(self.log_item.abbrev_hash, id="btn-browser")
                yield Button("Checkout", id="btn-checkout")
        yield Static(self.log_item.subject_msg, id="descr")

    def on_mount(self) -> None:
        if not self.app.app_data.repo_url:
            self.query_one("#btn-browser").disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-browser":
            self.open_at_url()
        elif event.button.id == "btn-checkout":
            self.checkout()

    @on(Checkbox.Changed)
    def update_selected(self) -> None:
        if self.query_one(Checkbox).value:
            self.add_class("selected")
        else:
            self.remove_class("selected")

    def open_at_url(self) -> None:
        url = self.app.app_data.repo_url
        if not url:
            return
        url = f"{url}/commit/{self.log_item.abbrev_hash}"
        try:
            webbrowser.open(url)
        except Exception:
            self.query_one("#btn-browser").disabled = True

    def checkout(self) -> None:
        branch_name = f"{BRANCH_PREFIX}{self.log_item.abbrev_hash}"
        logging.info(f"Checking out {branch_name}")
        output, errors = run_git_checkout_branch(
            self.app.app_data.run_path, branch_name, self.log_item.abbrev_hash
        )
        logging.info(output)
        if errors:
            errors = f"Checkout failed for {self.log_item.abbrev_hash}:\n{errors}"
            logging.error(errors)


class UI(App):
    def __init__(self, app_data: AppData, git_log: list[GitLogItem]) -> None:
        self.app_data = app_data
        self.git_log = git_log
        super().__init__()

    CSS_PATH = "ui.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Dark on/off"),
        ("x", "exit_app", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(id="commits")
        yield Footer()

    def on_mount(self) -> None:
        for commit in self.git_log:
            new_commit = Commit(log_item=commit)
            self.query_one("#commits").mount(new_commit)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_exit_app(self) -> None:
        self.exit()
