# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Use ansible-galaxy to list collections.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import typing as t
from collections.abc import Iterator
from pathlib import Path

from .data import CollectionInfo

_ANSIBLE_VERSION_NEW = re.compile(
    r"^ansible(?:-[a-z0-9]+)? \[(?:core|base) ([0-9][^\]]+)\]"
)
_ANSIBLE_VERSION_OLD = re.compile(r"^ansible(?:-[a-z0-9]+)? ([0-9][^\s]+)")

_COLLECTIONS_PATH_ENV_VAR = "ANSIBLE_COLLECTIONS_PATH"
_COLLECTIONS_PATH_ENV_VAR_COMPAT = "ANSIBLE_COLLECTIONS_PATHS"


class Runner(t.Protocol):
    """
    Function that executes a command and returns a tuple (stdout, stderr, rc).
    """

    def __call__(
        self, args: list[str], *, env: dict[str, str] | None = None
    ) -> tuple[bytes, bytes, int]: ...


def simple_runner(
    args: list[str], *, env: dict[str, str] | None = None
) -> tuple[bytes, bytes, int]:
    """
    Simple subprocess.run() based function implementing the Runner protocol.
    """
    p = subprocess.run(args, env=env, capture_output=True, check=False)
    return p.stdout, p.stderr, p.returncode


class ListingCollectionsError(ValueError):
    """
    Indicates that listing collections failed.
    """


class Ansible29Error(ListingCollectionsError):
    """
    Indicates that collections cannot be listed since Ansible 2.9 (or before) do not support this.
    """


def _extract_ansible_builtin_collection(stdout: str) -> CollectionInfo:
    path: Path | None = None
    version: str | None = None
    for line in stdout.splitlines():
        if line.strip().startswith("ansible python module location"):
            path = Path(line.split("=", 2)[1].strip())
        for regex in (_ANSIBLE_VERSION_NEW, _ANSIBLE_VERSION_OLD):
            match = regex.match(line)
            if match:
                version = match.group(1)
                break
    if path is None:
        raise ListingCollectionsError(
            f"Cannot extract module location path from ansible --version output: {stdout}"
        )
    if version is None:
        raise ListingCollectionsError(
            f"Cannot extract ansible-core version from ansible --version output: {stdout}"
        )
    return CollectionInfo(
        path=path,
        namespace="ansible",
        name="builtin",
        full_name="ansible.builtin",
        version=version,
        is_ansible_core=True,
    )


def locate_ansible_builtin_collection(runner: Runner) -> list[CollectionInfo]:
    """
    Use 'ansible-galaxy --version' to locate ansible.builtin
    (and potentially other collections included with ansible-core).
    """
    stdout, stderr, rc = runner(["ansible-galaxy", "--version"])
    if rc != 0:
        raise ListingCollectionsError(
            f"Unexpected return code {rc} when querying version."
            f" Standard error output: {stderr.decode('utf-8')}"
        )
    ansible_builtin = _extract_ansible_builtin_collection(stdout.decode("utf-8"))
    result = [ansible_builtin]
    # TODO: look for more in: ansible_builtin.path / "_internal" / "ansible_collections"
    return result


def _yield_collection(
    collection_name: str, collection_version: t.Any, root: Path
) -> Iterator[CollectionInfo]:
    parts = collection_name.split(".", 2)
    if len(parts) != 2:
        return
    namespace, name = parts
    version = (
        collection_version
        if isinstance(collection_version, str) and collection_version != "*"
        else None
    )
    yield CollectionInfo(
        path=root / namespace / name,
        namespace=namespace,
        name=name,
        full_name=collection_name,
        version=version,
    )


