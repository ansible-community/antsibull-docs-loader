# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Routing data for collections.
"""

from __future__ import annotations

import dataclasses
import datetime
import types
import typing as t
from collections.abc import Mapping
from pathlib import Path

from ._yaml import load_yaml_file as _load_yaml_file
from .ansible import (
    CORE_DOCUMENTABLE_PLUGIN_TYPES,
    CORE_OTHER_PLUGIN_TYPES,
    EDA_PLUGIN_TYPES,
)

if t.TYPE_CHECKING:
    from .ansible import PluginType
    from .data import CollectionInfo, CollectionInfos


_CORE_ROUTING_INFO = "config/ansible_builtin_runtime.yml"
_COLLECTION_ROUTING_INFO = "meta/runtime.yml"
# EDA docs: https://docs.ansible.com/projects/rulebook/en/latest/plugin_lifecycle.html
_COLLECTION_EDA_ROUTING_INFO = "extensions/eda/eda_runtime.yml"


@dataclasses.dataclass(frozen=True)
class RemovalData:
    warning_text: str | None
    removal_version: str | None
    removal_date: datetime.date | str | None


@dataclasses.dataclass(frozen=True)
class PluginRouting:
    action_plugin: str | None  # this is **only used for modules**!
    redirect: str | types.EllipsisType | None  # ellipsis == infinite loop
    redirect_chain: tuple[str, ...] | None
    redirect_deprecations: tuple[tuple[str, RemovalData], ...] | None
    redirect_tombstone: bool
    redirect_dead_end: bool
    redirect_error: str | None
    deprecation: RemovalData | None
    tombstone: RemovalData | None


@dataclasses.dataclass(frozen=True)
class CollectionRouting:
    plugin_data: dict[PluginType, dict[str, PluginRouting]]


def _load_removal_data(
    plugin_data: Mapping,
    *,
    path: Path,
    plugin_type: str,
    plugin_name: str,
    typ: t.Literal["deprecation", "tombstone"],
) -> RemovalData | None:
    if typ not in plugin_data:
        return None
    removal_data = plugin_data.get(typ)
    if not isinstance(removal_data, Mapping):
        raise ValueError(
            f"{typ.title()} for {plugin_type} {plugin_name} in {path}"
            f" must be a mapping, got {type(removal_data)}"
        )
    warning_text = removal_data.get("warning_text")
    if warning_text is not None and not isinstance(warning_text, str):
        raise ValueError(
            f"{typ.title()} for {plugin_type} {plugin_name} in {path}"
            f" must have its warning_text a string, got {type(warning_text)}"
        )
    removal_version = removal_data.get("removal_version")
    if removal_version is not None and not isinstance(removal_version, str):
        raise ValueError(
            f"{typ.title()} for {plugin_type} {plugin_name} in {path}"
            f" must have its removal_version a string, got {type(removal_version)}"
        )
    removal_date = removal_data.get("removal_date")
    if isinstance(removal_date, datetime.datetime):
        removal_date = removal_date.date()
    elif removal_date is not None and not isinstance(
        removal_date, (datetime.date, str)
    ):
        raise ValueError(
            f"{typ.title()} for {plugin_type} {plugin_name} in {path}"
            f" must have its removal_date a string or date, got {type(removal_date)}"
        )
    return RemovalData(
        warning_text=warning_text,
        removal_version=removal_version,
        removal_date=removal_date,
    )


def _parse_plugin_data(
    plugin_data: t.Any,
    *,
    path: Path,
    own_name: str,
    real_plugin_type: PluginType,
    plugin_type: str,
    plugin_name: str,
) -> PluginRouting:
    if not plugin_data:
        return PluginRouting(
            action_plugin=None,
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        )
    if not isinstance(plugin_data, Mapping):
        raise ValueError(
            f"Routing information for {plugin_type} {plugin_name} in {path}"
            f" must be a mapping, got {type(plugin_data)}"
        )
    deprecation = _load_removal_data(
        plugin_data,
        path=path,
        plugin_type=plugin_type,
        plugin_name=plugin_name,
        typ="deprecation",
    )
    tombstone = _load_removal_data(
        plugin_data,
        path=path,
        plugin_type=plugin_type,
        plugin_name=plugin_name,
        typ="tombstone",
    )
    plugin_fqcn = f"{own_name}.{plugin_name}"
    action_plugin: str | None = None
    redirect: str | types.EllipsisType | None = None
    redirect_chain: tuple[str, ...] | None = None
    redirect_deprecations: tuple[tuple[str, RemovalData], ...] | None = None
    redirect_error: str | None = None
    if real_plugin_type == "module" and "action_plugin" in plugin_data:
        action_plugin = plugin_data["action_plugin"]
        if not isinstance(action_plugin, str):
            raise ValueError(
                f"action_plugin for {plugin_type} {plugin_name} in {path}"
                f" must be a string, got {type(action_plugin)}"
            )
    if "redirect" in plugin_data:
        redirect = plugin_data["redirect"]
        if not isinstance(redirect, str):
            raise ValueError(
                f"redirect for {plugin_type} {plugin_name} in {path}"
                f" must be a string, got {type(redirect)}"
            )
        if redirect == plugin_fqcn:
            # This is an obvious infinite loop
            redirect = ...
            redirect_chain = (plugin_fqcn, plugin_fqcn)
            redirect_error = "Detected circular redirect"
            if deprecation is not None:
                redirect_deprecations = ((plugin_fqcn, deprecation),)
    return PluginRouting(
        action_plugin=action_plugin,
        redirect=redirect,
        redirect_chain=redirect_chain,
        redirect_deprecations=redirect_deprecations,
        redirect_tombstone=False,
        redirect_dead_end=False,
        redirect_error=redirect_error,
        deprecation=deprecation,
        tombstone=tombstone,
    )


def _load_routing_information(
    data: t.Any,
    *,
    path: Path,
    own_name: str,
    get_real_plugin_type_name: t.Callable[[str], PluginType | None],
) -> dict[PluginType, dict[str, PluginRouting]]:
    if data is None:
        # If the YAML file is empty, PyYAML returns None
        data = {}
    if not isinstance(data, Mapping):
        raise ValueError(
            f"Runtime information in {path} must have a top-level mapping, got {type(data)}"
        )
    result: dict[PluginType, dict[str, PluginRouting]] = {}
    plugin_routing = data.get("plugin_routing")
    if plugin_routing is None:
        return result
    if not isinstance(plugin_routing, Mapping):
        raise ValueError(
            f"Plugin routing information in {path} must be a mapping, got {type(plugin_routing)}"
        )
    for plugin_type, plugins_data in plugin_routing.items():
        real_plugin_type = get_real_plugin_type_name(plugin_type)
        if real_plugin_type is None:
            continue
        if not plugins_data:
            continue
        if not isinstance(plugins_data, Mapping):
            raise ValueError(
                f"Plugin routing information in {path} for type {plugin_type}"
                f" must be a mapping, got {type(plugins_data)}"
            )
        real_plugin_data: dict[str, PluginRouting] = {}
        for plugin_name, plugin_data in plugins_data.items():
            real_plugin_data[plugin_name] = _parse_plugin_data(
                plugin_data,
                path=path,
                own_name=own_name,
                real_plugin_type=real_plugin_type,
                plugin_type=plugin_type,
                plugin_name=plugin_name,
            )
        result[real_plugin_type] = real_plugin_data
    return result


def _get_real_plugin_type_name(name: str) -> PluginType | None:
    if name == "modules":
        return "module"
    if name in CORE_DOCUMENTABLE_PLUGIN_TYPES:
        return name  # type: ignore
    if name in CORE_OTHER_PLUGIN_TYPES:
        return name  # type: ignore
    return None


def _load_core_routing_information(
    path: Path,
) -> dict[PluginType, dict[str, PluginRouting]]:
    routing_path = path / _CORE_ROUTING_INFO
    try:
        data = _load_yaml_file(routing_path)
    except FileNotFoundError:
        # This should only happen for Ansible 2.9
        return {}
    return _load_routing_information(
        data,
        path=routing_path,
        own_name="ansible.builtin",
        get_real_plugin_type_name=_get_real_plugin_type_name,
    )


def _load_collection_routing_information(
    collection_info: CollectionInfo,
) -> dict[PluginType, dict[str, PluginRouting]]:
    path = collection_info.path / _COLLECTION_ROUTING_INFO
    try:
        data = _load_yaml_file(path)
    except FileNotFoundError:
        return {}
    return _load_routing_information(
        data,
        path=path,
        own_name=collection_info.full_name,
        get_real_plugin_type_name=_get_real_plugin_type_name,
    )


def _load_eda_routing_information(
    collection_info: CollectionInfo,
) -> dict[PluginType, dict[str, PluginRouting]]:
    path = collection_info.path / _COLLECTION_EDA_ROUTING_INFO
    try:
        data = _load_yaml_file(path)
    except FileNotFoundError:
        return {}

    def get_real_plugin_type_name(name: str) -> PluginType | None:
        trans_name = f"eda_{name}"
        if trans_name in EDA_PLUGIN_TYPES:
            return trans_name  # type: ignore
        return None

    return _load_routing_information(
        data,
        path=path,
        own_name=collection_info.full_name,
        get_real_plugin_type_name=get_real_plugin_type_name,
    )


def load_routing_information(collection_info: CollectionInfo) -> CollectionRouting:
    """
    Load routing information for a single collection.

    Note that most of the routing information is not yet present.
    """
    if collection_info.is_ansible_core:
        return CollectionRouting(
            plugin_data=_load_core_routing_information(collection_info.path)
        )
    result = {}
    result.update(_load_collection_routing_information(collection_info))
    result.update(_load_eda_routing_information(collection_info))
    return CollectionRouting(plugin_data=result)


def collect_routing_information(
    collection_infos: CollectionInfos,
    *,
    handle_broken: (
        t.Callable[[CollectionInfo, Exception], CollectionRouting | None] | None
    ) = None,
) -> dict[str, CollectionRouting]:
    """
    Load routing information for all collections sequentially.

    The handler in ``handle_broken`` is used in case routing information
    cannot be loaded for a source.

    Note that most of the routing information is not yet present.
    """
    result = {}
    for collection_info in collection_infos.collections.values():
        try:
            result[collection_info.full_name] = load_routing_information(
                collection_info
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if handle_broken is None:
                raise
            res = handle_broken(collection_info, exc)
            if res is not None:
                result[collection_info.full_name] = res
    return result


def _complete_redirect(  # noqa: C901 # pylint: disable=too-many-branches
    plugin_data: PluginRouting,
    *,
    routing_data: Mapping[str, CollectionRouting],
    collection_name: str,
    plugin_type: PluginType,
    plugin_name: str,
) -> PluginRouting:
    if plugin_data.redirect in (None, ...) or plugin_data.redirect_chain is not None:
        # Already done!
        return plugin_data
    fqcn = f"{collection_name}.{plugin_name}"
    found_names: set[str] = set()
    found_names.add(fqcn)
    redirection_list: list[
        tuple[str, str, str, PluginRouting | None, dict[str, PluginRouting] | None]
    ] = [(fqcn, collection_name, plugin_name, plugin_data, None)]
    next_name: str = plugin_data.redirect  # type: ignore # this is ensured further up
    redirect_chain: tuple[str, ...] | None = None
    redirect_deprecations: tuple[tuple[str, RemovalData], ...] | None = None
    redirect_tombstone = False
    redirect_dead_end = False
    redirect_error: str | None = None
    is_loop: bool = False
    while True:
        if next_name in found_names:
            # We found a cycle!
            start_index = next(
                index
                for index, elt in enumerate(redirection_list)
                if elt[0] == next_name
            )
            is_loop = True
            redirect_error = "Detected circular redirect"
            loop = redirection_list[start_index:]
            redirect_chain = tuple(elt[0] for elt in loop)
            redirect_deprecations_w_index = tuple(
                (index, (elt[0], elt[3].deprecation))
                for index, elt in enumerate(loop)
                if elt[3] is not None and elt[3].deprecation is not None
            )
            for index, (
                plugin_fqcn,
                _plugin_collection_name,
                plugin_plugin_name,
                plugin_plugin_data,
                plugin_owner,
            ) in enumerate(loop):
                redirect_chain += (plugin_fqcn,)
                if plugin_plugin_data is not None:
                    new_plugin_data = PluginRouting(
                        action_plugin=plugin_plugin_data.action_plugin,
                        redirect=...,
                        redirect_chain=redirect_chain,
                        redirect_deprecations=(
                            tuple(
                                elt
                                for idx, elt in redirect_deprecations_w_index
                                if idx >= index
                            )
                            + tuple(
                                elt
                                for idx, elt in redirect_deprecations_w_index
                                if idx < index
                            )
                        )
                        or None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=redirect_error,
                        deprecation=plugin_plugin_data.deprecation,
                        tombstone=plugin_plugin_data.tombstone,
                    )
                    if plugin_owner:
                        plugin_owner[plugin_plugin_name] = new_plugin_data
                    if plugin_fqcn == fqcn:
                        plugin_data = new_plugin_data
                else:
                    # This should never be reached
                    pass  # pragma: no cover
                redirect_chain = redirect_chain[1:]
            redirect_chain += (next_name,)
            redirect_deprecations = (
                tuple(elt for _index, elt in redirect_deprecations_w_index) or None
            )
            redirection_list = redirection_list[:start_index]
            break
        found_names.add(next_name)
        parts = next_name.split(".", 2)
        if len(parts) < 3:
            redirect_dead_end = True
            redirect_error = f"Found redirect to non-FQCN {next_name}"
            break
        next_ns, next_cn, next_pn = parts
        next_coll = f"{next_ns}.{next_cn}"
        if next_coll not in routing_data:
            redirection_list.append((next_name, next_coll, next_pn, None, None))
            redirect_dead_end = True
            redirect_error = f"Found redirect to unknown collection {next_coll}"
            break
        prd = routing_data[next_coll].plugin_data.get(plugin_type)
        pd = prd.get(next_pn) if prd else None
        if pd is not None and pd.tombstone:
            redirect_deprecations = ((next_name, pd.tombstone),)
            redirect_tombstone = True
            break
        if pd is None or pd.redirect is None:
            redirection_list.append((next_name, next_coll, next_pn, pd, None))
            break
        if (
            pd.redirect_error is not None
            or pd.redirect_tombstone
            or pd.redirect_dead_end
        ):
            redirect_chain = pd.redirect_chain
            redirect_deprecations = pd.redirect_deprecations
            redirect_tombstone = pd.redirect_tombstone
            redirect_dead_end = pd.redirect_dead_end
            redirect_error = pd.redirect_error
            is_loop = pd.redirect is ...
            break
        if pd.redirect is ...:
            raise AssertionError(  # pragma: no cover
                "Bad internal state: circular redirect should have been marked as an error"
            )
        redirection_list.append((next_name, next_coll, next_pn, pd, prd))
        next_name = pd.redirect
    max_index = len(redirection_list) - 1
    for index, (
        plugin_fqcn,
        _plugin_collection_name,
        plugin_plugin_name,
        plugin_plugin_data,
        plugin_owner,
    ) in enumerate(reversed(redirection_list)):
        index = max_index - index
        redirect_chain = (plugin_fqcn,) + (redirect_chain or ())
        if plugin_plugin_data is not None:
            if plugin_plugin_data.deprecation:
                redirect_deprecations = (
                    (plugin_fqcn, plugin_plugin_data.deprecation),
                ) + (redirect_deprecations or ())
            new_plugin_data = PluginRouting(
                action_plugin=plugin_plugin_data.action_plugin,
                redirect=... if is_loop else next_name,
                redirect_chain=redirect_chain,
                redirect_deprecations=redirect_deprecations,
                redirect_tombstone=redirect_tombstone,
                redirect_dead_end=redirect_dead_end,
                redirect_error=redirect_error,
                deprecation=plugin_plugin_data.deprecation,
                tombstone=plugin_plugin_data.tombstone,
            )
            if plugin_owner:
                plugin_owner[plugin_plugin_name] = new_plugin_data
            if plugin_fqcn == fqcn:
                plugin_data = new_plugin_data
    return plugin_data


def complete_redirects_for_collection(
    routing_data: Mapping[str, CollectionRouting], *, collection_name: str
) -> None:
    """
    Complete all redirection data for the given collection.
    """
    rd = routing_data.get(collection_name)
    if rd is None:
        return
    for plugin_type, plugin_routing_data in rd.plugin_data.items():
        # Do *not* use .items() in the next loop, since the values could be
        # changed by earlier iterations:
        for plugin_name in list(plugin_routing_data):
            plugin_routing_data[plugin_name] = _complete_redirect(
                plugin_routing_data[plugin_name],
                routing_data=routing_data,
                collection_name=collection_name,
                plugin_type=plugin_type,
                plugin_name=plugin_name,
            )


def complete_redirects(routing_data: Mapping[str, CollectionRouting]) -> None:
    """
    Complete all redirection data for all collections.
    """
    for collection_name in routing_data:
        complete_redirects_for_collection(routing_data, collection_name=collection_name)


__all__ = (
    "RemovalData",
    "PluginRouting",
    "CollectionRouting",
    "load_routing_information",
    "collect_routing_information",
    "complete_redirects_for_collection",
    "complete_redirects",
)
