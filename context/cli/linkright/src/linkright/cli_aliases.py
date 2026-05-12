"""Click utilities — AliasedGroup with prefix-match + alias support.

Industry pattern (git / npm / kubectl): users should NOT have to type the
full subcommand name when a prefix or alias is unambiguous. `git ci` →
commit, `kubectl get pods` works the same way. We mirror that here.

Resolution order (left to right):
  1. Exact command name
  2. Explicit alias (registered via ``add_alias``)
  3. Unique prefix match (e.g. `tail` → tailor if no other tail* exists)

Aliases are ADDITIVE. Long-form names always continue to work, so we never
break any existing workflow or muscle memory.
"""
from __future__ import annotations

import click


class AliasedGroup(click.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases: dict[str, str] = {}

    def add_alias(self, alias: str, target: str) -> None:
        self._aliases[alias] = target

    def add_aliases(self, mapping: dict[str, str]) -> None:
        self._aliases.update(mapping)

    def get_command(self, ctx, cmd_name):
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv
        if cmd_name in self._aliases:
            return super().get_command(ctx, self._aliases[cmd_name])
        matches = [n for n in self.list_commands(ctx) if n.startswith(cmd_name)]
        if len(matches) == 1:
            return super().get_command(ctx, matches[0])
        return None

    def resolve_command(self, ctx, args):
        # Use the real command's canonical name in help / error messages
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args
