# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test ansible-galaxy code.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # pylint: disable=import-error

from antsibull_docs_loader.data import (
    CollectionInfo,
    CollectionInfos,
)


def test_CollectionInfos_build() -> None:
    ci = CollectionInfos.build([])
    assert ci.ansible_core is None
    assert (
        ci.collections == {}  # pylint: disable=use-implicit-booleaness-not-comparison
    )

    core_1 = CollectionInfo(
        path=Path("/core-1"),
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version="1.2.3",
        is_ansible_core=True,
    )
    core_1_not_real = CollectionInfo(
        path=Path("/core-1"),
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version="1.2.3",
        is_ansible_core=False,
    )
    core_2 = CollectionInfo(
        path=Path("/core-2"),
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version="3.2.1",
        is_ansible_core=True,
    )
    core_2_not_real = CollectionInfo(
        path=Path("/core-2"),
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version="3.2.1",
        is_ansible_core=False,
    )
    fake_core = CollectionInfo(
        path=Path("/fake-core"),
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version="3.2.1",
        is_ansible_core=True,
    )

    with pytest.raises(
        ValueError,
        match=r"^Found more than one collection claiming to be ansible-core$",
    ):
        CollectionInfos.build([core_1, core_2])

    with pytest.raises(
        ValueError,
        match=r"^Ansible-core has wrong full name 'foo\.bar'$",
    ):
        CollectionInfos.build([fake_core])

    ci = CollectionInfos.build([core_1_not_real, core_2])
    assert ci.ansible_core is core_2
    assert ci.collections == {"ansible.builtin": core_2}

    ci = CollectionInfos.build([core_1, core_2_not_real])
    assert ci.ansible_core is core_1
    assert ci.collections == {"ansible.builtin": core_1}

    coll_1 = CollectionInfo(
        path=Path("/coll-1"),
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version="1.2.3",
        is_ansible_core=False,
    )
    coll_2 = CollectionInfo(
        path=Path("/coll-1"),
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version="3.2.1",
        is_ansible_core=False,
    )

    ci = CollectionInfos.build([coll_1, coll_2])
    assert ci.ansible_core is None
    assert ci.collections == {"foo.bar": coll_1}

    ci = CollectionInfos.build([coll_2, coll_1])
    assert ci.ansible_core is None
    assert ci.collections == {"foo.bar": coll_2}
