"""dm-bip package."""

import os

import importlib_metadata

try:
    __version__ = importlib_metadata.version(__name__)
except importlib_metadata.PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"  # pragma: no cover

# In containers, poetry-dynamic-versioning has no .git dir so __version__ is 0.0.0.
# Fall back to the build arg injected as an env var.
if __version__ == "0.0.0":
    __version__ = os.environ.get("DM_BIP_VERSION", "").strip() or __version__
