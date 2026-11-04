# Red Room — one-command workflows.

setup:
    python3 -m venv .venv
    .venv/bin/pip install -U pip
    .venv/bin/pip install -e ".[dev]"

demo:
    .venv/bin/redroom demo --offline --auto-approve

demo-interactive:
    .venv/bin/redroom demo --offline

test:
    .venv/bin/pytest -q

run:
    .venv/bin/redroom run
