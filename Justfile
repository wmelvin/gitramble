set dotenv-load

@default:
  @just --list

# @init:
#   pipenv run pip install -e '.[test]'

@clean:
  -rm dist/*
  -rmdir dist
  -rm src/gitramble.egg-info/*
  -rmdir src/gitramble.egg-info

@build: lint check test
  uv run pyproject-build

@check:
  uv run ruff format --check

@format: lint
  uv run ruff format

@lint:
  uv run ruff check

@test:
  uv run pytest

@checks: lint check test

@tui:
  uv run textual run --dev src/gitramble/cli.py $GRMBL_DIR -u $GRMBL_URL --ctrl-s

# Run the CLI with the help flag and save the output to temp.txt.
@help:
  uv run python3 src/gitramble/cli.py --help > temp.txt
