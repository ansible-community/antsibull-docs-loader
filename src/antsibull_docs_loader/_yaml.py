# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2021, Ansible Project

"""
YAML loading.
"""

from __future__ import annotations

import copy
import io
import typing as t
from pathlib import Path

import yaml

_SafeLoaderBase: t.Any
_SafeDumper: t.Any
try:
    # use C version if possible for speedup
    from yaml import CSafeDumper as _SafeDumper
    from yaml import CSafeLoader as _SafeLoaderBase
except ImportError:  # pragma: no cover
    from yaml import SafeDumper as _SafeDumper
    from yaml import SafeLoader as _SafeLoaderBase


def _construct_untagged(loader: t.Any, node: yaml.Node) -> t.Any:
    """
    Construct ``node``'s value as if it were not tagged, the same way that
    ansible-core's ``AnsibleConstructor._resolve_and_construct_object()`` does.
    """
    # copied to avoid mutating the node, which trips the recursion check
    node = copy.copy(node)
    node.tag = loader.resolve(type(node), node.value, (True, False))
    return loader.construct_object(node, deep=True)


class _SafeLoader(_SafeLoaderBase):
    """
    Safe YAML loader which also understands ansible-core's YAML tags.
    """


# These tags only affect how ansible-core treats a value at runtime, so the
# values are loaded as-is. !vault values are kept as ciphertext, not decrypted.
_SafeLoader.add_constructor("!unsafe", _construct_untagged)
_SafeLoader.add_constructor("!vault", _construct_untagged)
_SafeLoader.add_constructor("!vault-encrypted", _construct_untagged)

# Legacy aliases that ansible-core maps as well.
_SafeLoader.add_constructor(
    "tag:yaml.org,2002:python/dict", _SafeLoaderBase.construct_yaml_map
)
_SafeLoader.add_constructor(
    "tag:yaml.org,2002:python/unicode", _SafeLoaderBase.construct_yaml_str
)


def load_yaml_file(path: Path) -> t.Any:
    """
    Load and parse YAML file ``path``.
    """
    with path.open("rb") as stream:
        return yaml.load(stream, Loader=_SafeLoader)


def load_yaml_data(content: str | bytes) -> t.Any:
    """
    Load and parse YAML file content ``content``.
    """
    return yaml.load(content, Loader=_SafeLoader)


def format_yaml(content: t.Any) -> str:
    """
    Format YAML to string.
    """
    stream = io.StringIO()
    dumper = _SafeDumper
    dumper.ignore_aliases = lambda *args: True  # type: ignore[method-assign]
    yaml.dump(
        content,
        stream,
        default_flow_style=False,
        encoding="utf-8",
        Dumper=dumper,
        explicit_start=False,
        sort_keys=False,
    )
    return stream.getvalue()
