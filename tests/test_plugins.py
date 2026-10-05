import random

from eden.core.app import help_text
import sys
import types

import pytest

from eden.core.plugin import COMMAND_RE, Callback, Plugin, discover
from eden.core.ratelimit import Cooldown


def test_discovery_finds_plugins_with_valid_unique_commands():
    plugins = discover()
    names = [c.name for p in plugins for c in p.commands]
    assert {p.name for p in plugins} >= {"tarot", "iching"}
    assert len(names) == len(set(names))
    assert all(COMMAND_RE.match(n) for n in names)
    assert all(1 <= len(c.description) <= 256 for p in plugins for c in p.commands)


def test_help_lists_every_command():
    plugins = discover()
    text = help_text(plugins)
    for p in plugins:
        for c in p.commands:
            assert f"/{c.name}" in text


def test_cooldown_per_user_and_chat():
    t = [100.0]
    cd = Cooldown(5, clock=lambda: t[0])
    assert cd.hit(1, 10) == 0
    assert cd.hit(1, 10) == 5          # same user, same chat: wait
    assert cd.hit(1, 11) == 0          # other user
    assert cd.hit(2, 10) == 0          # same user, other chat
    t[0] += 5
    assert cd.hit(1, 10) == 0


def test_duplicate_callback_prefixes_are_rejected(monkeypatch):
    async def noop(update, context):
        pass
    pkg = types.ModuleType("fakeplugins")
    pkg.__path__ = []
    a, b = types.ModuleType("fakeplugins.a"), types.ModuleType("fakeplugins.b")
    a.PLUGIN = Plugin("a", "A", callbacks=(Callback("same", noop),))
    b.PLUGIN = Plugin("b", "B", callbacks=(Callback("same", noop),))
    for m in (pkg, a, b):
        monkeypatch.setitem(sys.modules, m.__name__, m)
    monkeypatch.setattr("pkgutil.iter_modules",
                        lambda path: [types.SimpleNamespace(name="a"), types.SimpleNamespace(name="b")])
    with pytest.raises(ValueError, match="defined twice"):
        discover("fakeplugins")
