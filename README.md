# 📁 projgen

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![PyPI](https://img.shields.io/pypi/v/projgen?color=orange&label=PyPI)
![License](https://img.shields.io/badge/License-MIT-green)
![JSON](https://img.shields.io/badge/JSON-supported-lightgrey?logo=json)
![YAML](https://img.shields.io/badge/YAML-supported-lightgrey?logo=yaml)

> A CLI tool to scaffold project directory structures from **JSON** or **YAML** config files.

```
pip install projgen          # JSON support (no extra deps)
pip install projgen[yaml]    # JSON + YAML support
```

---
### Note: Any idea or contribution is accepted after validation of authenticity of the contribution. Make sure to fork this first and follow me on Github.

## Quick start

```bash
# From a JSON file
projgen fastapi_proj.json

# From a YAML file
projgen fastapi_proj.yaml

# Choose output directory
projgen structure.yaml --output ~/projects

# Preview without creating anything
projgen structure.json --dry-run

# Verbose/debug output
projgen structure.json --verbose
```

---

## Config format

Both JSON and YAML use the same schema.

### JSON

```json
{
  "project_name": "my-api",
  "project-structure": [
    { "level": 1, "type": "folder", "name": "src" },
    { "level": 2, "type": "file",   "name": "src/main.py" },
    { "level": 1, "type": "file",   "name": "README.md" },
    { "level": 1, "type": "file",   "name": "Dockerfile" }
  ]
}
```

### YAML

```yaml
project_name: my-api

project-structure:
  - { level: 1, type: folder, name: src }
  - { level: 2, type: file,   name: "src/main.py" }
  - { level: 1, type: file,   name: README.md }
  - { level: 1, type: file,   name: Dockerfile }
```

### Schema reference

| Field  | Type            | Description                                         |
|--------|-----------------|-----------------------------------------------------|
| `name` | `str`           | Relative path, e.g. `"app/api/v1/routes.py"`       |
| `level`| `int` (≥ 1)     | Nesting depth — must match the number of `/` in `name` + 1 |
| `type` | `"file"\|"folder"` | Entry type                                       |

**Level rule:** `level = path.count("/") + 1`

| name              | level |
|-------------------|-------|
| `src`             | 1     |
| `src/api`         | 2     |
| `src/api/v1`      | 3     |
| `src/api/v1/routes.py` | 4 |

**Extensionless files** that are allowed without an extension:
`Dockerfile`, `Makefile`, `LICENSE`, `README`, `NOTICE`, `CODEOWNERS`,
`Procfile`, `Vagrantfile`, `Jenkinsfile`, `Brewfile`, and dotfiles (`.gitignore`, `.env`, …).

---

## Python API

```python
from projgen.core import load_config, create_project

# Load from file (auto-detects JSON / YAML)
data = load_config("structure.yaml")

# Scaffold the project
project_path = create_project(data, output_dir="~/projects")
print(f"Created: {project_path}")

# Dry-run preview
create_project(data, dry_run=True)

# Build the dict yourself
data = {
    "project_name": "hello",
    "project-structure": [
        {"level": 1, "type": "file", "name": "main.py"},
    ],
}
create_project(data)
```

---

## CLI reference

```
usage: projgen [-h] [-o DIR] [--dry-run] [-v] [--version] CONFIG_FILE

positional arguments:
  CONFIG_FILE           Path to the structure config file (.json, .yaml, .yml)

options:
  -h, --help            show this help message and exit
  -o DIR, --output DIR  Directory where the project folder will be created (default: .)
  --dry-run             Preview what would be created without touching the filesystem
  -v, --verbose         Enable verbose/debug output
  --version             show program's version number and exit
```

---

## Development

```bash
git clone https://github.com/avinash-kumar-prajapati-AI/Python
cd Python/projgen

# Install in editable mode with all dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check projgen tests
```

---

## Publishing to PyPI

```bash
pip install build twine

# Build sdist + wheel
python -m build

# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

---

## License

MIT © Avinash Kumar Prajapati
