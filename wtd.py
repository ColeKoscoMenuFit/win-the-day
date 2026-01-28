#!/usr/bin/env python3
"""Win The Day - Terminal Signal vs Noise Planner"""

import json
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Static, ListView, ListItem, Input, Label
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on

DATA_FILE = Path.home() / ".wintheday.json"

SECTIONS = [
    ("today_signals", "Today Signals", "signal"),
    ("busy_work", "Busy Work", "noise"),
    ("reminders", "Reminders", "neutral"),
    ("tomorrow_signals", "Tomorrow Signals", "signal"),
]

FOCUS_AREAS = ["Business", "Marketing"]


def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {key: [] for key, _, _ in SECTIONS}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))


def calc_signal_percent(data):
    signal_done = signal_total = noise_done = noise_total = 0
    for key, _, typ in SECTIONS:
        for task in data.get(key, []):
            if typ == "signal":
                signal_total += 1
                if task["done"]:
                    signal_done += 1
            elif typ == "noise":
                noise_total += 1
                if task["done"]:
                    noise_done += 1
    if signal_total + noise_total == 0:
        return 0
    signal_pct = (signal_done / signal_total * 100) if signal_total else 0
    noise_pct = ((1 - noise_done / noise_total) * 100) if noise_total else 100
    return round((signal_pct + noise_pct) / 2)


class TaskItem(ListItem):
    def __init__(self, text: str, done: bool, section: str, index: int):
        super().__init__()
        self.task_text = text
        self.done = done
        self.section = section
        self.index = index

    def compose(self) -> ComposeResult:
        check = "[x]" if self.done else "[ ]"
        style = "dim" if self.done else ""
        yield Label(f"{check} {self.task_text}", classes=style)


class SectionHeader(Static):
    def __init__(self, title: str, typ: str):
        badge = {"signal": "[green]SIGNAL[/]", "noise": "[yellow]NOISE[/]", "neutral": "[dim]NEUTRAL[/]"}
        super().__init__(f"[bold]{title}[/] {badge.get(typ, '')}")


class WinTheDay(App):
    CSS = """
    Screen { background: $surface; }
    #header { height: 5; content-align: center middle; background: $primary; color: $text; }
    #percent { text-style: bold; }
    .section-box { margin: 1 2; padding: 0 1; border: round $primary; }
    ListView { height: auto; max-height: 8; }
    ListView:focus { border: solid $accent; }
    ListItem { padding: 0 1; }
    ListItem.--highlight { background: $accent 30%; }
    Input { margin: 0 1 1 1; }
    #focus { margin: 1 2; padding: 1; }
    #help { dock: bottom; height: 1; background: $primary-darken-2; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_task", "Add"),
        Binding("d", "delete_task", "Delete"),
        Binding("space", "toggle_task", "Toggle", show=False),
        Binding("enter", "toggle_task", "Toggle"),
        Binding("tab", "focus_next", "Next Section", show=False),
        Binding("shift+tab", "focus_previous", "Prev Section", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.data = load_data()
        self.adding_to = None

    def compose(self) -> ComposeResult:
        pct = calc_signal_percent(self.data)
        yield Static(f"[bold]Win The Day[/]\n[bold]{pct}%[/] Signal vs Noise", id="header")

        for key, title, typ in SECTIONS:
            with Vertical(classes="section-box"):
                yield SectionHeader(title, typ)
                yield ListView(*self._make_items(key), id=f"list_{key}")

        yield Static(f"[bold]My Focus:[/] {', '.join(FOCUS_AREAS)}", id="focus")
        yield Static(" [q]Quit  [a]Add  [d]Delete  [Enter]Toggle  [Tab]Next Section ", id="help")

    def _make_items(self, section: str) -> list:
        return [
            TaskItem(t["text"], t["done"], section, i)
            for i, t in enumerate(self.data.get(section, []))
        ]

    def _refresh_list(self, section: str):
        lv = self.query_one(f"#list_{section}", ListView)
        lv.clear()
        for item in self._make_items(section):
            lv.append(item)

    def _refresh_header(self):
        pct = calc_signal_percent(self.data)
        self.query_one("#header", Static).update(f"[bold]Win The Day[/]\n[bold]{pct}%[/] Signal vs Noise")

    def action_toggle_task(self):
        focused = self.focused
        if isinstance(focused, ListView):
            item = focused.highlighted_child
            if isinstance(item, TaskItem):
                self.data[item.section][item.index]["done"] = not item.done
                save_data(self.data)
                self._refresh_list(item.section)
                self._refresh_header()

    def action_add_task(self):
        focused = self.focused
        if isinstance(focused, ListView):
            section = focused.id.replace("list_", "")
            self.adding_to = section
            inp = Input(placeholder="New task...", id="new_task_input")
            focused.parent.mount(inp)
            inp.focus()

    @on(Input.Submitted, "#new_task_input")
    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if text and self.adding_to:
            if self.adding_to not in self.data:
                self.data[self.adding_to] = []
            self.data[self.adding_to].append({"text": text, "done": False})
            save_data(self.data)
            self._refresh_list(self.adding_to)
            self._refresh_header()
        event.input.remove()
        self.query_one(f"#list_{self.adding_to}", ListView).focus()
        self.adding_to = None

    def action_delete_task(self):
        focused = self.focused
        if isinstance(focused, ListView):
            item = focused.highlighted_child
            if isinstance(item, TaskItem):
                del self.data[item.section][item.index]
                save_data(self.data)
                self._refresh_list(item.section)
                self._refresh_header()


if __name__ == "__main__":
    WinTheDay().run()
