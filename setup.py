import os

import setuptools  # noqa: F401,E402


def copy_files_build_py_factory(files, baseclass):
    class copy_files_build_py(baseclass):
        files = {}

        def run(self):
            print("RUNNING copy_files_build_py")
            if not self.dry_run:
                import shutil

                for directory, files in self.files.items():
                    target_dir = os.path.join(self.build_lib, directory)
                    self.mkpath(target_dir)

                    for entry in files:
                        if isinstance(entry, tuple):
                            if len(entry) != 2:
                                continue
                            source, dest = entry[0], os.path.join(target_dir, entry[1])
                        else:
                            source = entry
                            dest = os.path.join(target_dir, source)

                        print("Copying {} to {}".format(source, dest))
                        shutil.copy2(source, dest)

            baseclass.run(self)

    return type(copy_files_build_py)(
        copy_files_build_py.__name__, (copy_files_build_py,), {"files": files}
    )


def get_version_and_cmdclass(pkg_path):
    import os
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("version", os.path.join(pkg_path, "_version.py"))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    data = module.get_data()
    return data["version"], module.get_cmdclass(pkg_path)


def get_cmdclass(cmdclass):
    from setuptools.command.build_py import build_py as _build_py

    cmdclass["build_py"] = copy_files_build_py_factory(
        {
            "octoprint/templates/_data": [
                "AUTHORS.md",
                "SUPPORTERS.md",
                "THIRDPARTYLICENSES.md",
            ]
        },
        cmdclass.get("build_py", _build_py),
    )

    return cmdclass


if __name__ == "__main__":
    version, cmdclass = get_version_and_cmdclass(os.path.join("src", "octoprint"))
    setuptools.setup(
        version=version,
        license="AGPL-3.0-or-later",
        cmdclass=get_cmdclass(cmdclass),
    )
