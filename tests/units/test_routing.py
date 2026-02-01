# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test routing code.
"""

# pylint: disable=use-implicit-booleaness-not-comparison
# pylint: disable=too-many-lines

from __future__ import annotations

import copy
import datetime
from collections.abc import Mapping
from pathlib import Path

import pytest  # pylint: disable=import-error

from antsibull_docs_loader.data import CollectionInfo, CollectionInfos
from antsibull_docs_loader.routing import (
    CollectionRouting,
    PluginRouting,
    RemovalData,
    collect_routing_information,
    complete_redirects,
    complete_redirects_for_collection,
    load_routing_information,
)


def test_load_routing_information_core(tmp_path: Path) -> None:
    core = CollectionInfo(
        path=tmp_path,
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version="2.20.1",
        is_ansible_core=True,
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    metadata = config_dir / "ansible_builtin_runtime.yml"

    routing_info = load_routing_information(core)
    assert routing_info.plugin_data == {}

    metadata.write_text("---")
    routing_info = load_routing_information(core)
    assert routing_info.plugin_data == {}

    metadata.write_text("""---
plugin_routing:
""")
    routing_info = load_routing_information(core)
    assert routing_info.plugin_data == {}

    metadata.write_text("""---
plugin_routing:
  connection:
""")
    routing_info = load_routing_information(core)
    assert routing_info.plugin_data == {}

    metadata.write_text("""---
plugin_routing:
  nothing-we-care-about:
    foo:
""")
    routing_info = load_routing_information(core)
    assert routing_info.plugin_data == {}

    metadata.write_text("""---
plugin_routing:
  connection:
    redirected_local:
      redirect: ansible.builtin.local
      deprecation:
        warning_text: foo
        removal_version: 1.2.3
        removal_date: 2030-01-01
  modules:
    formerly_core_ping:
      redirect: testns.testcoll.ping
      tombstone:
        warning_text: foo
        removal_version: 1.2.3
        removal_date: "2030-01-01"
    uses_redirected_action:
      redirect: ansible.builtin.ping
    foo:
    bar: {}
    meh:
      action_plugin: foo
  module_utils:
    formerly_core:
      redirect: ansible_collections.testns.testcoll.plugins.module_utils.base
      deprecation: {}
    sub1.sub2.formerly_core:
      redirect: ansible_collections.testns.testcoll.plugins.module_utils.base
      tombstone: {}
  action:
    uses_redirected_action:
      redirect: testns.testcoll.subclassed_norm
      tombstone:
        warning_text:
        removal_version:
        removal_date:
  filter:
    formerly_core_filter:
      redirect: ansible.builtin.bool
      deprecation:
        warning_text: foo
        removal_version: 1.2.3
        removal_date: 2030-01-01 01:02:03
    formerly_core_masked_filter:
      redirect: ansible.builtin.bool
  inventory:
    formerly_core_inventory:
      redirect: testns.content_adj.statichost
  lookup:
    formerly_core_lookup:
      redirect: testns.testcoll.mylookup
  shell:
    formerly_core_powershell:
      redirect: ansible.builtin.powershell
  test:
    formerly_core_test:
      redirect: ansible.builtin.search
    formerly_core_masked_test:
      redirect: ansible.builtin.search
  netconf:
    loop:
      redirect: ansible.builtin.loop
    loop_w_depr:
      redirect: ansible.builtin.loop_w_depr
      deprecation: {}
import_redirection:
  ansible.module_utils.formerly_core:
    redirect: ansible_collections.testns.testcoll.plugins.module_utils.base
  ansible.module_utils.known_hosts:
    redirect: ansible_collections.community.general.plugins.module_utils.known_hosts
