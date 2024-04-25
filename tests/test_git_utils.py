"""Tests for gitramble.git_utils module. Requires 'git' is installed on the system."""

from gitramble.git_utils import git_status_clean, run_git, run_git_log, run_git_status


def test_run_git(tmp_path):
    run_git(tmp_path, ["init", "-b", "main"])
    assert (tmp_path / ".git").exists()


def test_run_git_add(tmp_path):
    run_git(tmp_path, ["init", "-b", "main"])
    (tmp_path / "file.txt").write_text("content")
    run_git(tmp_path, ["add", "file.txt"])
    run_git(tmp_path, ["commit", "-m", "Add file.txt"])
    output, errors = run_git_log(tmp_path)
    assert "Add file.txt" in output
    assert not errors


def test_run_git_status(tmp_path):
    run_git(tmp_path, ["init", "-b", "main"])
    (tmp_path / "file.txt").write_text("content")
    run_git(tmp_path, ["add", "file.txt"])
    output, errors = run_git_status(tmp_path)
    assert "file.txt" in output
    assert not errors
    assert not git_status_clean(tmp_path)

    run_git(tmp_path, ["commit", "-m", "Add file.txt"])
    output, errors = run_git_status(tmp_path)
    assert not output
    assert not errors
    assert git_status_clean(tmp_path)

    output, errors = run_git_log(tmp_path)
    assert "Add file.txt" in output
    assert not errors
