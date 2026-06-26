# projgen/cli.py
"""
Command-line interface for projgen.

Usage
-----
    projgen path/to/structure.json
    projgen path/to/structure.yaml
    projgen path/to/structure.json --output ./workspace
    projgen path/to/structure.json --dry-run
    projgen path/to/structure.json --verbose
    projgen --version
"""

from __future__ import annotations

import argparse
import logging
import sys

from pathlib import Path

from projgen import __version__
from projgen.core import create_project, load_config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(levelname)s  %(message)s",
        )
    )
    root = logging.getLogger("projgen")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projgen",
        description=(
            "📁 projgen – Generate a project directory structure from a JSON or YAML file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  projgen fastapi_proj.json
  projgen structure.yaml --output ~/workspace
  projgen structure.json --dry-run --verbose
  projgen structure.yml  --output .
""",
    )

    parser.add_argument(
        "config_file",
        metavar="CONFIG_FILE",
        help="Path to the structure config file (.json, .yaml, or .yml).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        default=".",
        help="Directory where the project folder will be created (default: current directory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without touching the filesystem.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug output.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns an exit code (0 = success, non-zero = failure).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    logger = logging.getLogger("projgen")

    config_path = Path(args.config_file)
    output_dir = Path(args.output)

    # --- load ---
    try:
        data = load_config(config_path)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    except ValueError as exc:
        print(f"Error loading config: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error while reading config: {exc}", file=sys.stderr)
        return 1

    # --- create ---
    try:
        project_path = create_project(data, output_dir=output_dir, dry_run=args.dry_run)
    except (ValueError, TypeError) as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Filesystem error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    if not args.dry_run:
        print(f"✅ Project created at: {project_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())