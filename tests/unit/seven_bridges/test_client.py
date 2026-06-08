"""Tests for the seven_bridges Client: config, token resolution, retry, folder listing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from dm_bip.seven_bridges.client import (
    DEFAULT_APP,
    DEFAULT_BASE_URL,
    DEFAULT_PROJECT,
    Client,
    SevenBridgesError,
    TokenMissingError,
    get_token,
    load_config,
)


def test_load_config_uses_defaults_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Base URL, project, and app fall back to documented defaults."""
    for var in ("SBG_BASE_URL", "SBG_DEFAULT_PROJECT", "SBG_DEFAULT_APP", "SBG_TOKEN_FILE"):
        monkeypatch.delenv(var, raising=False)

    config = load_config()

    assert config.base_url == DEFAULT_BASE_URL
    assert config.project == DEFAULT_PROJECT
    assert config.app == DEFAULT_APP


def test_load_config_respects_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """All four config knobs accept env overrides."""
    monkeypatch.setenv("SBG_BASE_URL", "https://override.example/v2/")
    monkeypatch.setenv("SBG_DEFAULT_PROJECT", "owner/proj")
    monkeypatch.setenv("SBG_DEFAULT_APP", "owner/proj/app/3")
    monkeypatch.setenv("SBG_TOKEN_FILE", str(tmp_path / "tok"))

    config = load_config()

    assert config.base_url == "https://override.example/v2"  # trailing slash stripped
    assert config.project == "owner/proj"
    assert config.app == "owner/proj/app/3"
    assert config.token_file == tmp_path / "tok"


def test_get_token_prefers_env_var(monkeypatch: pytest.MonkeyPatch, sbg_env: Path) -> None:
    """SBG_AUTH_TOKEN env var wins over the token file."""
    sbg_env.write_text("from-file")
    monkeypatch.setenv("SBG_AUTH_TOKEN", "from-env")

    assert get_token(load_config()) == "from-env"


def test_get_token_falls_back_to_file(sbg_env: Path) -> None:
    """With no env var set, the token file content is returned."""
    sbg_env.write_text("from-file\n")  # trailing newline should be stripped

    assert get_token(load_config()) == "from-file"


def test_get_token_raises_when_neither_set(sbg_env: Path) -> None:  # noqa: ARG001
    """With no env var and no file, TokenMissingError points the user at both options."""
    with pytest.raises(TokenMissingError, match="SBG_AUTH_TOKEN"):
        get_token(load_config())


def test_request_authenticates_with_token_header(
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """Client.request sends X-SBG-Auth-Token with the resolved token."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=p1",
        json={"items": []},
    )

    Client(load_config()).request("files?project=p1")

    request = httpx_mock.get_requests()[0]
    assert request.headers["X-SBG-Auth-Token"] == "test-sbg-token"


def test_request_retries_on_transient_then_succeeds(
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 503 followed by 200 succeeds; total of two requests issued."""
    monkeypatch.setattr("dm_bip.seven_bridges.client.time.sleep", lambda _: None)
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks",
        status_code=503,
        text="busy",
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks",
        json={"items": [{"id": "t1"}]},
    )

    result = Client(load_config()).request("tasks")

    assert result == {"items": [{"id": "t1"}]}
    assert len(httpx_mock.get_requests()) == 2


def test_request_raises_on_persistent_5xx(
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If 5xx persists past RETRY_MAX_ATTEMPTS, surface a SevenBridgesError."""
    monkeypatch.setattr("dm_bip.seven_bridges.client.time.sleep", lambda _: None)
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks",
        status_code=503,
        text="busy",
        is_reusable=True,
    )

    with pytest.raises(SevenBridgesError):
        Client(load_config()).request("tasks")


def test_request_raises_on_4xx(
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """Non-retryable 4xx responses surface as SevenBridgesError with the path in the message."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks/missing",
        status_code=404,
        text="not found",
    )

    with pytest.raises(SevenBridgesError, match="tasks/missing"):
        Client(load_config()).request("tasks/missing")


def test_request_accepts_absolute_url(
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """A path that starts with http(s) is used as-is (needed for SBG download_info URLs)."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://elsewhere.example/special",
        json={"url": "https://s3/signed"},
    )

    result = Client(load_config()).request("https://elsewhere.example/special")

    assert result == {"url": "https://s3/signed"}


def test_get_folders_filters_to_folder_type(
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """get_folders returns only items where type == 'folder'."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=test/project",
        json={
            "items": [
                {"id": "a", "name": "FolderA", "type": "folder"},
                {"id": "b", "name": "file.txt", "type": "file"},
                {"id": "c", "name": "FolderB", "type": "folder"},
            ]
        },
    )

    folders = Client(load_config()).get_folders(project="test/project")

    assert [f["name"] for f in folders] == ["FolderA", "FolderB"]
