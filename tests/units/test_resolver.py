# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test resolver code.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest  # pylint: disable=import-error

from antsibull_docs_loader.ansible import PluginType
from antsibull_docs_loader.resolver import (
    Resolved,
    ResolveResult,
    resolve,
)
from antsibull_docs_loader.routing import (
    CollectionRouting,
    File,
    RemovalData,
    complete_redirects,
)

from .routing_fixtures import (  # noqa: F401  # pylint: disable=unused-import
    fixture_routing_info,
)

TEST_RESOLVE_DATA: list[tuple[str, PluginType, ResolveResult]] = [
    (
        "foobar.baz.bam",
        "module",
        ResolveResult(
            status=Resolved.COLLECTION_MISSING,
            fqcn="foobar.baz.bam",
            deprecations=[],
            tombstone=None,
            error="Collection foobar.baz not found",
            resolved=None,
        ),
    ),
    (
        "foo.bar.not_found",
        "module",
        ResolveResult(
            status=Resolved.NOT_FOUND,
            fqcn="foo.bar.not_found",
            deprecations=[],
            tombstone=None,
            error=None,
            resolved=None,
        ),
    ),
    (
        "foo.bar.not_found",
        "test",
        ResolveResult(
            status=Resolved.NOT_FOUND,
            fqcn="foo.bar.not_found",
            deprecations=[],
            tombstone=None,
            error=None,
            resolved=None,
        ),
    ),
    (
        "foo.bar.dead_chain_1",
        "lookup",
        ResolveResult(
            status=Resolved.TOMBSTONE,
            fqcn="foo.bar.dead_chain_3",
            deprecations=[
                (
                    "foo.bar.dead_chain_1",
                    RemovalData(
                        warning_text="this will be dead",
                        removal_version=None,
                        removal_date=None,
                    ),
                ),
            ],
            tombstone=RemovalData(
                warning_text="this is dead", removal_version=None, removal_date=None
            ),
            error=None,
            resolved=None,
        ),
    ),
    (
        "foo.bar.broken_chain_1",
        "lookup",
        ResolveResult(
            status=Resolved.REDIRECT_ERROR,
            fqcn="this-is-not-a-fqcn",
            deprecations=[],
            tombstone=None,
            error="Found redirect to non-FQCN this-is-not-a-fqcn",
            resolved=None,
        ),
    ),
    (
        "foo.bar.bam",
        "module",
        ResolveResult(
            status=Resolved.FOUND,
            fqcn="foo.bar.bam",
            deprecations=[],
            tombstone=None,
            error=None,
            resolved=File(
                fqcn="foo.bar.bam",
                python_file=Path("collections/foo/bar/plugins/modules/bam.py"),
                docs_candidates=[Path("collections/foo/bar/plugins/modules/bam.py")],
            ),
        ),
    ),
    (
        "foo.bar.baz",
        "module",
        ResolveResult(
            status=Resolved.FOUND,
            fqcn="foo.bar.baz",
            deprecations=[],
            tombstone=None,
            error=None,
            resolved=File(
                fqcn="foo.bar.baz",
                python_file=Path("collections/foo/bar/plugins/modules/baz.py"),
                docs_candidates=[Path("collections/foo/bar/plugins/modules/baz.py")],
            ),
        ),
    ),
    (
        "foo.bar.depr_bam",
        "module",
        ResolveResult(
            status=Resolved.FOUND,
            fqcn="foo.bar.bam",
            deprecations=[
                (
                    "foo.bar.depr_bam",
                    RemovalData(
                        warning_text="use bam directly",
                        removal_version="2.0.0",
                        removal_date=None,
                    ),
                ),
            ],
            tombstone=None,
            error=None,
            resolved=File(
                fqcn="foo.bar.bam",
                python_file=Path("collections/foo/bar/plugins/modules/bam.py"),
                docs_candidates=[Path("collections/foo/bar/plugins/modules/bam.py")],
            ),
        ),
    ),
    (
        "foo.bar.self_loop",
        "module",
        ResolveResult(
            status=Resolved.REDIRECT_ERROR,
            fqcn="foo.bar.self_loop",
            deprecations=[],
            tombstone=None,
            error="Detected circular redirect",
            resolved=None,
        ),
    ),
    (
        "foo.bar.loop_1",
        "module",
        ResolveResult(
            status=Resolved.REDIRECT_ERROR,
            fqcn="foo.bar.loop_1",
            deprecations=[
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
                (
                    "foo.bar.loop_1",
                    RemovalData(
                        warning_text="loop 1",
                        removal_version=None,
                        removal_date=None,
                    ),
                ),
            ],
            tombstone=None,
            error="Detected circular redirect",
            resolved=None,
        ),
    ),
    (
        "foo.bar.leave_chain_1",
        "module",
        ResolveResult(
            status=Resolved.COLLECTION_MISSING,
            fqcn="outside.here.meh",
            deprecations=[],
            tombstone=None,
            error="Collection outside.here not found",
            resolved=None,
        ),
    ),
    (
        "bar.baz.chain_2",
        "module",
        ResolveResult(
            status=Resolved.NOT_FOUND,
            fqcn="foo.bar.chain_4",
            deprecations=[
                (
                    "foo.bar.chain_3",
                    RemovalData(
                        warning_text="foo 3",
                        removal_version=None,
                        removal_date=None,
                    ),
                ),
            ],
            tombstone=None,
            error=None,
            resolved=None,
        ),
    ),
]


@pytest.mark.parametrize(
    "fqcn, plugin_type, expected_result",
    TEST_RESOLVE_DATA,
)
def test_resolve(
    fqcn: str,
    plugin_type: PluginType,
    expected_result: ResolveResult,
    routing_info: Mapping[str, CollectionRouting],
) -> None:
    complete_redirects(routing_info)
    result = resolve(routing_info, fqcn=fqcn, plugin_type=plugin_type)
    assert expected_result == result


def test_resolve_fail(routing_info: Mapping[str, CollectionRouting]) -> None:
    with pytest.raises(ValueError, match="^Expected FQCN, got 'a\\.b'$"):
        resolve(routing_info, fqcn="a.b", plugin_type="module")
