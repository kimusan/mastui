from importlib import metadata
from pathlib import Path
import tomllib
import logging

log = logging.getLogger(__name__)


def _read_pyproject_version() -> str | None:
    try:
        root = Path(__file__).resolve().parents[1]
        data = tomllib.loads((root / "pyproject.toml").read_text())
        return data["tool"]["poetry"]["version"]
    except Exception as e:
        log.debug(f"Could not read version from pyproject: {e}")
        return None


def _detect_version() -> str:
    try:
        return metadata.version("mastui")
    except metadata.PackageNotFoundError:
        pass
    return _read_pyproject_version() or "0.0.0"


__version__ = _detect_version()
