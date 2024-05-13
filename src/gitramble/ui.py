from __future__ import annotations

import logging
import webbrowser
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Footer,
    Header,
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
    run_git_branch_list,
    run_git_checkout_existing_branch,
    run_git_checkout_new_branch,
)


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
        # This assumes a GitHub URL scheme.
        # TODO: Add options for other providers?
        url = f"{url}/commit/{self.commit_info.abbrev_hash}"
        try:
            webbrowser.open(url)
        except Exception:
            self.query_one("#btn-browser").disabled = True

    def checkout(self) -> None:
        branch_name = f"{APP_BRANCH_PREFIX}{self.commit_info.abbrev_hash}"
        ls_out, ls_err = run_git_branch_list(self.app.app_data.run_path)
        if ls_err:
            logging.error(ls_err)
            self.app.say(f"ERROR:\n{ls_err}")
            return
        if branch_name in ls_out:
            self.app.say(f"Branch {branch_name} already exists.")
            return
        self.app.say(f"Checking out {branch_name}")
        co_out, co_err = run_git_checkout_new_branch(
            self.app.app_data.run_path, branch_name, self.commit_info.abbrev_hash
        )
        self.app.say(co_out)
        if co_err:
            co_err = f"Checkout failed for {self.commit_info.abbrev_hash}:\n{co_err}"
            self.app.say(f"ERROR:\n{co_err}")
        self.app.show_current_branch()


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
        # ("t", "try_stuff", "Try"),
        ("u", "toggle_dark", "UI mode"),
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
        self.show_current_branch()

    def say(
        self, message: str, pre: str = "", no_dt: bool = False, pop: bool = False
    ) -> None:
        logging.info("UI: %s", message)
        dt = "" if no_dt else f"{datetime.now().strftime('%H:%M:%S')} - "
        self.query_one(RichLog).write(f"{dt}{pre}{message}\n")
        if pop:
            self.query_one("#log-area").collapsed = False

    def action_show_branches(self) -> None:
        out, err = run_git_branch_list(self.app_data.run_path)
        self.say("Branches:", pop=True)
        self.say(f"\n{out}", pre="[bold]", no_dt=True)
        if err:
            self.say(f"ERRORS:\n{err}", pre="[bold red]")

    def action_change_branch(self) -> None:
        self.open_branch_screen("change")

    def action_delete_branch(self) -> None:
        self.open_branch_screen("delete")

    def open_branch_screen(self, action: str) -> None:
        lst, _, err = get_branch_info(self.app_data.run_path)
        if err:
            self.say(f"ERRORS:\n{err}", pre="[bold red]", pop=True)
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
        self.say(f"Branch selected: {branch_name}")
        if action == "change":
            self.checkout_branch(branch_name)
        elif action == "delete":
            self.delete_branch(branch_name)

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

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

    # def action_try_stuff(self) -> None:
    #     self.say("blah " * 50)

    def action_exit_app(self) -> None:
        self.exit()

    def show_current_branch(self) -> None:
        _, cur, err = get_branch_info(self.app_data.run_path)
        if err:
            self.say(f"ERRORS:\n{err}", pre="[bold red]", pop=True)
            return
        self.title = f"gitramble (branch: {cur})"

    def checkout_branch(self, branch_name: str) -> None:
        _, cur, err = get_branch_info(self.app_data.run_path)
        if err:
            self.say(f"ERRORS:\n{err}", pre="[bold red]", pop=True)
            return
        if branch_name == cur:
            self.say("Already on that branch.", pop=True)
            return
        out, err = run_git_checkout_existing_branch(self.app_data.run_path, branch_name)
        self.say(f"\n{out}", pop=True)
        if err:
            self.say(f"ERRORS:\n{err}", pre="[bold red]")

    def delete_branch(self, branch_name: str) -> None:
        _, cur, err = get_branch_info(self.app_data.run_path)
        if err:
            self.say(f"ERRORS:\n{err}", pre="[bold red]", pop=True)
            return
        if branch_name == cur:
            self.say("Cannot delete the current branch.", pop=True)
            return
        out, err = delete_gitramble_branch(self.app_data.run_path, branch_name)
        self.say(f"\n{out}", pop=True)
        if err:
            self.say(f"ERRORS:\n{err}", pre="[bold red]")
