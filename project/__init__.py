"""kubeconfig_updater package."""

# Use vendored dependencies when present (no pip install needed on target)
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
_vendor = _root / "vendor"
if _vendor.is_dir():
    sys.path.insert(0, str(_vendor))

__all__ = []
