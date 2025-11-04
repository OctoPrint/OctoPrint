import logging
import os.path
import tarfile
import zipfile
from typing import Optional, Union

import filetype

PRE_PEP517_PIP_ARGS = ["--use-pep517", "--no-build-isolation"]


def _get_zipinfo(archive: zipfile.ZipFile, name: str) -> Optional[zipfile.ZipInfo]:
    try:
        try:
            return archive.getinfo(name)
        except KeyError:
            # check for a single contained dir, indicated by a common prefix
            files = archive.namelist()
            prefix = os.path.commonprefix(
                files
            )  # e.g. "OctoPrint-RequestSpinner-master/"
            if not prefix:
                raise

            return archive.getinfo(prefix + name)

    except KeyError:
        # not found
        pass

    return None


def _get_tarinfo(archive: tarfile.TarFile, name: str) -> Optional[tarfile.TarInfo]:
    try:
        try:
            return archive.getmember(name)
        except KeyError:
            # check for a single contained dir, indicated by a common prefix
            files = archive.getnames()
            prefix = os.path.commonprefix(files)  # e.g. "OctoPrint-RequestSpinner-master"
            if not prefix:
                raise
            return archive.getmember(f"{prefix}/{name}")

    except KeyError:
        # not found
        pass

    return None


def is_pre_pep517_plugin_package(path: str) -> bool:
    if not filetype.is_archive(path):
        return False

    if path.endswith(".whl"):
        return False

    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, mode="r") as archive:
                if _get_zipinfo(archive, "pyproject.toml"):
                    return False

                setup_py = _get_zipinfo(archive, "setup.py")
                if not setup_py:
                    return False

                with archive.open(setup_py, mode="r") as f:
                    data = f.readlines()
                return has_legacy_octoprint_setuptools_dependency(b"\n".join(data))

        elif tarfile.is_tarfile(path):
            with tarfile.open(path, mode="r") as archive:
                if _get_tarinfo(archive, "pyproject.toml"):
                    return False

                setup_py = _get_tarinfo(archive, "setup.py")
                if not setup_py:
                    return False

                with archive.extractfile(setup_py.name) as f:
                    setup_py_bytes = f.readlines()
                return has_legacy_octoprint_setuptools_dependency(
                    b"\n".join(setup_py_bytes)
                )

    except Exception:
        logging.getLogger(__name__).exception(f"Error while inspecting {path}")

    # if we reach this point, we didn't find any hint that this is legacy code
    return False


def has_legacy_octoprint_setuptools_dependency(
    data: Union[bytes, str], encoding="utf-8"
) -> bool:
    if isinstance(data, str):
        data = data.encode(encoding)
    return b"octoprint_setuptools" in data
