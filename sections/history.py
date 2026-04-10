"""This Day in Team History section.

First extraction in the sectioned build.py refactor (Unit 3). Pattern for
all subsequent section files: import only stdlib + TeamBriefing, read state
exclusively through the `briefing` parameter, return inner HTML string(s).
"""
from html import escape


def render(briefing):
    history_items = briefing.data["history"]
    if not history_items:
        return '<p class="idle-msg">No historical entries for today&rsquo;s date.</p>'
    items = []
    for h in history_items[:5]:
        items.append(f'<li><span class="inn">{h["year"]}</span><span class="txt">{escape(h["text"])}</span></li>')
    return f'<ul class="plays">{"".join(items)}</ul>'
