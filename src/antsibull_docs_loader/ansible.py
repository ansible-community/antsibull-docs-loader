# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Use ansible-galaxy to list collections.
"""

from __future__ import annotations

import typing as t
from collections.abc import Mapping
from pathlib import Path

from .data import CollectionInfo

CoreDocumentablePluginType = t.Literal[  # pragma: no cover
    "become",
    "cache",
    "callback",
    "cliconf",
    "connection",
    "filter",
    "httpapi",
    "inventory",
    "lookup",
    "module",
    "netconf",
    "shell",
    "strategy",
    "test",
    "vars",
]

# There are more plugin types, but we aren't interested in them (yet).
# (In fact we are only interested in doc_fragments.)
CoreOtherPluginType = t.Literal[
    "action", "module_utils", "plugin_utils", "doc_fragments"
]

EdaPluginType = t.Literal[
    "eda_event_filter",
    "eda_event_source",
]

DocumentablePluginType = t.Union[CoreDocumentablePluginType, EdaPluginType]

PluginType = t.Union[DocumentablePluginType, CoreOtherPluginType]


CORE_DOCUMENTABLE_PLUGIN_TYPES: tuple[CoreDocumentablePluginType, ...] = (
    "become",
    "cache",
    "callback",
    "cliconf",
    "connection",
    "filter",
    "httpapi",
    "inventory",
    "lookup",
    "module",
    "netconf",
    "shell",
    "strategy",
    "test",
    "vars",
)

CORE_OTHER_PLUGIN_TYPES: tuple[CoreOtherPluginType, ...] = (
    "action",
    "doc_fragments",
    "module_utils",
    "plugin_utils",
)

EDA_PLUGIN_TYPES: tuple[EdaPluginType, ...] = (
    "eda_event_filter",
    "eda_event_source",
)

_EDA_DIRECTORIES: Mapping[EdaPluginType, str] = {
    "eda_event_filter": "extensions/eda/plugins/event_filter",
    "eda_event_source": "extensions/eda/plugins/event_source",
}

ALL_DOCUMENTABLE_PLUGIN_TYPES: tuple[DocumentablePluginType, ...] = tuple(
    sorted(CORE_DOCUMENTABLE_PLUGIN_TYPES + EDA_PLUGIN_TYPES)  # type: ignore
)

ALL_PLUGIN_TYPES: tuple[PluginType, ...] = tuple(
    sorted(ALL_DOCUMENTABLE_PLUGIN_TYPES + CORE_OTHER_PLUGIN_TYPES)
)


def get_plugin_directory(collection: CollectionInfo, plugin_type: PluginType) -> Path:
    """
    Find the path for a given plugin type in the given collection.

    If the plugin type is unknown, or not supported by the collection,
    a ValueError is raised. This can only happen for valid ``PluginType`` values
    if ``collection.is_ansible_core`` is true.
    """
    if plugin_type == "module":
        if collection.is_ansible_core:
            return collection.path / "modules"
        return collection.path / "plugins" / "modules"
    if (
        plugin_type in CORE_DOCUMENTABLE_PLUGIN_TYPES
        or plugin_type in CORE_OTHER_PLUGIN_TYPES
    ):
        return collection.path / "plugins" / plugin_type
    if not collection.is_ansible_core:
        directory: str | None = _EDA_DIRECTORIES.get(plugin_type)  # type: ignore
        if directory is not None:
            return collection.path / directory
    what = (
        "ansible-core"
        if collection.is_ansible_core
        else f"collection {collection.full_name}"
    )
    raise ValueError(f"Unknown plugin type {plugin_type!r} for {what}")


__all__ = (
    "CoreDocumentablePluginType",
    "CoreOtherPluginType",
    "EdaPluginType",
    "DocumentablePluginType",
    "PluginType",
    "CORE_DOCUMENTABLE_PLUGIN_TYPES",
    "CORE_OTHER_PLUGIN_TYPES",
    "EDA_PLUGIN_TYPES",
    "ALL_DOCUMENTABLE_PLUGIN_TYPES",
    "ALL_PLUGIN_TYPES",
    "get_plugin_directory",
)