""")
    routing_info = load_routing_information(core)

    assert sorted(routing_info.plugin_data) == [
        "action",
        "connection",
        "filter",
        "inventory",
        "lookup",
        "module",
        "module_utils",
        "netconf",
        "shell",
        "test",
    ]
    assert routing_info.plugin_data["connection"] == {
        "redirected_local": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.local",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=RemovalData(
                warning_text="foo",
                removal_version="1.2.3",
                removal_date=datetime.date(2030, 1, 1),
            ),
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["module"] == {
        "formerly_core_ping": PluginRouting(
            action_plugin=None,
            redirect="testns.testcoll.ping",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=RemovalData(
                warning_text="foo",
                removal_version="1.2.3",
                removal_date="2030-01-01",
            ),
        ),
        "uses_redirected_action": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.ping",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "foo": PluginRouting(
            action_plugin=None,
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "bar": PluginRouting(
            action_plugin=None,
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "meh": PluginRouting(
            action_plugin="foo",
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["module_utils"] == {
        "formerly_core": PluginRouting(
            action_plugin=None,
            redirect="ansible_collections.testns.testcoll.plugins.module_utils.base",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=RemovalData(
                warning_text=None,
                removal_version=None,
                removal_date=None,
            ),
            tombstone=None,
        ),
        "sub1.sub2.formerly_core": PluginRouting(
            action_plugin=None,
            redirect="ansible_collections.testns.testcoll.plugins.module_utils.base",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=RemovalData(
                warning_text=None,
                removal_version=None,
                removal_date=None,
            ),
        ),
    }
    assert routing_info.plugin_data["action"] == {
        "uses_redirected_action": PluginRouting(
            action_plugin=None,
            redirect="testns.testcoll.subclassed_norm",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=RemovalData(
                warning_text=None,
                removal_version=None,
                removal_date=None,
            ),
        ),
    }
    assert routing_info.plugin_data["filter"] == {
        "formerly_core_filter": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.bool",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=RemovalData(
                warning_text="foo",
                removal_version="1.2.3",
                removal_date=datetime.date(2030, 1, 1),
            ),
            tombstone=None,
        ),
        "formerly_core_masked_filter": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.bool",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["inventory"] == {
        "formerly_core_inventory": PluginRouting(
            action_plugin=None,
            redirect="testns.content_adj.statichost",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["lookup"] == {
        "formerly_core_lookup": PluginRouting(
            action_plugin=None,
            redirect="testns.testcoll.mylookup",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["shell"] == {
        "formerly_core_powershell": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.powershell",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["test"] == {
        "formerly_core_test": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.search",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "formerly_core_masked_test": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.search",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["test"] == {
        "formerly_core_test": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.search",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "formerly_core_masked_test": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.search",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["netconf"] == {
        "loop": PluginRouting(
            action_plugin=None,
            redirect=...,
            redirect_chain=("ansible.builtin.loop", "ansible.builtin.loop"),
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error="Detected circular redirect",
            deprecation=None,
            tombstone=None,
        ),
        "loop_w_depr": PluginRouting(
            action_plugin=None,
            redirect=...,
            redirect_chain=(
                "ansible.builtin.loop_w_depr",
                "ansible.builtin.loop_w_depr",
            ),
            redirect_deprecations=(
                (
                    "ansible.builtin.loop_w_depr",
                    RemovalData(
                        warning_text=None,
                        removal_version=None,
                        removal_date=None,
                    ),
                ),
            ),
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error="Detected circular redirect",
            deprecation=RemovalData(
                warning_text=None,
                removal_version=None,
                removal_date=None,
            ),
            tombstone=None,
        ),
    }


LOAD_ROUTING_INFORMATION_CORE_FAIL_DATA: list[tuple[str, str]] = [
    (
        """---
        "plugin_routing"
        """,
        r"^Runtime information in .* must have a top-level mapping, got <class 'str'>$",
    ),
    (
        """---
        plugin_routing:
          - foo
        """,
        r"^Plugin routing information in .* must be a mapping, got <class 'list'>$",
    ),
    (
        """---
        plugin_routing:
          connection:
            - foo
        """,
        r"^Plugin routing information in .* for type connection must be a mapping,"
        r" got <class 'list'>$",
    ),
    (
        """---
        plugin_routing:
          modules:
            foo: 123
        """,
        r"^Routing information for modules foo in .* must be a mapping, got <class 'int'>$",
    ),
    (
        """---
        plugin_routing:
          modules:
            foo:
              action_plugin: true
        """,
        r"^action_plugin for modules foo in .* must be a string, got <class 'bool'>$",
    ),
    (
        """---
        plugin_routing:
          connection:
            foo:
              redirect: 123
        """,
        r"^redirect for connection foo in .* must be a string, got <class 'int'>$",
    ),
    (
        """---
        plugin_routing:
          connection:
            foo:
              deprecation:
        """,
        r"^Deprecation for connection foo in .* must be a mapping, got <class 'NoneType'>$",
    ),
    (
        """---
        plugin_routing:
          connection:
            foo:
              deprecation:
                warning_text: 123
        """,
        r"^Deprecation for connection foo in .* must have its warning_text a string,"
        r" got <class 'int'>$",
    ),
    (
        """---
        plugin_routing:
          connection:
            foo:
              deprecation:
                removal_version: true
        """,
        r"^Deprecation for connection foo in .* must have its removal_version a string,"
        r" got <class 'bool'>$",
    ),
    (
        """---
        plugin_routing:
          connection:
            foo:
              deprecation:
                removal_date: 1.2
        """,
        r"^Deprecation for connection foo in .* must have its removal_date a string or date,"
        r" got <class 'float'>$",
    ),
]


@pytest.mark.parametrize(
    "runtime_content, expected_error",
    LOAD_ROUTING_INFORMATION_CORE_FAIL_DATA,
)
def test_load_routing_information_core_fail(
    runtime_content: str, expected_error: str, tmp_path: Path
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    metadata = config_dir / "ansible_builtin_runtime.yml"
    metadata.write_text(runtime_content)
    core = CollectionInfo(
        path=tmp_path,
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version="2.20.1",
        is_ansible_core=True,
    )
    with pytest.raises(ValueError, match=expected_error):
        load_routing_information(core)


def test_load_routing_information_collection(tmp_path: Path) -> None:
    coll = CollectionInfo(
        path=tmp_path,
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version=None,
        is_ansible_core=False,
    )
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    metadata = meta_dir / "runtime.yml"

    extension_dir = tmp_path / "extensions"
    extension_dir.mkdir()
    eda_dir = extension_dir / "eda"
    eda_dir.mkdir()
    eda_runtime = eda_dir / "eda_runtime.yml"

    routing_info = load_routing_information(coll)
    assert routing_info.plugin_data == {}

    metadata.write_text("---")
    eda_runtime.write_text("---")
    routing_info = load_routing_information(coll)
    assert routing_info.plugin_data == {}

    metadata.write_text("""---
