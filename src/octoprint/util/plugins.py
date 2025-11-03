import logging
import os.path
import tarfile
import zipfile
from typing import Union

import filetype

PRE_PEP517_PIP_ARGS = ["--use-pep517", "--no-build-isolation"]


def is_pre_pep517_plugin_package(path):
    if not filetype.is_archive(path):
        return False

    kind = filetype.guess(path)

    try:
        if kind.mime == "application/zip":
            with zipfile.ZipFile(path, mode="r") as archive:
                try:
                    try:
                        setup_py = archive.getinfo("setup.py")
                    except KeyError:
                        # check for a single contained dir, indicated by a common prefix
                        files = archive.namelist()
                        prefix = os.path.commonprefix(
                            files
                        )  # e.g. "OctoPrint-RequestSpinner-master/"
                        if not prefix:
                            raise
                        setup_py = archive.getinfo(prefix + "setup.py")

                    with archive.open(setup_py, mode="r") as f:
                        data = f.readlines()
                    return has_legacy_octoprint_setuptools_dependency(b"\n".join(data))

                except KeyError:
                    # no setup.py contained
                    pass

        elif tarfile.is_tarfile(path):
            with tarfile.open(path, mode="r") as archive:
                try:
                    try:
                        setup_py = archive.getmember("setup.py")
                    except KeyError:
                        # check for a single contained dir, indicated by a common prefix
                        files = archive.getnames()
                        prefix = os.path.commonprefix(
                            files
                        )  # e.g. "OctoPrint-RequestSpinner-master"
                        if not prefix:
                            raise
                        setup_py = archive.getmember(prefix + "/setup.py")

                    with archive.extractfile(setup_py.name) as f:
                        setup_py_bytes = f.readlines()
                    return has_legacy_octoprint_setuptools_dependency(
                        b"\n".join(setup_py_bytes)
                    )

                except KeyError:
                    # no setup.py contained
                    pass

    except Exception:
        logging.getLogger(__name__).exception(f"Error while inspecting {path}")

    # if we reach this point, we didn't find any hint that this is legacy code
    return False


def has_legacy_octoprint_setuptools_dependency(
    data: Union[bytes, str], encoding="utf-8"
) -> bool:
    if isinstance(data, str):
        data = data.encode(encoding)
    return (
        b"import octoprint_setuptools" in data
        or b"octoprint_setuptools.create_plugin_setup_parameters(" in data
    )
