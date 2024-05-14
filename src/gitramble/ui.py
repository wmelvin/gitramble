from __future__ import annotations

import logging
import webbrowser
from datetime import datetime

from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
)

from gitramble.app_data import AppData, CommitInfo
from gitramble.branch_screen import BranchScreen
from gitramble.git_utils import (
    APP_BRANCH_PREFIX,
    delete_gitramble_branch,
    get_branch_info,
    parse_git_log_output,
    run_git_branch_list,
    run_git_checkout_existing_branch,
    run_git_checkout_new_branch,
    run_git_log,
)


class Commit(Static):
    def __init__(self, commit_info: CommitInfo) -> None:
        super().__init__()
        self.commit_info = commit_info
        self.id = f"c-{commit_info.abbrev_hash}"

    def compose(self) -> ComposeResult:
        with Horizontal(id="panel-commit"):
            with Vertical(id="panel"):
                with Horizontal(id="panel-select"):
                    yield Checkbox()
                    yield Label(self.commit_info.when_str(), id="date")
                with Horizontal(id="panel-buttons"):
                    yield Button("...", id="btn-note")
                    yield Button(self.commit_info.abbrev_hash, id="btn-browser")
                    yield Button("Checkout", id="btn-checkout")
            yield Static(self.commit_info.subject_msg, id="descr")
        with Horizontal(id="panel-note"):
            yield Label("Note:")
            yield Input(self.commit_info.note, max_length=60, id="input-note")

    def on_mount(self) -> None:
        if not self.app.app_data.repo_url:
            self.query_one("#btn-browser").disabled = True
        if self.commit_info.selected:
            self.add_class("selected")
            self.query_one(Checkbox).value = True
        if self.commit_info.note:
            self.add_class("noted")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-browser":
            self.open_at_url()
        elif event.button.id == "btn-checkout":
            self.checkout()
        elif event.button.id == "btn-note":
            if self.has_class("noted"):
                if not self.commit_info.note:
                    self.remove_class("noted")
            else:
                self.add_class("noted")
                self.query_one("#input-note").focus()

    @on(Checkbox.Changed)
    def update_selected(self) -> None:
        if self.query_one(Checkbox).value:
            self.add_class("selected")
            self.app.app_data.set_selected(self.commit_info.abbrev_hash, 1)
        else:
            self.remove_class("selected")
            self.app.app_data.set_selected(self.commit_info.abbrev_hash, 0)

    @on(Input.Changed)
    def update_note_change(self, event: Input.Changed) -> None:
        self.app.app_data.set_note(self.commit_info.abbrev_hash, event.value)

    def open_at_url(self) -> None:
        url = self.app.app_data.repo_url
        if not url:
            return
        # This assumes a GitHub URL scheme.
        # TODO: Add options for other providers?
        url = f"{url}/commit/{self.commit_info.abbrev_hash}"
        try:
            webbrowser.open(url)
        except Exception:
            self.query_one("#btn-browser").disabled = True

    def checkout(self) -> None:
        self.app.checkout_new_branch(self.commit_info.abbrev_hash)


