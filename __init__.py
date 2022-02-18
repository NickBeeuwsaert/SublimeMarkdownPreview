import importlib
import sys
from collections import defaultdict
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

TEMPLATE = """
    <body>
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
    </body>
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
    counter = 0
    sheet = sheet_proxy

    def on_deactivated(self):
        if self.sheet:
            self.sheet.close()
        sheet_proxy.disassociate(self.view)

    # For some reason this isn't firing
    # def on_text_changed(self, changes):
    #     pass

    def on_selection_modified(self):
        sheet = self.sheet
        if sheet is None:
            return

        sheet.set_contents(
            TEMPLATE.format(
                content=markdown(self.view.substr(sublime.Region(0, self.view.size())))
            )
        )
