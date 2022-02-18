import importlib
import sys
from collections import defaultdict
from pathlib import Path

import sublime
import sublime_plugin

here = str(Path(__file__).parent)
if here not in sys.path:
    sys.path.append(here)

mistune = importlib.import_module("mistune")
sublime_task_lists = importlib.import_module("sublime_task_lists")
renderer = importlib.import_module("renderer")
importlib.reload(sublime_task_lists)
importlib.reload(renderer)

plugin_sublime_task_lists = sublime_task_lists.plugin_sublime_task_lists

_markdown = mistune.create_markdown(
    renderer=mistune.AstRenderer(),
    plugins=["footnotes", "table", plugin_sublime_task_lists],
    # plugins=["table"],
)

TEMPLATE = """
    <body>
        <style type="text/css">
            .blockquote p {{
                padding-left: 0.5em;
                border-left: 0.25em solid gray;
            }}
        </style>
        {content}
    </body>
"""


def markdown(source):
    ast = _markdown(source)
    transformer = renderer.Ast2HTML()

    return "\n".join(transformer.transform(**child) for child in ast)


# markdown_map = defaultdict(dict)


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


class MarkdownPreview:
    def __init__(self, view, sheet):
        self.view = view
        self.sheet = sheet

    def update(self):
        self.sheet.set_contents(
            markdown(self.view.substr(sublime.Region(0, self.view.size())))
        )

    def close(self):
        self.sheet.close()

    def should_close(self, view):
        return view.sheet() not in (self.view.sheet(), self.sheet)


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

    # def on_activated(self):
    #     window = self.view.window()
    #     for view, preview in list(markdown_map[window].items()):
    #         if preview.should_close(self.view):
    #             preview.close()
    #             markdown_map[window].pop(view)
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
        # padding-left: 0.5em; border-left: 0.25em solid gray"
        sheet.set_contents(
            TEMPLATE.format(
                content=markdown(self.view.substr(sublime.Region(0, self.view.size())))
            )
        )
