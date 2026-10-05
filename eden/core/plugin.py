"""Plugin contract and discovery.

A plugin is a package in eden/plugins/ that exposes PLUGIN = Plugin(...). Adding a feature means
adding a package: the core registers its commands, the Telegram command menu and /help.
"""

import importlib
import pkgutil
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from telegram import Update
from telegram.ext import ContextTypes

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
COMMAND_RE = re.compile(r"^[a-z0-9_]{1,32}$")   # Telegram's rule for command names


@dataclass(frozen=True)
class Command:
    name: str           # without the slash
    description: str    # shown in Telegram's command menu (max 256 chars)
    handler: Handler
    usage: str = ""     # e.g. "<domanda>", shown in /help


@dataclass(frozen=True)
class Plugin:
    name: str
    description: str
    commands: tuple[Command, ...] = field(default_factory=tuple)


def discover(package: str = "eden.plugins") -> list[Plugin]:
    """Import every sub-package of `package` and collect its PLUGIN; validate command names."""
    pkg = importlib.import_module(package)
    plugins: list[Plugin] = []
    for mod in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        module = importlib.import_module(f"{package}.{mod.name}")
        plugin = getattr(module, "PLUGIN", None)
        if isinstance(plugin, Plugin):
            plugins.append(plugin)
    seen: dict[str, str] = {}
    for p in plugins:
        for c in p.commands:
            if not COMMAND_RE.match(c.name):
                raise ValueError(f"invalid command name /{c.name} in plugin {p.name}")
            if c.name in seen or c.name in ("start", "help"):
                raise ValueError(f"/{c.name} defined twice ({seen.get(c.name, 'core')} and {p.name})")
            if not 1 <= len(c.description) <= 256:
                raise ValueError(f"/{c.name}: description must be 1-256 characters")
            seen[c.name] = p.name
    return plugins
