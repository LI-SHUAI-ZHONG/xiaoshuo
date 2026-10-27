"""Prepare private local identity configuration without starting ACCOS or touching its database."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID


def restrict_windows_permissions(path: Path, *, directory: bool) -> None:
    """Remove inherited access before writing secrets, using the current user's SID."""
    system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    try:
        identity = subprocess.run(
            [str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        match = re.search(rb'"(S-1-[0-9]+(?:-[0-9]+)+)"', identity.stdout)
        if match is None:
            raise PermissionError("Cannot resolve the installation user's SID.")
        sid = match[1].decode("ascii")
        rights = "(OI)(CI)F" if directory else "F"
        subprocess.run(
            [
                str(system / "icacls.exe"),
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"*{sid}:{rights}",
            ],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise PermissionError("Cannot set private identity permissions.") from None


def write_private(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if os.name == "nt":
            restrict_windows_permissions(path, directory=False)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n", closefd=False) as stream:
            stream.write(content)
    finally:
        os.close(descriptor)


def prepare_identity(
    directory: Path,
    *,
    public_origin: str = "http://localhost:3000",
    adopt_workspace: str = "",
    config_name: str = "identity.env",
) -> dict[str, str]:
    """Only create a new directory; never replace an installation's existing master keys."""
    origin = urlsplit(public_origin)
    if (
        origin.scheme not in {"http", "https"}
        or not origin.hostname
        or origin.path
        or origin.query
        or origin.fragment
        or origin.username is not None
        or origin.password is not None
        or any(ord(c) < 32 or c.isspace() for c in public_origin)
        or (origin.scheme == "http" and origin.hostname not in {"localhost", "127.0.0.1", "::1"})
        or (origin.port is not None and not 1 <= origin.port <= 65535)
    ):
        raise ValueError(
            "Use an HTTPS origin or explicit loopback development origin without a path."
        )
    if adopt_workspace:
        adopt_workspace = str(UUID(adopt_workspace))
    if (
        not config_name.endswith(".env")
        or Path(config_name).name != config_name
        or any(c in config_name for c in "/\\:\r\n")
    ):
        raise ValueError("The private configuration must be a plain .env filename.")
    target = directory.resolve()
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    if os.name == "nt":
        restrict_windows_permissions(target, directory=True)
    token = secrets.token_urlsafe(48)
    key_id = "local-" + secrets.token_hex(8)
    key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    config = target / config_name
    bootstrap = target / "bootstrap-token.txt"
    write_private(
        config,
        "# Private installation configuration. Preserve this keyring with encrypted backups.\n"
        f"ACCOS_PUBLIC_ORIGIN={public_origin}\n"
        f"ACCOS_ALLOWED_HOSTS={origin.hostname},localhost,127.0.0.1,[::1]\n"
        f"ACCOS_BOOTSTRAP_ADOPT_WORKSPACE_ID={adopt_workspace}\n"
        f"ACCOS_BOOTSTRAP_TOKEN_SHA256={hashlib.sha256(token.encode()).hexdigest()}\n"
        f"ACCOS_SECRET_ACTIVE_KEY_ID={key_id}\n"
        f"ACCOS_SECRET_KEYS_JSON={json.dumps({key_id: key}, separators=(',', ':'))}\n",
    )
    write_private(bootstrap, token + "\n")
    # Output contains locations only; passwords, tokens and master keys never enter logs.
    return {"identity_config_file": str(config), "bootstrap_token_file": str(bootstrap)}


def main(*, legacy_output_file: bool = False) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(".secrets/identity"), required=legacy_output_file
    )
    parser.add_argument("--public-origin", default="http://localhost:3000")
    parser.add_argument("--adopt-workspace", default="")
    arguments = parser.parse_args()
    try:
        result = prepare_identity(
            arguments.output.parent if legacy_output_file else arguments.output,
            public_origin=arguments.public_origin,
            adopt_workspace=arguments.adopt_workspace,
            config_name=arguments.output.name if legacy_output_file else "identity.env",
        )
    except (OSError, ValueError) as error:
        parser.exit(
            1,
            f"Identity setup did not complete ({type(error).__name__}). "
            "Check permissions and options; use a new private directory. "
            "Keep any partial files for recovery; existing files are never replaced.\n",
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
