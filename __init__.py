import importlib
import sys
from collections import defaultdict
from functools import cached_property
from pathlib import Path

import sublime  # type: ignore
import sublime_plugin  # type: ignore

from . import lib
from .vendor import mistune

importlib.reload(lib)

_markdown = mistune.create_markdown(
    renderer=mistune.AstRenderer(),
    plugins=["footnotes", "table", "task_lists"],
)


class Settings:
    @cached_property
    def _settings(self):
        return sublime.load_settings("MarkdownPreview.sublime-settings")

    def get(self, key, default=None):
        return self._settings.get(key, default)


settings = Settings()


TEMPLATE = """
    <style type="text/css">
        .blockquote p {{
            padding-left: 0.5em;
            border-left: 0.25em solid gray;
        }}

        .task-list-item__checkbox {{
            width: 0.75em;
            height: 0.75em;
            display: inline-block;
            border: 1px solid white;
            line-height: 1;
        }}

        .task-list-item__checkbox--checked {{
            /* minihtml doesn't support <input/>, so we are hacking around it. */
            background-color: hsl(210, 70%, 50%);
        }}

        .footnote__ref {{
            display: inline;
            font-size: 0.75em;
            position: relative;
            top: -0.75em;
        }}

        .block-code {{
            background-color: #333;
            border-radius: 0.25em;
            padding: 0.25em;
            border: 1px solid black;
            display: inline-block
        }}

        .code-span {{
            background-color: #333;
            border-radius: 0.25em
        }}

        .thematic-break {{
            border-bottom: 1px solid black;
            width: 100px;
        }}
    </style>
    {content}
"""


def markdown(source):
    ast = _markdown(source)
    transformer = lib.Ast2HTML()

    return "\n".join(transformer.transform(**child) for child in ast)


class SheetProxy:
    def __init__(self):
        self._map = {}

    def associate(self, view, sheet):
        self._map[view] = sheet

    def disassociate(self, view):
        self._map.pop(view, None)

    def __get__(self, instance, owner=None):
        return self._map.get(instance.view)


sheet_proxy = SheetProxy()


class MarkdownPreviewCommand(sublime_plugin.TextCommand):
    sheet = sheet_proxy

    def run(self, edit):
        view = self.view
        if "markdown" not in view.syntax().scope:
            return

        if self.sheet:
            return
        content = markdown(self.view.substr(sublime.Region(0, self.view.size())))
        sheet = view.window().new_html_sheet(
            f"Preview",
            TEMPLATE.format(content=content),
        )
        view.window().select_sheets([view.sheet(), sheet])
        view.window().focus_view(view)
        sheet_proxy.associate(view, sheet)

    def is_enabled(self):
        return "markdown" in self.view.syntax().scope


class MarkdownViewUpdate(sublime_plugin.ViewEventListener):
    sheet = sheet_proxy

    def on_deactivated(self):
        if self.sheet:
            self.sheet.close()
        sheet_proxy.disassociate(self.view)

    # For some reason this isn't firing
    # def on_text_changed(self, changes):
    #     pass

    def update(self):
        if self.sheet is None:
            return
        self.sheet.set_contents(
            TEMPLATE.format(
                content=markdown(self.view.substr(sublime.Region(0, self.view.size())))
            )
        )

    @cached_property
    def debounced_update(self):
        # debouncing updates so the preview isn't fired on every keystroke
        return lib.debounce(lambda: settings.get("markdown-preview.debounce", 0.1))(
            self.update
        )

    # Not really happy with having to use the on_selection_modified event
    # since it also means we update on selection changes and not just
    # buffer changes, but on_text_changed isn't firing for me
    def on_selection_modified(self):
        sheet = self.sheet
        if sheet is None:
            return

        if settings.get("markdown-preview.debounce", None):
            self.debounced_update()
        else:
            self.update()
