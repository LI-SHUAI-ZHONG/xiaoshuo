"""Repository-confined declarative plugin manifest loader."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from accos.modules.tools.public import PluginManifest, PluginTrustStatus

if TYPE_CHECKING:
    from pathlib import Path


class RepositoryPluginLoader:
    """Load JSON metadata only from a configured repository fixture root."""

    def __init__(self, root: Path, *, trusted_signatures: frozenset[str]) -> None:
        self._root = root.resolve()
        self._trusted_signatures = trusted_signatures

    def load(self, relative_manifest: str) -> PluginManifest:
        """Reject escapes/remote paths and derive trust from local configuration."""
        path = (self._root / relative_manifest).resolve()
        if not path.is_relative_to(self._root) or path.name != "manifest.json":
            raise ValueError("plugin manifest must remain under the configured repository root")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("plugin manifest must be a JSON object")
        signature = raw.get("signature")
        plugin_id = raw.get("plugin_id")
        version = raw.get("version")
        compatibility = raw.get("core_compatibility")
        capabilities = raw.get("capabilities")
        permissions = raw.get("required_permissions")
        enabled = raw.get("enabled")
        if (
            not isinstance(plugin_id, str)
            or not isinstance(version, str)
            or not isinstance(compatibility, str)
            or not isinstance(capabilities, list)
            or not isinstance(permissions, list)
            or not all(isinstance(value, str) for value in (*capabilities, *permissions))
            or (signature is not None and not isinstance(signature, str))
            or not isinstance(enabled, bool)
        ):
            raise ValueError("plugin manifest fields are invalid")
        if signature is None:
            trust = PluginTrustStatus.UNSIGNED
        elif isinstance(signature, str) and signature in self._trusted_signatures:
            trust = PluginTrustStatus.TRUSTED
        else:
            trust = PluginTrustStatus.UNTRUSTED
        return PluginManifest(
            plugin_id=plugin_id,
            version=version,
            core_compatibility=compatibility,
            capabilities=tuple(capabilities),
            required_permissions=frozenset(permissions),
            signature=signature,
            trust_status=trust,
            enabled=enabled,
        )
