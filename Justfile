set dotenv-load

@default:
  @just --list

@init:
  pipenv run pip install -e '.[test]'

@clean:
  -rm dist/*
  -rmdir dist
  -rm src/gitramble.egg-info/*
  -rmdir src/gitramble.egg-info

@build: lint check test
  pipenv run pyproject-build

@check:
  pipenv run ruff format --check

@format: lint
  pipenv run ruff format

@lint:
  pipenv run ruff check

@test:
  pipenv run pytest

@checks: lint check test

@tui:
  pipenv run textual run --dev src/gitramble/cli.py $GRMBL_DIR -u $GRMBL_URL
