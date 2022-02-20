import functools
import html
import operator
from textwrap import dedent

from .debounce import debounce

NL = "\n"
BR = "<br/>"
BRNL = BR + NL
NBSP = "&nbsp;"


class Ast2HTML:
    """
    Transform mistunes AST into a minihtml-compatible format.
    """

    def newline(self):
        return ""

    def _estimate_inline_width(self, **kwargs):
        if kwargs["type"] == "text":
            return len(kwargs["text"])
        if kwargs["type"] == "image":
            return 0
        return sum(self._estimate_inline_width(**child) for child in kwargs["children"])

    def _get_inline_text(self, **kwargs):
        if kwargs["type"] == "text":
            return kwargs["text"]

        if kwargs["type"] == "image":
            return ""

        return "".join(self._get_inline_text(**child) for child in kwargs["children"])

    def _estimate_table_cell_width(self, children, **kwargs):
        return sum(self._estimate_inline_width(**child) for child in children)

    def _estimate_table_head_widths(self, children, **kwargs):
        return [
            functools.reduce(
                max,
                (self._estimate_table_cell_width(**child) for child in children),
            )
        ]

    def _estimate_table_row_widths(self, children, **kwargs):
        return [self._estimate_table_cell_width(**child) for child in children]

    def _estimate_table_body_widths(self, children, **kwargs):
        return [self._estimate_table_row_widths(**child) for child in children]

    def _get_cell_text(self, children, align, width, **kwargs):
        text_width = len("".join(self._get_inline_text(**child) for child in children))
        content = "".join(self.transform(**child) for child in children)
        padding = width - text_width
        if align == "right":
            content = NBSP * padding + content
        elif align == "center":
            lpad = padding // 2
            rpad = padding - lpad
            content = NBSP * lpad + content + NBSP * rpad
        else:
            content = content + NBSP * padding

        return content

    def _print_table_head(self, children, column_widths, **kwargs):
        header_separator = (
            f'+={"=+=".join("=" * column_width for column_width in column_widths)}=+'
        )
        columns = [
            self._get_cell_text(**child, width=width)
            for child, width in zip(children, column_widths)
        ]
        columns = [text for text in columns if isinstance(text, str)]

        return [header_separator, f"| {' | '.join(columns)} |", header_separator]

    def _print_table_row(self, children, column_widths, **kwargs):
        columns = [
            self._get_cell_text(**child, width=width)
            for child, width in zip(children, column_widths)
        ]
        text_widths = [self._estimate_table_cell_width(**child) for child in children]
        columns = [text for text in columns if isinstance(text, str)]

        return f'| {" | ".join(columns)} |'

    def _print_table_body(self, children, column_widths, **kwargs):
        rows = [
            self._print_table_row(child["children"], column_widths=column_widths)
            for child in children
        ]
        row_separator = (
            f'+-{"-+-".join("-" * column_width for column_width in column_widths)}-+'
        )

        for row in rows:
            yield row
            yield row_separator

    def _estimate_table_widths(self, children, **kwargs):

        row_widths = functools.reduce(
            operator.add,
            (
                [self._estimate_table_row_widths(**child)]
                if child["type"] == "table_head"
                else self._estimate_table_body_widths(**child)
                for child in children
            ),
        )
        return [max(row_width) for row_width in zip(*row_widths)]

    def _get_table_text(self, children, **kwargs):
        column_widths = self._estimate_table_widths(children, **kwargs)
        for child in children:
            if child["type"] == "table_head":
                yield from self._print_table_head(
                    child["children"], column_widths=column_widths
                )
            else:
                yield from (
                    self._print_table_body(
                        child["children"], column_widths=column_widths
                    )
                )

    def table(self, *, children, **kwargs):
        table = f"<pre>{BRNL.join(self._get_table_text(children, **kwargs))}</pre>"
        return f"{BRNL}{table}{BRNL}"

    def text(self, text):
        # Replace all spaces with a nbsp entity, since minihtml
        # doesn't have a CSS white-space property
        return html.escape(text).replace(" ", NBSP)

    def emphasis(self, children):
        return f'<em>{"".join(self.transform(**child) for child in children)}</em>'

    def strong(self, children):
        return (
            f'<strong>{"".join(self.transform(**child) for child in children)}</strong>'
        )

    def link(self, link, children: list, title):
        return dedent(
            f"""\
                <a
                    src="{html.escape(link) }"
                >{"".join(self.transform(**child) for child in children)}</a>
            """
        )

    def image(self, src, alt, title):
        return dedent(
            f"""\
                <img
                    src="{html.escape(src)}"
                    alt="{html.escape(alt or "")}"
                    title="{html.escape(title or "")}"
                />
            """
        )

    def codespan(self, text):
        return f'<code class="code-span">{html.escape(text)}</code>'

    def linebreak(self):
        return "<br/>"

    def inline_html(self, html):
        return html

    def paragraph(self, children):
        return f'<p>{"".join(self.transform(**child) for child in children)}</p>'

    def heading(self, children, level):
        tag = f"h{level}"
        content = "".join(self.transform(**child) for child in children)
        return f"<{tag}>{content}</{tag}>"

    def thematic_break(self):
        return '<div class="thematic-break"></div>'

    def block_text(self, children):
        text = "".join(self.transform(**child) for child in children)

        return text

    def block_code(self, text, info):
        NL = "\n"
        return dedent(
            f"""\
            <div class="block-code">
                <pre><code>
                    {html.escape(text).rstrip(NL).replace(NL, BR)}
                </code></pre>
            </div>
        """
        )

    def block_quote(self, children):
        NL = "\n"
        text = f'{"".join(self.transform(**child) for child in children)}'

        return f'<div class="blockquote">{text}</div>'

    def list(self, children, ordered, level, start=None):
        return f'<ul>{"".join(self.transform(**child) for child in children)}</ul>'

    def list_item(self, children, level):
        return f'<li>{"".join(self.transform(**child) for child in children)}</li>'

    def task_list_item(self, children, checked, **kwargs):
        checked = "checked" if checked else "unchecked"
        classes = f"task-list-item__checkbox task-list-item__checkbox--{checked}"
        checkbox = f'<div class="{classes}"></div>'

        return f'<li>{checkbox} {"".join(self.transform(**child) for child in children)}</li>'

    def footnote_item(self, children, key, index):
        return f'<div>[{html.escape(key)}]: <div style="display: inline-block">{"".join(self.transform(**child) for child in children)}</div></div><br/>'

    def footnote_ref(self, key, index):
        return f'<div class="footnote__ref">[{html.escape(key)}]</div>'

    def footnotes(self, children, **kwargs):
        return "".join(self.transform(**child) for child in children)

    def transform(self, type, **kwargs):
        if hasattr(self, type):
            return getattr(self, type)(**kwargs)
        return f"UNHANDLED: {type}"
