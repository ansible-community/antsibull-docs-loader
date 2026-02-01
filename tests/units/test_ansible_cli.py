# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test ansible-galaxy code.
"""

# pylint: disable=line-too-long
# pylint: disable=too-many-positional-arguments

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import pytest  # pylint: disable=import-error

from antsibull_docs_loader.ansible_cli import (
    ListingCollectionsError,
    ansible_galaxy_list_collections,
    locate_ansible_builtin_collection,
    simple_runner,
)
from antsibull_docs_loader.data import CollectionInfo

LOCATE_ANSIBLE_BUILTIN_COLLECTION_DATA: list[
    tuple[bytes, bytes, int, list[CollectionInfo]]
] = [
    (
        b"""ansible [core 2.21.0.dev0] (devel 29086acfa6) last updated 2026/01/30 21:47:54 (GMT +200)
  config file = None
  configured module search path = ['/home/me/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /home/me/ansible/lib/ansible
  ansible collection location = /home/me/collections-root:/home/me/.ansible/collections:/usr/share/ansible/collections
  executable location = /home/me/.local/bin/ansible
  python version = 3.14.2 (main, Jan  2 2026, 14:27:39) [GCC 15.2.1 20251112] (/usr/bin/python)
  jinja version = 3.1.6
  pyyaml version = 6.0.3 (with libyaml v0.2.5)
""",
        b"",
        0,
        [
            CollectionInfo(
                path=Path("/home/me/ansible/lib/ansible"),
                namespace="ansible",
                name="builtin",
                full_name="ansible.builtin",
                version="2.21.0.dev0",
                is_ansible_core=True,
            ),
        ],
    ),
    (
        b"""ansible-galaxy [core 2.21.0.dev0] (devel 29086acfa6) last updated 2026/01/30 21:47:54 (GMT +200)
  config file = None
  configured module search path = ['/home/me/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /home/me/ansible/lib/ansible
  ansible collection location = /home/me/collections-root:/home/me/.ansible/collections:/usr/share/ansible/collections
  executable location = /home/me/.local/bin/ansible
  python version = 3.14.2 (main, Jan  2 2026, 14:27:39) [GCC 15.2.1 20251112] (/usr/bin/python)
  jinja version = 3.1.6
  pyyaml version = 6.0.3 (with libyaml v0.2.5)
""",
        b"",
        0,
        [
            CollectionInfo(
                path=Path("/home/me/ansible/lib/ansible"),
                namespace="ansible",
                name="builtin",
                full_name="ansible.builtin",
                version="2.21.0.dev0",
                is_ansible_core=True,
            ),
        ],
    ),
    (
        b"""ansible 1.2.3
ansible python module location = foo
""",
        b"",
        0,
        [
            CollectionInfo(
                path=Path("foo"),
                namespace="ansible",
                name="builtin",
                full_name="ansible.builtin",
                version="1.2.3",
                is_ansible_core=True,
            ),
        ],
    ),
    (
        b"""ansible-playbook 1.2.3
ansible python module location = foo
""",
        b"",
        0,
        [
            CollectionInfo(
                path=Path("foo"),
                namespace="ansible",
                name="builtin",
                full_name="ansible.builtin",
                version="1.2.3",
                is_ansible_core=True,
            ),
        ],
    ),
]


@pytest.mark.parametrize(
    "stdout, stderr, rc, expected_collections",
    LOCATE_ANSIBLE_BUILTIN_COLLECTION_DATA,
)
def test_locate_ansible_builtin_collection(
    stdout: bytes, stderr: bytes, rc: int, expected_collections: list[CollectionInfo]
) -> None:
    def runner(
        args: list[str], *, env: dict[str, str] | None = None
    ) -> tuple[bytes, bytes, int]:
        assert args == ["ansible-galaxy", "--version"]
        assert env is None
        return stdout, stderr, rc

    collection_list = list(locate_ansible_builtin_collection(runner))
    assert collection_list == expected_collections


LOCATE_ANSIBLE_BUILTIN_COLLECTION_FAIL_DATA: list[tuple[bytes, bytes, int, str]] = [
    (
        b"Foo",
        b"",
        0,
        r"^Cannot extract module location path from ansible --version output: Foo$",
    ),
    (
        b"ansible python module location = foo",
        b"",
        0,
        r"^Cannot extract ansible-core version from ansible --version output:"
        r" ansible python module location = foo$",
    ),
    (
        b"ansible 1.2.3",
        b"",
        0,
        r"^Cannot extract module location path from ansible --version output: ansible 1.2.3$",
    ),
    (
        b"",
        b"",
        1,
        r"^Unexpected return code 1 when querying version. Standard error output: $",
    ),
]


@pytest.mark.parametrize(
    "stdout, stderr, rc, expected_error_matcher",
    LOCATE_ANSIBLE_BUILTIN_COLLECTION_FAIL_DATA,
)
def test_locate_ansible_builtin_collection_fail(
    stdout: bytes, stderr: bytes, rc: int, expected_error_matcher: str
) -> None:
    def runner(
        args: list[str], *, env: dict[str, str] | None = None
    ) -> tuple[bytes, bytes, int]:
        assert args == ["ansible-galaxy", "--version"]
        assert env is None
        return stdout, stderr, rc

    with pytest.raises(ListingCollectionsError, match=expected_error_matcher):
        list(locate_ansible_builtin_collection(runner))


ANSIBLE_GALAXY_LIST_COLLECTIONS_DATA: list[
    tuple[str | None, bool, bool, bytes, bytes, int, list[CollectionInfo]]
] = [
    (
        None,
        False,
        True,
        b"",
        b"BlablaNone of the provided paths were usable.Blabla",
        5,
        [],
    ),
    (
        "foo-bar",
        False,
        True,
        b"{}",
        b"",
        0,
        [],
    ),
    (
        "foo-bar",
        False,
        True,
        b"""{
"/foo": {
    "bar": {},
    "baz.bam": {},
    "foo.bar": {"version": "*"},
    "foo.bam": {"version": "1.2.3"},
    "baz.bar": {"version": 42}
}
        }""",
        b"",
        0,
        [
            CollectionInfo(
                path=Path("/foo/baz/bam"),
                namespace="baz",
                name="bam",
                full_name="baz.bam",
                version=None,
            ),
            CollectionInfo(
                path=Path("/foo/foo/bar"),
                namespace="foo",
                name="bar",
                full_name="foo.bar",
                version=None,
            ),
            CollectionInfo(
                path=Path("/foo/foo/bam"),
                namespace="foo",
                name="bam",
                full_name="foo.bam",
                version="1.2.3",
            ),
            CollectionInfo(
                path=Path("/foo/baz/bar"),
                namespace="baz",
                name="bar",
                full_name="baz.bar",
                version=None,
            ),
        ],
    ),
]


@pytest.mark.parametrize(
    "collections_path, only_pass_env_updates, expects_env,"
    " stdout, stderr, rc, expected_collections",
    ANSIBLE_GALAXY_LIST_COLLECTIONS_DATA,
)
def test_ansible_galaxy_list_collections(
    collections_path: str | None,
    only_pass_env_updates: bool,
    expects_env: bool,
    stdout: bytes,
    stderr: bytes,
    rc: int,
    expected_collections: list[CollectionInfo],
) -> None:
    def runner(
        args: list[str], *, env: dict[str, str] | None = None
    ) -> tuple[bytes, bytes, int]:
        assert args == ["ansible-galaxy", "collection", "list", "--format", "json"]
        assert (env is not None) == expects_env
        return stdout, stderr, rc

    collections = list(
        ansible_galaxy_list_collections(
            runner,
            collections_path=collections_path,
            only_pass_env_updates=only_pass_env_updates,
        )
    )
    assert collections == expected_collections


ANSIBLE_GALAXY_LIST_COLLECTIONS_FAIL_DATA: list[
    tuple[str | None, bool, bool, bytes, bytes, int, str]
] = [
    (
        None,
        False,
        True,
        b"",
        b"BlablaNone of the provided paths were usable.Blabla",
        2,
        r"^Unexpected return code 2 when listing collections\. Standard error output:"
        r" BlablaNone of the provided paths were usable\.Blabla$",
    ),
    (
        "foo-bar",
        False,
        True,
        b"{}",
        b"",
        5,
        r"^Unexpected return code 5 when listing collections\. Standard error output: $",
    ),
    (
        None,
        True,
        True,
        b"""{"/foo": {"bar": {},}}""",
        b"",
        0,
        r"^Error while loading collection list: Illegal trailing comma"
        r" before end of object: line 1 column 20 \(char 19\)$",
    ),
    (
        None,
        True,
        True,
        b"""""",
        b"ABCerror: argument COLLECTION_ACTION: invalid choice: 'list'XYZ",
        2,
        r"^ansible-galaxy does not support 'collection list' command$",
    ),
]


@pytest.mark.parametrize(
    "collections_path, only_pass_env_updates, expects_env,"
    " stdout, stderr, rc, expected_error_matcher",
    ANSIBLE_GALAXY_LIST_COLLECTIONS_FAIL_DATA,
)
def test_ansible_galaxy_list_collections_fail(
    collections_path: str | None,
    only_pass_env_updates: bool,
    expects_env: bool,
    stdout: bytes,
    stderr: bytes,
    rc: int,
    expected_error_matcher: str,
) -> None:
    def runner(
        args: list[str], *, env: dict[str, str] | None = None
    ) -> tuple[bytes, bytes, int]:
        assert args == ["ansible-galaxy", "collection", "list", "--format", "json"]
        assert (env is not None) == expects_env
        return stdout, stderr, rc

    with pytest.raises(ListingCollectionsError, match=expected_error_matcher):
        print(
            list(
                ansible_galaxy_list_collections(
                    runner,
                    collections_path=collections_path,
                    only_pass_env_updates=only_pass_env_updates,
                )
            )
        )


ANSIBLE_GALAXY_LIST_COLLECTIONS_COMPAT_DATA: list[
    tuple[str | None, bool, bool, bytes, bytes, int, list[CollectionInfo]]
] = [
    (
        None,
        False,
        True,
        b"",
        b"BlablaNone of the provided paths were usable.Blabla",
        5,
        [],
    ),
    (
        "foo-bar",
        False,
        True,
        b"{}",
        b"",
        0,
        [],
    ),
    (
        "foo-bar",
        False,
        True,
        b"""{
# /foo
Collection                               Version    
---------------------------------------- -----------
bar                                      *      
baz.bam                                  *      
foo.bar                                  *      
foo.bam                                  1.2.3      
baz.bar                                  *      
        """,
        b"",
        0,
        [
            CollectionInfo(
                path=Path("/foo/baz/bam"),
                namespace="baz",
                name="bam",
                full_name="baz.bam",
                version=None,
            ),
            CollectionInfo(
                path=Path("/foo/foo/bar"),
                namespace="foo",
                name="bar",
                full_name="foo.bar",
                version=None,
            ),
            CollectionInfo(
                path=Path("/foo/foo/bam"),
                namespace="foo",
                name="bam",
                full_name="foo.bam",
                version="1.2.3",
            ),
            CollectionInfo(
                path=Path("/foo/baz/bar"),
                namespace="baz",
                name="bar",
                full_name="baz.bar",
                version=None,
            ),
        ],
    ),
    (
        None,
        True,
        True,
        # This is broken output and should never happen.
        b"""{
Collection                               Version    
---------------------------------------- -----------
bar                                      *      
baz.bam                                  *      
foo.bar                                  *      
foo.bam                                  1.2.3      
baz.bar                                  *      
        """,
        b"",
        0,
        [],
    ),
]


@pytest.mark.parametrize(
    "collections_path, only_pass_env_updates, expects_env,"
    " stdout, stderr, rc, expected_collections",
    ANSIBLE_GALAXY_LIST_COLLECTIONS_COMPAT_DATA,
)
def test_ansible_galaxy_list_collections_compat(
    collections_path: str | None,
    only_pass_env_updates: bool,
    expects_env: bool,
    stdout: bytes,
    stderr: bytes,
    rc: int,
    expected_collections: list[CollectionInfo],
) -> None:
    counter = [0]

    def runner(
        args: list[str], *, env: dict[str, str] | None = None
    ) -> tuple[bytes, bytes, int]:
        counter[0] += 1
        if counter[0] == 1:
            assert args == ["ansible-galaxy", "collection", "list", "--format", "json"]
            assert (env is not None) == expects_env
            return b"", b"XYZerror: unrecognized arguments: --formatABC", 2
        assert args == ["ansible-galaxy", "collection", "list"]
        assert (env is not None) == expects_env
        return stdout, stderr, rc

    collections = list(
        ansible_galaxy_list_collections(
            runner,
            collections_path=collections_path,
            only_pass_env_updates=only_pass_env_updates,
        )
    )
    assert collections == expected_collections
    assert counter[0] == 2


ANSIBLE_GALAXY_LIST_COLLECTIONS_COMPAT_FAIL_DATA: list[
    tuple[str | None, bool, bool, bytes, bytes, int, str]
] = [
    (
        None,
        False,
        True,
        b"",
        b"BlablaNone of the provided paths were usable.Blabla",
        2,
        r"^Unexpected return code 2 when listing collections\."
        r" Standard error output: BlablaNone of the provided paths were usable\.Blabla$",
    ),
]


@pytest.mark.parametrize(
    "collections_path, only_pass_env_updates, expects_env,"
    " stdout, stderr, rc, expected_error_matcher",
    ANSIBLE_GALAXY_LIST_COLLECTIONS_COMPAT_FAIL_DATA,
)
def test_ansible_galaxy_list_collections_compat_fail(
    collections_path: str | None,
    only_pass_env_updates: bool,
    expects_env: bool,
    stdout: bytes,
    stderr: bytes,
    rc: int,
    expected_error_matcher: str,
) -> None:
    counter = [0]

    def runner(
        args: list[str], *, env: dict[str, str] | None = None
    ) -> tuple[bytes, bytes, int]:
        counter[0] += 1
        if counter[0] == 1:
            assert args == ["ansible-galaxy", "collection", "list", "--format", "json"]
            assert (env is not None) == expects_env
            return b"", b"XYZerror: unrecognized arguments: --formatABC", 2
        assert args == ["ansible-galaxy", "collection", "list"]
        assert (env is not None) == expects_env
        return stdout, stderr, rc

    with pytest.raises(ListingCollectionsError, match=expected_error_matcher):
        print(
            list(
                ansible_galaxy_list_collections(
                    runner,
                    collections_path=collections_path,
                    only_pass_env_updates=only_pass_env_updates,
                )
            )
        )
    assert counter[0] == 2


def test_simple_runner() -> None:
    with mock.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["foo", "bar"], returncode=23, stdout=b"stdout", stderr=b"stderr"
        ),
    ) as m:
        assert simple_runner(["foo", "bar"]) == (b"stdout", b"stderr", 23)

    m.assert_called_once_with(
        ["foo", "bar"], env=None, capture_output=True, check=False
    )
