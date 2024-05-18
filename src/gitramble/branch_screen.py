from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView


class BranchScreen(ModalScreen[str]):
    def __init__(self, action: str, branch_list: list[str]) -> None:
        self.action = action
        self.branches = branch_list
        self.selected_branch = None
        super().__init__()

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "screenshot", "Screenshot", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="branch-dialog"):
            yield ListView(id="branch-list")
            with Horizontal(id="branch-buttons"):
                yield Button("Select", id="btn-select")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        lv = self.query_one(ListView)
        for branch in self.branches:
            lv.append(ListItem(Label(branch)))

    def on_list_view_highlighted(self, hl: ListView.Highlighted) -> None:
        ix = hl.list_view.index
        self.selected_branch = self.branches[ix]

    def action_screenshot(self) -> None:
        self.app.take_screenshot()

    def close_screen(self, branch: str) -> None:
        if branch:
            # If branch name has appended info it will be after a pipe symbol.
            # Use only the part before the pipe.
            if "|" in branch:
                branch = branch.split("|")[0].strip()
            self.dismiss(f"{self.action}:{branch}")
        else:
            self.dismiss("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-select":
            event.stop()
            self.close_screen(self.selected_branch)
        elif event.button.id == "btn-cancel":
            event.stop()
            self.close_screen("")

    def action_cancel(self) -> None:
        self.close_screen("")
