"""
This "python package" doesn't actually install. This is intentional. It is merely
used to figure out some information about the environment a specific pip call
is running under (installation dir, whether it belongs to a virtual environment,
whether the install location is writable by the current user), and for that it
only needs to be invoked by pip, the pip call doesn't have to be successful
however.

Any output (STDOUT and STDERR) produced by this script is captured by pip and,
until pip v19, printed via its STDOUT, from pip v20 on, via its STDERR. The
parsing script hence needs to capture both to support all pip versions.
"""

import os
import sys
from distutils.command.install import install as cmd_install
from distutils.dist import Distribution

cmd = cmd_install(Distribution())
cmd.finalize_options()

install_dir = cmd.install_lib
virtual_env = hasattr(sys, "real_prefix") or (
    hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
)
writable = os.access(install_dir, os.W_OK)

lines = [
    f"PIP_INSTALL_DIR={install_dir}",
    f"PIP_VIRTUAL_ENV={virtual_env}",
    f"PIP_WRITABLE={writable}",
]

# write to stdout
for line in lines:
    print(line, file=sys.stdout)

sys.stdout.flush()

# fail intentionally
sys.exit(-1)
