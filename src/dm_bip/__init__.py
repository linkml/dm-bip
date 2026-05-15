"""dm-bip package."""

import os
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"  # pragma: no cover

# In containers without .git, importlib_metadata returns 0.0.0.
# Fall back to the build arg injected as an env var.
if __version__ == "0.0.0":
    __version__ = os.environ.get("DM_BIP_VERSION", "").strip() or __version__
