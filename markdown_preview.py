import importlib
import sys
from collections import defaultdict
from pathlib import Path

import sublime
import sublime_plugin

here = str(Path(__file__).parent)
if here not in sys.path:
    sys.path.append(here)
mistletoe = importlib.import_module("mistletoe")

markdown_map = defaultdict(dict)


class MarkdownPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if "markdown" not in self.view.syntax().scope:
            return

        if self.view in markdown_map[self.view.window()]:
            return
        sheet = self.view.window().new_html_sheet(
            f"Preview",
            mistletoe.markdown(self.view.substr(sublime.Region(0, self.view.size()))),
        )
        self.view.window().select_sheets([self.view.sheet(), sheet])
        self.view.window().focus_view(self.view)
        markdown_map[self.view.window()][self.view] = sheet

    def is_enabled(self):
        return "markdown" in self.view.syntax().scope


class MarkdownViewUpdate(sublime_plugin.ViewEventListener):
    def on_activated(self):
        window = self.view.window()
        remove_views = []
        for view, sheet in markdown_map[window].items():
            if self.view.sheet() not in (view.sheet(), sheet):
                remove_views.append(view)
                sheet.close()
        for view in remove_views:
            markdown_map[window].pop(view)


class MarkdownView2Update(sublime_plugin.TextChangeListener):
    def on_text_changed(self, changes):
        markdown_views = markdown_map[self.buffer.primary_view().window()]
        for view in self.buffer.views():
            if view in markdown_views:
                markdown_views[view].set_contents(
                    mistletoe.markdown(view.substr(sublime.Region(0, view.size())))
                )
