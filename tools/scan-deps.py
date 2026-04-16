import os

import requests
from packaging.requirements import Requirement
from packaging.version import parse as parse_version
from tqdm import tqdm

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11


PYPI_SIMPLE = "https://pypi.org/simple/{package}/"
PYPI_JSON = "https://pypi.org/pypi/{package}/{version}/json"


def read_pyproject_toml(path: str) -> dict:
    with open(path, mode="rb") as f:
        return tomllib.load(f)


def get_versions(package: str) -> list[str]:
    resp = requests.get(
        PYPI_SIMPLE.format(package=package),
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    )
    resp.raise_for_status()

    def safe_parse_version(version):
        try:
            return parse_version(version)
        except ValueError:
            return None

    data = resp.json()
    return list(
        filter(
            lambda x: x and not x.is_prerelease and not x.is_devrelease,
            (safe_parse_version(x) for x in data.get("versions", [])),
        )
    )


def is_yanked(package: str, version: str) -> bool:
    resp = requests.get(PYPI_JSON.format(package=package, version=version))
    resp.raise_for_status()

    data = resp.json()
    return data.get("info", {}).get("yanked", False)


def scan_deps(requires: list[str]):
    from collections import namedtuple

    Update = namedtuple("Update", ["name", "spec", "current", "latest"])
    update_lower_bounds = []
    update_bounds = []

    reqs = [Requirement(r) for r in requires]
    longest_name = max([len(r.name) for r in reqs]) + 1
    format_str = f"{{package:<{longest_name}}}"

    with tqdm(reqs, unit="pkgs") as t:
        for r in t:
            package = r.name
            t.set_description(format_str.format(package=package))

            versions = get_versions(package)
            if not versions:
                # no versions found for package
                continue

            lower = None
            for spec in r.specifier._specs:
                if spec.operator == ">=":
                    lower = spec.version
                    break

            latest = versions[-1]
            if lower and parse_version(lower) <= latest:
                # lower bound is still latest, nothing to do
                continue

            # make sure latest version is not yanked, fetch latest not-yanked if it is
            if is_yanked(package, str(latest)):
                for version in reversed(versions[:-1]):
                    if not is_yanked(package, str(version)):
                        latest = version
                        break
                else:
                    # nothing found that isn't yanked
                    continue

            update = Update(package, str(r), lower, latest)

            if str(latest) not in r.specifier:
                update_bounds.append(update)
            elif lower and parse_version(lower) < latest:
                update_lower_bounds.append(update)

    def print_update(update):
        print(
            f"{update.spec}: latest {update.latest}, pypi: https://pypi.org/project/{update.name}/"
        )

    if update_lower_bounds:
        print("")
        print("The following dependencies can get their lower bounds updated:")
        print("")
        for update in update_lower_bounds:
            print_update(update)

    if update_bounds:
        print("")
        print("The following dependencies should get looked at for a full update:")
        print("")
        for update in update_bounds:
            print_update(update)


def main():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    )
    pyproject = read_pyproject_toml(path)

    deps = [*pyproject.get("project", {}).get("dependencies", [])]
    for _, optional in (
        pyproject.get("project", {}).get("optional-dependencies", {}).items()
    ):
        deps += optional

    print(f"Scanning {len(deps)} dependencies...")
    scan_deps(deps)


if __name__ == "__main__":
    main()
