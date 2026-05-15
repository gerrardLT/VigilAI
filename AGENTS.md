# Agent Instructions

## Python Environment

This project should be run with the project-specific Conda environment named `vigilai`.

Use this environment before running backend commands, tests, dependency installs, or local services:

```powershell
conda activate vigilai
```

Do not assume the active Conda environment is correct. Check it when needed:

```powershell
conda info --envs
python -c "import sys; print(sys.executable)"
```

Expected Python executable:

```text
C:\Users\gerrard\miniconda3\envs\vigilai\python.exe
```

## Dependencies

Dependencies installed into Conda `base` are not installed into `vigilai`. If a package was installed while `base` was active, install it again after activating `vigilai`.

Install backend dependencies from the backend requirements file:

```powershell
conda activate vigilai
python -m pip install -r app/backend/requirements.txt -i https://pypi.org/simple --timeout 60
```

Prefer the official PyPI index for packages that are missing or fail through the global pip mirror.

## Backend Configuration

Backend environment variables are loaded from:

```text
app/backend/.env
```

That file is intentionally ignored by git and may contain local API keys.
