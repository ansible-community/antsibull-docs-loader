# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2021, Ansible Project

"""
YAML loading.
"""

from __future__ import annotations

import io
import typing as t
from pathlib import Path

import yaml

_SafeLoader: t.Any
_SafeDumper: t.Any
try:
    # use C version if possible for speedup
    from yaml import CSafeDumper as _SafeDumper
    from yaml import CSafeLoader as _SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeDumper as _SafeDumper
    from yaml import SafeLoader as _SafeLoader


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
