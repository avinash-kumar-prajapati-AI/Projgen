# projgen/core.py
"""
Core logic for projgen: parsing config files and scaffolding project structures.
Supports JSON and YAML input formats.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional YAML support — graceful degradation if PyYAML is not installed
# ---------------------------------------------------------------------------
try:
    import yaml  # type: ignore

    _YAML_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    _YAML_AVAILABLE = False

# Files that legitimately have no extension
_EXTENSIONLESS_FILES: frozenset[str] = frozenset(
    {
        "Dockerfile",
        "Makefile",
        "LICENSE",
        "README",
        "NOTICE",
        "CODEOWNERS",
        "Procfile",
        "Vagrantfile",
        "Jenkinsfile",
        "Brewfile",
    }
)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> dict[str, Any]:
    """
    Load a project-structure config from *path*.

    Supported formats
    -----------------
    * ``.json``  – always available
    * ``.yaml`` / ``.yml`` – requires ``PyYAML`` (``pip install projgen[yaml]``)

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file extension is unsupported or PyYAML is missing for YAML files.
    json.JSONDecodeError / yaml.YAMLError
        If the file content is malformed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".json":
        logger.debug("Loading JSON config: %s", path)
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    if suffix in {".yaml", ".yml"}:
        if not _YAML_AVAILABLE:
            raise ValueError(
                "PyYAML is required to read YAML config files.\n"
                "Install it with:  pip install projgen[yaml]"
            )
        logger.debug("Loading YAML config: %s", path)
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            if not isinstance(data, dict):
                raise ValueError(
                    f"Expected a YAML mapping at the top level, got {type(data).__name__}."
                )
            return data

    raise ValueError(
        f"Unsupported config format: '{suffix}'. "
        "Supported formats are: .json, .yaml, .yml"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_entry(entry: dict[str, Any], index: int) -> None:
    """
    Validate a single structure entry.

    Expected keys
    -------------
    ``name``  – relative path string  (e.g. ``"app/api/v1"``)
    ``level`` – nesting depth (1-based integer)
    ``type``  – ``"file"`` or ``"folder"``

    Raises
    ------
    TypeError
        If *entry* is not a dict or required keys are missing / wrong type.
    ValueError
        If semantic constraints are violated (level mismatch, bad extension, …).
    """
    if not isinstance(entry, dict):
        raise TypeError(f"Entry #{index} must be a mapping/dict, got {type(entry).__name__}.")

    missing = [k for k in ("name", "level", "type") if k not in entry]
    if missing:
        raise TypeError(f"Entry #{index} is missing required key(s): {missing}.")

    name: str = entry["name"]
    level: Any = entry["level"]
    entry_type: str = entry["type"]

    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Entry #{index}: 'name' must be a non-empty string.")

    # Normalise path separators
    name = name.replace("\\", "/").strip("/")

    if not isinstance(level, int) or level < 1:
        raise ValueError(f"Entry #{index} ('{name}'): 'level' must be a positive integer.")

    expected_level = name.count("/") + 1
    if level != expected_level:
        raise ValueError(
            f"Entry #{index} ('{name}'): level mismatch. "
            f"Path depth implies level {expected_level}, but 'level' is {level}."
        )

    if entry_type not in {"file", "folder"}:
        raise ValueError(
            f"Entry #{index} ('{name}'): 'type' must be 'file' or 'folder', got '{entry_type}'."
        )

    base_name = Path(name).name
    has_extension = bool(Path(name).suffix)

    if entry_type == "file":
        if (
            not has_extension
            and not base_name.startswith(".")
            and base_name not in _EXTENSIONLESS_FILES
        ):
            raise ValueError(
                f"Entry #{index}: File '{name}' has no extension and is not a known "
                f"extensionless file. If intentional, add '{base_name}' to the allow-list."
            )

    elif entry_type == "folder" and has_extension:
        raise ValueError(
            f"Entry #{index}: Folder '{name}' should not have a file extension."
        )


def validate_structure(data: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """
    Validate the top-level config dict and all its entries.

    Returns
    -------
    (project_name, structure)
        Validated project name and list of entries.

    Raises
    ------
    ValueError / TypeError
        On any validation failure.
    """
    if not isinstance(data, dict):
        raise TypeError(f"Config must be a mapping, got {type(data).__name__}.")

    project_name: str = data.get("project_name", "").strip()
    if not project_name:
        raise ValueError("Config is missing a non-empty 'project_name' field.")

    structure = data.get("project-structure")
    if structure is None:
        raise ValueError("Config is missing the 'project-structure' key.")
    if not isinstance(structure, list):
        raise TypeError(
            f"'project-structure' must be a list, got {type(structure).__name__}."
        )
    if not structure:
        raise ValueError("'project-structure' list is empty – nothing to create.")

    for i, entry in enumerate(structure, start=1):
        validate_entry(entry, i)

    return project_name, structure


# ---------------------------------------------------------------------------
# File-system operations
# ---------------------------------------------------------------------------

def _create_entry(base_path: Path, entry: dict[str, Any]) -> None:
    """Create a single file or folder under *base_path*."""
    # Normalise separators so Windows paths work too
    rel = entry["name"].replace("\\", "/").strip("/")
    entry_path = base_path / rel

    if entry["type"] == "folder":
        entry_path.mkdir(parents=True, exist_ok=True)
        logger.debug("  [dir]  %s", entry_path)
    else:
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.touch(exist_ok=True)
        logger.debug("  [file] %s", entry_path)


def _resolve_project_name(project_name: str, output_dir: Path) -> Path:
    """
    Return a Path for the new project directory.

    If *project_name* already exists under *output_dir* this function:
    1. Asks the user for a new name, or
    2. Auto-generates ``<name>-1``, ``<name>-2``, … if the user presses Enter.
    """
    candidate = output_dir / project_name
    if not candidate.exists():
        return candidate

    original = project_name
    counter = 1
    while True:
        logger.warning("Project directory '%s' already exists.", candidate)
        try:
            new_name = input(
                f"Directory '{candidate}' exists. "
                "Enter a new project name or press Enter to auto-generate: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            new_name = ""

        if new_name:
            project_name = new_name
        else:
            project_name = f"{original}-{counter}"
            counter += 1

        candidate = output_dir / project_name
        if not candidate.exists():
            return candidate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_project(
    data: dict[str, Any],
    output_dir: str | Path = ".",
    dry_run: bool = False,
) -> Path:
    """
    Scaffold a project from a validated config dict.

    Parameters
    ----------
    data:
        Parsed config (from :func:`load_config` or your own dict).
    output_dir:
        Where to create the project folder. Defaults to the current directory.
    dry_run:
        If ``True``, print what *would* be created without touching the filesystem.

    Returns
    -------
    Path
        The resolved path of the created (or would-be-created) project directory.

    Raises
    ------
    ValueError / TypeError
        On validation errors.
    OSError
        On filesystem errors.
    """
    output_dir = Path(output_dir).resolve()
    project_name, structure = validate_structure(data)

    project_path = _resolve_project_name(project_name, output_dir)

    if dry_run:
        print(f"[dry-run] Would create project: {project_path}")
        for entry in structure:
            tag = "dir " if entry["type"] == "folder" else "file"
            print(f"[dry-run]   [{tag}] {entry['name']}")
        return project_path

    logger.info("Creating project: %s", project_path)
    project_path.mkdir(parents=True)

    for entry in structure:
        _create_entry(project_path, entry)

    logger.info("Project '%s' created successfully at %s", project_name, project_path)
    return project_path


# ---------------------------------------------------------------------------
# Legacy shim – keeps backward-compatibility with the original API
# ---------------------------------------------------------------------------

def create_project_from_json(data: dict[str, Any], output_dir: str | Path = ".") -> Path:
    """
    Backward-compatible wrapper around :func:`create_project`.

    .. deprecated::
        Use :func:`create_project` directly.
    """
    import warnings

    warnings.warn(
        "create_project_from_json() is deprecated; use create_project() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_project(data, output_dir=output_dir)