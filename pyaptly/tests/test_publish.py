"""Test publish functionality."""
import pytest

import pyaptly


@pytest.mark.parametrize("repo", ["fakerepo01", "asdfasdf"])
@pytest.mark.parametrize("config", ["publish.toml"], indirect=True)
def test_publish_create_single(config, snapshot_create, test_key_03, repo):
    """Test if creating a single publish works."""
    args = ["-c", config, "publish", "create", repo]
    if repo == "asdfasdf":
        with pytest.raises(ValueError):
            pyaptly.main(args)
        return
    pyaptly.main(args)
    state = pyaptly.SystemStateReader()
    state.read()
    assert set(["fakerepo01 main"]) == state.publishes
    expect = {"fakerepo01 main": set(["fakerepo01-20121010T0000Z"])}
    assert expect == state.publish_map


@pytest.mark.parametrize("config", ["publish.toml"], indirect=True)
def test_publish_create_inexistent(config, snapshot_create, test_key_03):
    """Test if creating inexistent publish raises an error."""
    args = ["-c", config, "publish", "create", "asdfasdf"]
    error = False
    try:
        pyaptly.main(args)
    except ValueError:
        error = True
    assert error


@pytest.mark.parametrize("config", ["publish-repo.toml"], indirect=True)
def test_repo_crate_basic(config, repo_create):
    """Test if creating repositories works."""
    pass


@pytest.mark.parametrize("config", ["publish-repo.toml"], indirect=True)
def test_publish_create_repo(config, repo_create):
    """Test if creating repo publishes works."""
    args = [
        "-c",
        config,
        "publish",
        "create",
    ]
    pyaptly.main(args)
    args = [
        "-c",
        config,
        "publish",
        "update",
    ]
    pyaptly.main(args)
    state = pyaptly.SystemStateReader()
    state.read()
    assert set(["centrify latest"]) == state.publishes
    assert {"centrify latest": set([])} == state.publish_map


@pytest.mark.parametrize("config", ["publish.toml"], indirect=True)
def test_publish_create_basic(config, publish_create):
    """Test if creating publishes works."""
    pass


@pytest.mark.parametrize("via", ["publish", "snapshot"])
@pytest.mark.parametrize("config", ["publish-current.toml"], indirect=True)
def test_publish_update_rotating(config, freeze, publish_create_rotating, via):
    """Test if update rotating publishes works."""
    freeze.move_to("2012-10-11 10:10:10")
    args = ["-c", config, via, "update"]
    pyaptly.main(args)
    state = pyaptly.SystemStateReader()
    state.read()
    expect = {
        "fake/current stable": set(["fake-current"]),
        "fakerepo01/current stable": set(["fakerepo01-current"]),
        "fakerepo02/current stable": set(["fakerepo02-current"]),
    }
    assert expect == state.publish_map
    if via == "snapshot":
        expect2 = {
            "fakerepo02-current",
            "fakerepo02-current-rotated-20121011T1010Z",
            "fakerepo01-current",
            "fake-current",
            "fakerepo01-current-rotated-20121011T1010Z",
            "fakerepo02-current-rotated-20121010T1010Z",
            "fakerepo01-current-rotated-20121010T1010Z",
            "fake-current-rotated-20121010T1010Z",
            "fake-current-rotated-20121011T1010Z",
        }
        assert expect2 == state.snapshots


@pytest.mark.parametrize("config", ["publish-current.toml"], indirect=True)
def test_publish_create_rotating(config, publish_create_rotating):
    """Test if creating rotating publishes works."""
    pass


@pytest.mark.parametrize("config", ["publish-publish.toml"], indirect=True)
def test_publish_create_republish(config, publish_create_republish):
    """Test if creating republishes works."""
    pass


@pytest.mark.parametrize("config", ["publish-publish.toml"], indirect=True)
def test_publish_update_republish(config, publish_create_republish, freeze):
    """Test if update republishes works."""
    freeze.move_to("2012-10-11 10:10:10")
    args = ["-c", config, "snapshot", "create"]
    pyaptly.main(args)
    args = ["-c", config, "publish", "update"]
    pyaptly.main(args)
    state = pyaptly.SystemStateReader()
    state.read()
    assert "fakerepo01-stable main" in state.publishes
    # As you see fakerepo01-stable main points to the old snapshot
    # this is theoretically not correct, but it will be fixed with
    # the next call to publish update. Since we use this from a hourly cron
    # job it is no problem.
    # This can't be easily fixed and would need a rewrite of the
    # dependencies engine.
    expect = {
        "fakerepo01-stable main": set(["fakerepo01-20121010T0000Z"]),
        "fakerepo02 main": set(["fakerepo02-20121006T0000Z"]),
        "fakerepo01 main": set(["fakerepo01-20121011T0000Z"]),
    }
    assert expect == state.publish_map


@pytest.mark.parametrize("config", ["publish.toml"], indirect=True)
def test_publish_updating_basic(config, publish_create, freeze):
    """Test if updating publishes works."""
    freeze.move_to("2012-10-11 10:10:10")
    args = ["-c", config, "snapshot", "create"]
    pyaptly.main(args)
    args = ["-c", config, "publish", "update"]
    pyaptly.main(args)
    state = pyaptly.SystemStateReader()
    state.read()
    expect = set(
        [
            "archived-fakerepo01-20121011T1010Z",
            "fakerepo01-20121011T0000Z",
            "fakerepo02-20121006T0000Z",
            "fakerepo01-20121010T0000Z",
        ]
    )
    assert expect == state.snapshots
    expect2 = {
        "fakerepo02 main": set(["fakerepo02-20121006T0000Z"]),
        "fakerepo01 main": set(["fakerepo01-20121011T0000Z"]),
    }
    assert expect2 == state.publish_map


@pytest.mark.parametrize("repo", ["centrify", "asdfasdf"])
@pytest.mark.parametrize("config", ["repo.toml"], indirect=True)
def test_repo_create_single(config, repo, test_key_03):
    """Test if updating publishes works."""
    args = ["-c", config, "repo", "create", repo]
    if repo == "asdfasdf":
        with pytest.raises(ValueError):
            pyaptly.main(args)
        return
    pyaptly.main(args)
    state = pyaptly.SystemStateReader()
    state.read()
    assert set(["centrify"]) == state.repos
