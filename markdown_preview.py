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
importlib.reload(sublime_task_lists)

plugin_sublime_task_lists = sublime_task_lists.plugin_sublime_task_lists

markdown = mistune.create_markdown(
    renderer="html",
    plugins=["footnotes", "strikethrough", "table", plugin_sublime_task_lists],
)

markdown_map = defaultdict(dict)


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
    def run(self, edit):
        view = self.view
        if "markdown" not in view.syntax().scope:
            return

        if view in markdown_map[view.window()]:
            return
        sheet = view.window().new_html_sheet(f"Preview", "")
        view.window().select_sheets([view.sheet(), sheet])
        view.window().focus_view(view)
        preview = MarkdownPreview(self.view, sheet)
        preview.update()
        markdown_map[view.window()][view] = preview

    def is_enabled(self):
        return "markdown" in self.view.syntax().scope


class MarkdownViewUpdate(sublime_plugin.ViewEventListener):
    def on_activated(self):
        window = self.view.window()
        for view, preview in list(markdown_map[window].items()):
            if preview.should_close(self.view):
                preview.close()
                markdown_map[window].pop(view)


class MarkdownView2Update(sublime_plugin.TextChangeListener):
    def on_text_changed(self, changes):
        markdown_views = markdown_map[self.buffer.primary_view().window()]
        for view in self.buffer.views():
            try:
                markdown_views[view].update()
            except KeyError:
                pass