plugin_routing:
  modules:
    formerly_core_ping:
      redirect: testns.testcoll.ping
      tombstone:
        warning_text: foo
        removal_version: 1.2.3
        removal_date: "2030-01-01"
    uses_redirected_action:
      redirect: ansible.builtin.ping
    foo:
    bar: {}
    meh:
      action_plugin: foo
""")
    eda_runtime.write_text("""---
plugin_routing:
  event_source:
    old_webhook:
      tombstone:
        removal_version: "2.0.0"
        warning_text: foo
  event_filter:
    legacy_filter:
      redirect: "foo.bar.baz"
      deprecation:
        removal_version: "3.0.0"
        warning_text: bar
  i-dont-care:
    meh:
""")
    routing_info = load_routing_information(coll)

    assert sorted(routing_info.plugin_data) == [
        "eda_event_filter",
        "eda_event_source",
        "module",
    ]
    assert routing_info.plugin_data["module"] == {
        "formerly_core_ping": PluginRouting(
            action_plugin=None,
            redirect="testns.testcoll.ping",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=RemovalData(
                warning_text="foo",
                removal_version="1.2.3",
                removal_date="2030-01-01",
            ),
        ),
        "uses_redirected_action": PluginRouting(
            action_plugin=None,
            redirect="ansible.builtin.ping",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "foo": PluginRouting(
            action_plugin=None,
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "bar": PluginRouting(
            action_plugin=None,
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
        "meh": PluginRouting(
            action_plugin="foo",
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=None,
        ),
    }
    assert routing_info.plugin_data["eda_event_source"] == {
        "old_webhook": PluginRouting(
            action_plugin=None,
            redirect=None,
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=None,
            tombstone=RemovalData(
                warning_text="foo",
                removal_version="2.0.0",
                removal_date=None,
            ),
        ),
    }
    assert routing_info.plugin_data["eda_event_filter"] == {
        "legacy_filter": PluginRouting(
            action_plugin=None,
            redirect="foo.bar.baz",
            redirect_chain=None,
            redirect_deprecations=None,
            redirect_tombstone=False,
            redirect_dead_end=False,
            redirect_error=None,
            deprecation=RemovalData(
                warning_text="bar",
                removal_version="3.0.0",
                removal_date=None,
            ),
            tombstone=None,
        ),
    }


def test_collect_routing_information(tmp_path: Path) -> None:
    coll = CollectionInfo(
        path=tmp_path,
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version=None,
        is_ansible_core=False,
    )
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    metadata = meta_dir / "runtime.yml"

    ci = CollectionInfos.build([coll])
    ri = collect_routing_information(ci)
    assert ri == {"foo.bar": CollectionRouting(plugin_data={})}

    metadata.write_text("""---
