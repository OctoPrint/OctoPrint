import contextlib
import dataclasses
import logging
import os.path
import tarfile
import tempfile
import zipfile
from collections.abc import Generator
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


@dataclasses.dataclass
class InstallPreparationResult:
    path: str
    args: list[str] = dataclasses.field(default_factory=list)


@contextlib.contextmanager
def prepare_install(
    install_arg: str, log: callable = None
) -> Generator[InstallPreparationResult, None, None]:
    from octoprint.util.net import download_file

    if log is None:

        def log(*args):
            pass

    folder = None
    pip_args = []

    try:
        if install_arg.startswith("https://") or install_arg.startswith("http://"):
            # we download this first and check if we need to add --no-build-isolation
            log(f"Downloading {install_arg}...")
            folder = tempfile.TemporaryDirectory()
            install_arg = download_file(install_arg, folder.name)

            if is_pre_pep517_plugin_package(install_arg):
                pip_args += PRE_PEP517_PIP_ARGS

        yield InstallPreparationResult(path=install_arg, args=pip_args)
    finally:
        if folder is not None:
            folder.cleanup()
