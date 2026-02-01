# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2021, Ansible Project

"""
YAML loading.
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import yaml

_SafeLoader: t.Any
try:
    # use C version if possible for speedup
    from yaml import CSafeLoader as _SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader as _SafeLoader


def load_yaml_file(path: Path) -> t.Any:
    """
    Load and parse YAML file ``path``.
    """
    with path.open("rb") as stream:
        return yaml.load(stream, Loader=_SafeLoader)