plugin_routing: foo
""")
    with pytest.raises(
        ValueError,
        match=r"^Plugin routing information in .* must be a mapping, got <class 'str'>$",
    ):
        collect_routing_information(ci)

    def raise_error(ci: CollectionInfo, exc: Exception) -> CollectionRouting | None:
        assert ci is coll
        assert str(exc).endswith(" must be a mapping, got <class 'str'>")
        raise ValueError("foo")

    metadata.write_text("""---
plugin_routing: foo
""")
    with pytest.raises(ValueError, match=r"^foo$"):
        collect_routing_information(ci, handle_broken=raise_error)

    def return_none(  # pylint: disable=useless-return
        ci: CollectionInfo, exc: Exception
    ) -> CollectionRouting | None:
        assert ci is coll
        assert str(exc).endswith(" must be a mapping, got <class 'str'>")
        return None

    metadata.write_text("""---
plugin_routing: foo
""")
    ri = collect_routing_information(ci, handle_broken=return_none)
    assert ri == {}

    def return_ri(ci: CollectionInfo, exc: Exception) -> CollectionRouting | None:
        assert ci is coll
        assert str(exc).endswith(" must be a mapping, got <class 'str'>")
        return CollectionRouting(plugin_data={"connection": {}})

    metadata.write_text("""---