def _ansible_galaxy_list_collections_compat(
    runner: Runner, *, env: dict[str, str] | None
) -> Iterator[CollectionInfo]:
    # Handle ansible-base 2.10 that does not know about '--format json'.
    stdout, stderr, rc = runner(["ansible-galaxy", "collection", "list"], env=env)
    if rc == 5 and b"None of the provided paths were usable." in stderr:
        # Due to a bug in ansible-galaxy collection list, ansible-galaxy
        # fails with an error if no collection can be found.
        return
    if rc != 0:
        raise ListingCollectionsError(
            f"Unexpected return code {rc} when listing collections."
            f" Standard error output: {stderr.decode('utf-8')}"
        )
    root: Path | None = None
    for line in stdout.decode("utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            continue
        if parts[0] == "#":
            root = Path(parts[1])
        elif root is not None:
            yield from _yield_collection(parts[0], parts[1].strip(), root)


def _prepare_env(
    *,
    collections_path: str | None,
    only_pass_env_updates: bool = False,
    compat: bool = False,
) -> dict[str, str] | None:
    env: dict[str, str] = {} if only_pass_env_updates else os.environ.copy()
    env.update(
        {
            "ANSIBLE_ACTION_PLUGINS": "/dev/null",
            "ANSIBLE_CACHE_PLUGINS": "/dev/null",
            "ANSIBLE_CALLBACK_PLUGINS": "/dev/null",
            "ANSIBLE_CLICONF_PLUGINS": "/dev/null",
            "ANSIBLE_CONNECTION_PLUGINS": "/dev/null",
            "ANSIBLE_FILTER_PLUGINS": "/dev/null",
            "ANSIBLE_HTTPAPI_PLUGINS": "/dev/null",
            "ANSIBLE_INVENTORY_PLUGINS": "/dev/null",
            "ANSIBLE_LOOKUP_PLUGINS": "/dev/null",
            "ANSIBLE_LIBRARY": "/dev/null",
            "ANSIBLE_MODULE_UTILS": "/dev/null",
            "ANSIBLE_NETCONF_PLUGINS": "/dev/null",
            "ANSIBLE_ROLES_PATH": "/dev/null",
            "ANSIBLE_STRATEGY_PLUGINS": "/dev/null",
            "ANSIBLE_TERMINAL_PLUGINS": "/dev/null",
            "ANSIBLE_TEST_PLUGINS": "/dev/null",
            "ANSIBLE_VARS_PLUGINS": "/dev/null",
            "ANSIBLE_DOC_FRAGMENT_PLUGINS": "/dev/null",
        }
    )
    if collections_path:
        env["ANSIBLE_COLLECTIONS_PATH"] = collections_path
        if compat:
            env["_COLLECTIONS_PATH_ENV_VAR_COMPAT"] = collections_path
    return env if env or not only_pass_env_updates else None


def ansible_galaxy_list_collections(
    runner: Runner,
    *,
    collections_path: str | None = None,
    only_pass_env_updates: bool = False,
) -> Iterator[CollectionInfo]:
    """
    Use 'ansible-galaxy collection list' to list all collections.
    """
    try:
        stdout, stderr, rc = runner(
            ["ansible-galaxy", "collection", "list", "--format", "json"],
            env=_prepare_env(
                collections_path=collections_path,
                only_pass_env_updates=only_pass_env_updates,
            ),
        )
        if (
            rc == 2
            and b"error: argument COLLECTION_ACTION: invalid choice: 'list'" in stderr
        ):
            # This happens for Ansible 2.9, where there is no 'list' command at all.
            # Avoid using ansible-galaxy from the virtual environment, and hope it is
            # installed somewhere more globally...
            raise Ansible29Error(
                "ansible-galaxy does not support 'collection list' command"
            )
        if rc == 2 and b"error: unrecognized arguments: --format" in stderr:
            yield from _ansible_galaxy_list_collections_compat(
                runner,
                env=_prepare_env(
                    collections_path=collections_path,
                    only_pass_env_updates=only_pass_env_updates,
                    compat=True,
                ),
            )
            return
        if rc == 5 and b"None of the provided paths were usable." in stderr:
            # Due to a bug in ansible-galaxy collection list, ansible-galaxy
            # fails with an error if no collection can be found.
            # (This will be fixed in ansible-core 2.21; see
            # https://github.com/ansible/ansible/issues/73127.)
            return
        if rc != 0:
            raise ListingCollectionsError(
                f"Unexpected return code {rc} when listing collections."
                f" Standard error output: {stderr.decode('utf-8')}"
            )
        data = json.loads(stdout)
        for collections_root_path, collections in data.items():
            root = Path(collections_root_path)
            for collection_name, collection_data in collections.items():
                yield from _yield_collection(
                    collection_name, collection_data.get("version"), root
                )
    except ListingCollectionsError:
        raise
    except Exception as exc:
        raise ListingCollectionsError(
            f"Error while loading collection list: {exc}"
        ) from exc


__all__ = ("ansible_galaxy_list_collections", "locate_ansible_builtin_collection")
