# Sublime Text 4 Markdown Live Preview

Sublime Text 4 plugin to show a live preview of markdown.

[mistune](https://mistune.readthedocs.io/en/latest/) is vendored in because ST4's plugin system can't install PyPI packages.

## Quirks

* Tables are rendered as ascii-tables since ST4 doesn't support the `<table>` element
* Images don't load since ST4's `<img>` tag doesn't load `http`/`https` URLs
* Switching to a different file will close the preview[^1].

[^1]: which is intentional since I don't want it cluttering up my tabs.