plugin_routing: foo
""")
    ri = collect_routing_information(ci, handle_broken=return_ri)
    assert ri == {"foo.bar": CollectionRouting(plugin_data={"connection": {}})}


@pytest.fixture(name="routing_info")
def fixture_routing_info() -> Mapping[str, CollectionRouting]:
    return {
        "foo.bar": CollectionRouting(
            plugin_data={
                "module": {
                    "baz": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "self_loop": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.self_loop",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "pre_loop_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.pre_loop_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "pre_loop_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_1",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="pre 2",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "loop_1": PluginRouting(
                        action_plugin=None,
                        redirect="bar.baz.loop_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="loop 1",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_3": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_1",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="loop 3",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="foo 1",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "chain_3": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_4",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="foo 3",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_4": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.leave_chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.leave_chain_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_3": PluginRouting(
                        action_plugin=None,
                        redirect="outside.here.meh",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                },
                "lookup": {
                    "loop_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_3": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=("foo.bar.loop_3", "foo.bar.loop_3"),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.dead_chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.dead_chain_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_3": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=RemovalData(
                            warning_text="this is dead",
                            removal_version=None,
                            removal_date=None,
                        ),
                    ),
                    "broken_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.broken_chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "broken_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="this-is-not-a-fqcn",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                },
            },
        ),
        "bar.baz": CollectionRouting(
            plugin_data={
                "module": {
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                },
            },
        ),
    }


def test_complete_redirects(routing_info: Mapping[str, CollectionRouting]) -> None:
    complete_redirects(routing_info)
    assert routing_info == {
        "foo.bar": CollectionRouting(
            plugin_data={
                "module": {
                    "baz": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "self_loop": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.self_loop",
                            "foo.bar.self_loop",
                        ),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "pre_loop_1": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.pre_loop_1",
                            "foo.bar.pre_loop_2",
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.pre_loop_2",
                                RemovalData(
                                    warning_text="pre 2",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "pre_loop_2": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.pre_loop_2",
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.pre_loop_2",
                                RemovalData(
                                    warning_text="pre 2",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=RemovalData(
                            warning_text="pre 2",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "loop_1": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=RemovalData(
                            warning_text="loop 1",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_3": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=RemovalData(
                            warning_text="loop 3",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_4",
                        redirect_chain=(
                            "foo.bar.chain_1",
                            "foo.bar.chain_2",
                            "foo.bar.chain_3",
                            "foo.bar.chain_4",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.chain_1",
                                RemovalData(
                                    warning_text="foo 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.chain_3",
                                RemovalData(
                                    warning_text="foo 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="foo 1",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_4",
                        redirect_chain=(
                            "foo.bar.chain_2",
                            "foo.bar.chain_3",
                            "foo.bar.chain_4",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.chain_3",
                                RemovalData(
                                    warning_text="foo 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "chain_3": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_4",
                        redirect_chain=(
                            "foo.bar.chain_3",
                            "foo.bar.chain_4",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.chain_3",
                                RemovalData(
                                    warning_text="foo 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="foo 3",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_4": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="outside.here.meh",
                        redirect_chain=(
                            "foo.bar.leave_chain_1",
                            "foo.bar.leave_chain_2",
                            "foo.bar.leave_chain_3",
                            "outside.here.meh",
                        ),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=True,
                        redirect_error="Found redirect to unknown collection outside.here",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="outside.here.meh",
                        redirect_chain=(
                            "foo.bar.leave_chain_2",
                            "foo.bar.leave_chain_3",
                            "outside.here.meh",
                        ),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=True,
                        redirect_error="Found redirect to unknown collection outside.here",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_3": PluginRouting(
                        action_plugin=None,
                        redirect="outside.here.meh",
                        redirect_chain=(
                            "foo.bar.leave_chain_3",
                            "outside.here.meh",
                        ),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=True,
                        redirect_error="Found redirect to unknown collection outside.here",
                        deprecation=None,
                        tombstone=None,
                    ),
                },
                "lookup": {
                    "loop_1": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.loop_1",
                            "foo.bar.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_3",
                        ),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_3",
                        ),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_3": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=("foo.bar.loop_3", "foo.bar.loop_3"),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.dead_chain_3",
                        redirect_chain=(
                            "foo.bar.dead_chain_1",
                            "foo.bar.dead_chain_2",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.dead_chain_3",
                                RemovalData(
                                    warning_text="this is dead",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=True,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.dead_chain_3",
                        redirect_chain=("foo.bar.dead_chain_2",),
                        redirect_deprecations=(
                            (
                                "foo.bar.dead_chain_3",
                                RemovalData(
                                    warning_text="this is dead",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=True,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_3": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=RemovalData(
                            warning_text="this is dead",
                            removal_version=None,
                            removal_date=None,
                        ),
                    ),
                    "broken_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="this-is-not-a-fqcn",
                        redirect_chain=(
                            "foo.bar.broken_chain_1",
                            "foo.bar.broken_chain_2",
                        ),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=True,
                        redirect_error="Found redirect to non-FQCN this-is-not-a-fqcn",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "broken_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="this-is-not-a-fqcn",
                        redirect_chain=("foo.bar.broken_chain_2",),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=True,
                        redirect_error="Found redirect to non-FQCN this-is-not-a-fqcn",
                        deprecation=None,
                        tombstone=None,
                    ),
                },
            },
        ),
        "bar.baz": CollectionRouting(
            plugin_data={
                "module": {
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_4",
                        redirect_chain=(
                            "bar.baz.chain_2",
                            "foo.bar.chain_3",
                            "foo.bar.chain_4",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.chain_3",
                                RemovalData(
                                    warning_text="foo 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                },
            },
        ),
    }


def test_complete_redirects_for_collection(
    routing_info: Mapping[str, CollectionRouting],
) -> None:
    original = copy.deepcopy(routing_info)
    complete_redirects_for_collection(routing_info, collection_name="does-not-exist")
    assert original == routing_info

    complete_redirects_for_collection(routing_info, collection_name="bar.baz")
    assert routing_info == {
        "foo.bar": CollectionRouting(
            plugin_data={
                "module": {
                    "baz": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "self_loop": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.self_loop",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "pre_loop_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.pre_loop_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "pre_loop_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_1",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="pre 2",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "loop_1": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=RemovalData(
                            warning_text="loop 1",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_3": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=RemovalData(
                            warning_text="loop 3",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="foo 1",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "chain_3": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_4",
                        redirect_chain=(
                            "foo.bar.chain_3",
                            "foo.bar.chain_4",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.chain_3",
                                RemovalData(
                                    warning_text="foo 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=RemovalData(
                            warning_text="foo 3",
                            removal_version=None,
                            removal_date=None,
                        ),
                        tombstone=None,
                    ),
                    "chain_4": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.leave_chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.leave_chain_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "leave_chain_3": PluginRouting(
                        action_plugin=None,
                        redirect="outside.here.meh",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                },
                "lookup": {
                    "loop_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.loop_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "loop_3": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=("foo.bar.loop_3", "foo.bar.loop_3"),
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.dead_chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.dead_chain_3",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "dead_chain_3": PluginRouting(
                        action_plugin=None,
                        redirect=None,
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=RemovalData(
                            warning_text="this is dead",
                            removal_version=None,
                            removal_date=None,
                        ),
                    ),
                    "broken_chain_1": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.broken_chain_2",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                    "broken_chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="this-is-not-a-fqcn",
                        redirect_chain=None,
                        redirect_deprecations=None,
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                },
            },
        ),
        "bar.baz": CollectionRouting(
            plugin_data={
                "module": {
                    "loop_2": PluginRouting(
                        action_plugin=None,
                        redirect=...,
                        redirect_chain=(
                            "bar.baz.loop_2",
                            "foo.bar.loop_3",
                            "foo.bar.loop_1",
                            "bar.baz.loop_2",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.loop_3",
                                RemovalData(
                                    warning_text="loop 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                            (
                                "foo.bar.loop_1",
                                RemovalData(
                                    warning_text="loop 1",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error="Detected circular redirect",
                        deprecation=None,
                        tombstone=None,
                    ),
                    "chain_2": PluginRouting(
                        action_plugin=None,
                        redirect="foo.bar.chain_4",
                        redirect_chain=(
                            "bar.baz.chain_2",
                            "foo.bar.chain_3",
                            "foo.bar.chain_4",
                        ),
                        redirect_deprecations=(
                            (
                                "foo.bar.chain_3",
                                RemovalData(
                                    warning_text="foo 3",
                                    removal_version=None,
                                    removal_date=None,
                                ),
                            ),
                        ),
                        redirect_tombstone=False,
                        redirect_dead_end=False,
                        redirect_error=None,
                        deprecation=None,
                        tombstone=None,
                    ),
                },
            },
        ),
    }
