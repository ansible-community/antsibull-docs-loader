# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test ansible-galaxy code.
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import pytest  # pylint: disable=import-error

# pylint: disable-next=import-error
from ansible.constants import DOCUMENTABLE_PLUGINS as ANSIBLE_CORE_DOCUMENTABLE_PLUGINS

from antsibull_docs_loader.ansible import (
    _EDA_DIRECTORIES,
    ALL_DOCUMENTABLE_PLUGIN_TYPES,
    ALL_PLUGIN_TYPES,
    CORE_DOCUMENTABLE_PLUGIN_TYPES,
    CORE_OTHER_PLUGIN_TYPES,
    EDA_PLUGIN_TYPES,
    CoreDocumentablePluginType,
    CoreOtherPluginType,
    DocumentablePluginType,
    EdaPluginType,
    PluginType,
    get_plugin_directory,
)
from antsibull_docs_loader.data import (
    CollectionInfo,
)


def test_CORE_DOCUMENTABLE_PLUGIN_TYPES() -> None:
    # Make sure our list is sorted
    assert sorted(CORE_DOCUMENTABLE_PLUGIN_TYPES) == list(
        CORE_DOCUMENTABLE_PLUGIN_TYPES
    )

    # Make sure our list matches ansible-core (we install the latest devel branch in CI)
    assert list(CORE_DOCUMENTABLE_PLUGIN_TYPES) == sorted(
        ANSIBLE_CORE_DOCUMENTABLE_PLUGINS
    )

    # Make sure the literal list in the type matches
    assert list(CORE_DOCUMENTABLE_PLUGIN_TYPES) == sorted(
        t.get_args(CoreDocumentablePluginType)
    )


def test_CORE_OTHER_PLUGIN_TYPES() -> None:
    # Make sure our list is sorted
    assert sorted(CORE_OTHER_PLUGIN_TYPES) == list(CORE_OTHER_PLUGIN_TYPES)

    # Make sure our list matches ansible-core (we install the latest devel branch in CI)
    assert list(CORE_DOCUMENTABLE_PLUGIN_TYPES) == sorted(
        ANSIBLE_CORE_DOCUMENTABLE_PLUGINS
    )

    # Make sure the literal list in the type matches
    assert list(CORE_OTHER_PLUGIN_TYPES) == sorted(t.get_args(CoreOtherPluginType))


def test_EDA_PLUGIN_TYPES() -> None:
    # Make sure our list is sorted
    assert sorted(EDA_PLUGIN_TYPES) == list(EDA_PLUGIN_TYPES)

    # Make sure that the dictionary keys match the list
    assert sorted(_EDA_DIRECTORIES.keys()) == list(EDA_PLUGIN_TYPES)

    # Make sure the literal list in the type matches
    assert list(EDA_PLUGIN_TYPES) == sorted(t.get_args(EdaPluginType))


def _get_union_args(union_type: t.Any) -> list[t.Any]:
    assert t.get_origin(union_type) is t.Union
    result: list[t.Any] = []
    for ut in t.get_args(union_type):
        assert t.get_origin(ut) is t.Literal
        result.extend(t.get_args(ut))
    return result


def test_ALL_DOCUMENTABLE_PLUGIN_TYPES() -> None:
    # Make sure our list is sorted
    assert sorted(ALL_DOCUMENTABLE_PLUGIN_TYPES) == list(ALL_DOCUMENTABLE_PLUGIN_TYPES)

    # Make sure that ALL_DOCUMENTABLE_PLUGIN_TYPES =
    # CORE_DOCUMENTABLE_PLUGIN_TYPES + EDA_PLUGIN_TYPES
    assert len(ALL_DOCUMENTABLE_PLUGIN_TYPES) == len(
        CORE_DOCUMENTABLE_PLUGIN_TYPES
    ) + len(EDA_PLUGIN_TYPES)
    assert all(
        plugin_type in ALL_DOCUMENTABLE_PLUGIN_TYPES
        for plugin_type in CORE_DOCUMENTABLE_PLUGIN_TYPES
    )
    assert all(
        plugin_type in ALL_DOCUMENTABLE_PLUGIN_TYPES for plugin_type in EDA_PLUGIN_TYPES
    )

    # Make sure the literal list in the type matches
    assert list(ALL_DOCUMENTABLE_PLUGIN_TYPES) == sorted(
        _get_union_args(DocumentablePluginType)
    )


def test_ALL_PLUGIN_TYPES() -> None:
    # Make sure our list is sorted
    assert sorted(ALL_PLUGIN_TYPES) == list(ALL_PLUGIN_TYPES)

    # Make sure that ALL_PLUGIN_TYPES =
    # ALL_DOCUMENTABLE_PLUGIN_TYPES + CORE_OTHER_PLUGIN_TYPES
    assert len(ALL_PLUGIN_TYPES) == len(ALL_DOCUMENTABLE_PLUGIN_TYPES) + len(
        CORE_OTHER_PLUGIN_TYPES
    )
    assert all(
        plugin_type in ALL_PLUGIN_TYPES for plugin_type in ALL_DOCUMENTABLE_PLUGIN_TYPES
    )
    assert all(
        plugin_type in ALL_PLUGIN_TYPES for plugin_type in CORE_OTHER_PLUGIN_TYPES
    )

    # Make sure the literal list in the type matches
    assert list(ALL_PLUGIN_TYPES) == sorted(_get_union_args(PluginType))


def test_get_plugin_directory() -> None:
    core = CollectionInfo(
        path=Path("/core"),
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version=None,
        is_ansible_core=True,
    )
    coll = CollectionInfo(
        path=Path("/coll"),
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version=None,
    )

    assert get_plugin_directory(core, "module") == Path("/core/modules")
    assert get_plugin_directory(core, "lookup") == Path("/core/plugins/lookup")
    assert get_plugin_directory(core, "doc_fragments") == Path(
        "/core/plugins/doc_fragments"
    )
    assert get_plugin_directory(coll, "module") == Path("/coll/plugins/modules")
    assert get_plugin_directory(coll, "lookup") == Path("/coll/plugins/lookup")
    assert get_plugin_directory(coll, "doc_fragments") == Path(
        "/coll/plugins/doc_fragments"
    )
    assert get_plugin_directory(coll, "eda_event_source") == Path(
        "/coll/extensions/eda/plugins/event_source"
    )

    with pytest.raises(
        ValueError,
        match=r"^Unknown plugin type 'not-a-valid-type' for collection foo\.bar$",
    ):
        get_plugin_directory(coll, "not-a-valid-type")  # type: ignore
    with pytest.raises(
        ValueError, match=r"^Unknown plugin type 'eda_event_source' for ansible-core$"
    ):
        get_plugin_directory(core, "eda_event_source")
