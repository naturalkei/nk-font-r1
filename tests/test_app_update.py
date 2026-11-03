"""App self-update: fast-forward only, never touches local work (synthetic git repos)."""

from __future__ import annotations

import subprocess

import pytest

from nkfont.studio import update


def git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repos(tmp_path):
    """origin (bare), upstream work tree that pushes, and the app checkout that updates."""
    origin, up, app = tmp_path / "origin.git", tmp_path / "up", tmp_path / "app"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(up))
    (up / "a.txt").write_text("1")
    git(up, "add", "a.txt")
    git(up, "commit", "-q", "-m", "first")
    git(up, "push", "-q", "origin", "HEAD:main")
    git(tmp_path, "clone", "-q", str(origin), str(app))
    return up, app


def push(up, name, text, msg):
    (up / name).write_text(text)
    git(up, "add", name)
    git(up, "commit", "-q", "-m", msg)
    git(up, "push", "-q", "origin", "HEAD:main")


def test_up_to_date(repos):
    _, app = repos
    st = update.status(app)
    assert (st["behind"], st["ahead"], st["can_update"]) == (0, 0, False)
    assert update.apply(app)["updated"] is False


def test_fast_forwards_and_lists_commits(repos):
    up, app = repos
    push(up, "b.txt", "2", "add specimen")
    st = update.status(app)
    assert st["behind"] == 1 and st["can_update"] and st["commits"][0].endswith("add specimen")
    r = update.apply(app, reinstall=False)
    assert r["updated"] and (app / "b.txt").read_text() == "2"
    assert update.status(app)["behind"] == 0


def test_untracked_files_do_not_block(repos):
    up, app = repos
    push(up, "b.txt", "2", "upstream")
    (app / "my-preset.toml").write_text("label = 'mine'")
    assert update.apply(app, reinstall=False)["updated"]
    assert (app / "my-preset.toml").exists()


def test_dirty_tree_blocks_update_and_is_left_alone(repos):
    up, app = repos
    push(up, "a.txt", "upstream", "change a")
    (app / "a.txt").write_text("my edit")
    assert update.status(app)["dirty"] == ["a.txt"]
    with pytest.raises(update.UpdateError, match="커밋하지 않은 변경"):
        update.apply(app)
    assert (app / "a.txt").read_text() == "my edit"


def test_local_commits_block_update(repos):
    up, app = repos
    push(up, "b.txt", "2", "upstream")
    (app / "c.txt").write_text("mine")
    git(app, "add", "c.txt")
    git(app, "commit", "-q", "-m", "local")
    with pytest.raises(update.UpdateError, match="로컬 커밋 1개"):
        update.apply(app)
    assert not (app / "b.txt").exists()


def test_not_a_checkout(tmp_path):
    with pytest.raises(update.UpdateError):
        update.status(tmp_path)


def test_update_page_is_packaged():
    from importlib import resources

    page = resources.files("nkfont.studio").joinpath("static", "update.html").read_text()
    assert "/api/update/check" in page and "/api/app/restart" in page
