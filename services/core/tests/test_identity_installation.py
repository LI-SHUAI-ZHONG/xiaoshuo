"""T004/T008: installer secret handling and settings precedence. Execute only at stage 45."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from accos.kernel.errors import ConfigurationError
from accos.kernel.settings import load_settings
from scripts import setup_identity
from scripts.setup_identity import prepare_identity


def required_environment() -> dict[str, str]:
    return {
        "ACCOS_DATABASE_URL": "postgresql+psycopg://fixture:fixture@localhost/fixture",
        "ACCOS_REDIS_URL": "redis://:fixture@localhost/0",
        "ACCOS_S3_ENDPOINT": "http://localhost:9000",
        "ACCOS_S3_BUCKET": "fixture-project",
        "ACCOS_S3_ACCESS_KEY": "fixture-access",
        "ACCOS_S3_SECRET_KEY": "fixture-secret",
    }


def test_private_installation_preserves_keys_and_loads_without_exposing_token(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".secrets/identity"
    result = prepare_identity(target)
    env = tmp_path / ".env"
    env.write_text(
        "ACCOS_IDENTITY_CONFIG_FILE=.secrets/identity/identity.env\nACCOS_SESSION_HOURS=4\n",
        encoding="utf-8",
    )
    config = load_settings(env_file=env, environ=required_environment())
    token = (target / "bootstrap-token.txt").read_text().strip()
    assert config.auth.bootstrap_digest == hashlib.sha256(token.encode()).hexdigest()
    assert len(base64.b64decode(config.auth.secret_keys[config.auth.active_key_id])) == 32
    assert config.auth.session_hours == 4
    assert token not in json.dumps(result) and token not in repr(config.auth)
    assert token not in (target / "identity.env").read_text()
    original = (target / "identity.env").read_bytes()
    with pytest.raises(FileExistsError):
        prepare_identity(target)
    assert (target / "identity.env").read_bytes() == original
    override = load_settings(
        env_file=env, environ={**required_environment(), "ACCOS_SESSION_HOURS": "6"}
    )
    assert override.auth.session_hours == 6


def test_private_identity_file_cannot_replace_database_config(tmp_path: Path) -> None:
    fragment = tmp_path / "identity.env"
    fragment.write_text("ACCOS_DATABASE_URL=postgresql://forged@elsewhere/db\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="only auth"):
        load_settings(
            env_file=tmp_path / ".env",
            environ={**required_environment(), "ACCOS_IDENTITY_CONFIG_FILE": str(fragment)},
        )


def test_explicit_missing_identity_file_is_not_silently_ignored(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="unavailable"):
        load_settings(
            env_file=tmp_path / ".env",
            environ={**required_environment(), "ACCOS_IDENTITY_CONFIG_FILE": "missing.env"},
        )


def test_t004_t008_windows_acl_is_user_only_and_precedes_secret_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "private-install"
    calls: list[tuple[Path, bool]] = []
    monkeypatch.setattr(setup_identity, "os", SimpleNamespace(name="nt", environ=os.environ))

    def denied(path: Path, *, directory: bool) -> None:
        calls.append((path, directory))
        raise PermissionError("ACL denied")

    generate = Mock(
        side_effect=AssertionError("Secrets must not be generated before directory ACL")
    )
    monkeypatch.setattr(setup_identity, "restrict_windows_permissions", denied)
    monkeypatch.setattr("scripts.setup_identity.secrets.token_urlsafe", generate)
    with pytest.raises(PermissionError):
        prepare_identity(target)
    assert calls == [(target.resolve(), True)]
    assert list(target.iterdir()) == []
    generate.assert_not_called()


@pytest.mark.parametrize("directory,rights", [(True, "(OI)(CI)F"), (False, "F")])
def test_t008_windows_permission_command_uses_sid_and_rejects_inherited_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: bool, rights: str
) -> None:
    sid = "S-1-5-21-100-200-300-1001"
    runner = Mock(
        return_value=subprocess.CompletedProcess([], 0, f'"local\\author","{sid}"'.encode())
    )
    monkeypatch.setattr("scripts.setup_identity.subprocess.run", runner)
    target = tmp_path / "private target"
    setup_identity.restrict_windows_permissions(target, directory=directory)
    command = runner.call_args_list[1].args[0]
    assert command[1:] == [str(target), "/inheritance:r", "/grant:r", f"*{sid}:{rights}"]
    assert all(
        call.kwargs["check"] and call.kwargs["capture_output"] for call in runner.call_args_list
    )
    assert all(not call.kwargs.get("shell", False) for call in runner.call_args_list)


def test_t008_acl_failure_does_not_return_subprocess_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = b"private-output-must-not-be-displayed"
    monkeypatch.setattr(
        "scripts.setup_identity.subprocess.run",
        Mock(side_effect=subprocess.CalledProcessError(1, ["icacls"], output=marker)),
    )
    with pytest.raises(PermissionError) as failure:
        setup_identity.restrict_windows_permissions(tmp_path, directory=True)
    assert marker.decode() not in str(failure.value)


def test_t008_file_acl_failure_leaves_no_secret_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "private.env"
    close = Mock(wraps=os.close)
    monkeypatch.setattr(
        setup_identity,
        "os",
        SimpleNamespace(
            name="nt",
            open=os.open,
            close=close,
            fdopen=os.fdopen,
            O_WRONLY=os.O_WRONLY,
            O_CREAT=os.O_CREAT,
            O_EXCL=os.O_EXCL,
        ),
    )
    monkeypatch.setattr(
        setup_identity,
        "restrict_windows_permissions",
        Mock(side_effect=PermissionError("ACL denied")),
    )
    with pytest.raises(PermissionError):
        setup_identity.write_private(target, "must-never-be-written")
    assert target.read_bytes() == b""
    close.assert_called_once()


@pytest.mark.parametrize(
    "origin",
    [
        "http://192.168.1.2:3000",
        "https://studio.example/path",
        "https://studio.example\nINJECT=yes",
        "http://localhost:0",
    ],
)
def test_t004_invalid_installer_options_create_no_directory(tmp_path: Path, origin: str) -> None:
    target = tmp_path / "identity"
    with pytest.raises(ValueError):
        prepare_identity(target, public_origin=origin)
    assert not target.exists()


def test_t004_t008_legacy_cli_shares_private_installation_and_prints_only_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts import prepare_local_identity

    target = tmp_path / "legacy-private" / "auth.env"
    workspace = "45b36b4f-ea71-4a61-9cd1-d21241441120"
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepare_local_identity.py",
            "--output",
            str(target),
            "--public-origin",
            "https://studio.example",
            "--adopt-workspace",
            workspace,
        ],
    )
    assert prepare_local_identity.main(legacy_output_file=True) == 0
    output = capsys.readouterr().out
    token = (target.parent / "bootstrap-token.txt").read_text().strip()
    settings = load_settings(
        env_file=tmp_path / ".env",
        environ={**required_environment(), "ACCOS_IDENTITY_CONFIG_FILE": str(target)},
    )
    assert token not in output
    assert settings.auth.secret_keys[settings.auth.active_key_id] not in output
    assert json.loads(output)["identity_config_file"] == str(target.resolve())
    assert settings.auth.public_origin == "https://studio.example"
    assert str(settings.auth.adopt_workspace_id) == workspace
    before = target.read_bytes()
    with pytest.raises(SystemExit) as failure:
        prepare_local_identity.main(legacy_output_file=True)
    assert failure.value.code == 1
    assert target.read_bytes() == before