class UI(App):
    def __init__(self, app_data: AppData) -> None:
        self.app_data = app_data
        self.selected_only = False
        super().__init__()

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("b", "show_branches", "Branches"),
        ("c", "change_branch", "Change"),
        ("d", "delete_branch", "Delete"),
        ("f", "filter_selected", "Filter"),
        ("l", "toggle_log", "Log"),
        # ("u", "toggle_dark", "Mode"),
        ("x", "exit_app", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(id="commits")
        with Collapsible(title="Log", id="log-area"):
            yield RichLog(
                wrap=True, highlight=True, markup=True, auto_scroll=True, id="log"
            )
        yield Footer()

    def on_mount(self) -> None:
        for commit in self.app_data.get_commits_current():
            new_commit = Commit(commit_info=commit)
            self.query_one("#commits").mount(new_commit)
        self.say(f"Repository: {self.app_data.run_path}")
        self.title = "gitramble"
        self.show_current_branch()

    @on(events.DescendantBlur)
    def on_descendent_blur(self, event: events.DescendantBlur) -> None:
        if event.widget.id == "input-note":
            # Save any pending changes on leaving the Input widget.
            self.app_data.save_pending_changes()

    def say(self, message: str, pop: bool = False) -> None:
        if not message.strip():
            return
        logging.info("UI: %s", message)
        dt = f"{datetime.now().strftime('%H:%M:%S')} - "
        self.query_one(RichLog).write(f"{dt}{message}")
        if pop:
            self.query_one("#log-area").collapsed = False

    def show_error(self, error_msg: str | None) -> bool:
        """Show an error message in the log area. Return True if there was an error.

        Args:
            error_msg (str): Error message to display.

        Returns:
            bool: True if there was an error.
        """
        if not error_msg:
            return False
        logging.error(error_msg)
        dt = f"{datetime.now().strftime('%H:%M:%S')} - "
        self.query_one(RichLog).write(f"{dt}[bold red]ERRORS:\n{error_msg}")
        self.query_one("#log-area").collapsed = False
        return True

    def action_show_branches(self) -> None:
        out, err = run_git_branch_list(self.app_data.run_path)
        self.say(f"Branches:\n{out}", pop=True)
        self.show_error(err)

    def action_change_branch(self) -> None:
        self.open_branch_screen("change")

    def action_delete_branch(self) -> None:
        self.open_branch_screen("delete")

    def open_branch_screen(self, action: str) -> None:
        lst, _, err = get_branch_info(self.app_data.run_path)
        if self.show_error(err):
            return
        if not lst:
            self.say("No branches available.", pop=True)
            return
        self.push_screen(BranchScreen(action, lst), self.branch_screen_closed)

    def branch_screen_closed(self, action_branch: str) -> None:
        if not action_branch:
            self.say("Branch selection cancelled.", pop=True)
            return
        action, branch_name = action_branch.split(":")
        if action == "change":
            self.checkout_existing_branch(branch_name)
        elif action == "delete":
            self.delete_branch(branch_name)

    # def action_toggle_dark(self) -> None:
    #     self.dark = not self.dark

    def action_filter_selected(self) -> None:
        self.selected_only = not self.selected_only
        commits = self.query(Commit)
        for commit in commits:
            if self.selected_only and not commit.has_class("selected"):
                commit.add_class("hidden")
            else:
                commit.remove_class("hidden")

    def action_toggle_log(self) -> None:
        log_area: Collapsible = self.query_one("#log-area")
        log_area.collapsed = not log_area.collapsed

    def action_exit_app(self) -> None:
        self.exit()

    def show_current_branch(self) -> None:
        _, cur, err = get_branch_info(self.app_data.run_path)
        if self.show_error(err):
            return
        self.sub_title = f"branch: {cur}"

    def refresh_commits(self) -> None:
        self.say("Refreshing list of commits from git log.", pop=True)
        log_output, err = run_git_log(self.app_data.run_path)
        if self.show_error(err):
            return

        # Remove existing Commit widgets.
        commits_list = self.query_one("#commits")
        commits_list.remove_children(Commit)

        # Parse the log output and update app_data.
        log_items = parse_git_log_output(log_output)
        self.app_data.update_commits(log_items)

        # Add the updated set of Commit widgets to the UI.
        for commit in self.app_data.get_commits_current():
            new_commit = Commit(commit_info=commit)
            commits_list.mount(new_commit)

    def checkout_new_branch(self, abbrev_hash: str) -> None:
        branch_name = f"{APP_BRANCH_PREFIX}{abbrev_hash}"
        ls_out, ls_err = run_git_branch_list(self.app_data.run_path)
        if self.show_error(ls_err):
            return
        if branch_name in ls_out:
            self.say(f"Branch {branch_name} already exists.")
            return
        self.say(f"Checking out {branch_name}")
        co_out, co_err = run_git_checkout_new_branch(
            self.app_data.run_path, branch_name, abbrev_hash
        )
        self.say(co_out)
        self.show_error(co_err)

        self.show_current_branch()
        self.refresh_commits()

    def checkout_existing_branch(self, branch_name: str) -> None:
        self.say(f"Checkout {branch_name}")
        _, cur, err = get_branch_info(self.app_data.run_path)
        if self.show_error(err):
            return
        if branch_name == cur:
            self.say("Already on that branch.", pop=True)
            return
        out, err = run_git_checkout_existing_branch(self.app_data.run_path, branch_name)
        self.say(f"{out}", pop=True)
        self.show_error(err)
        self.refresh_commits()

    def delete_branch(self, branch_name: str) -> None:
        self.say(f"Delete {branch_name}")
        _, cur, err = get_branch_info(self.app_data.run_path)
        if self.show_error(err):
            return
        if branch_name == cur:
            self.say("Cannot delete the current branch.", pop=True)
            return
        out, err = delete_gitramble_branch(self.app_data.run_path, branch_name)
        self.say(f"\n{out}", pop=True)
        self.show_error(err)
