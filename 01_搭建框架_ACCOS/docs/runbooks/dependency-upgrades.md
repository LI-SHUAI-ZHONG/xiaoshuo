# Dependency upgrade policy

## Pinned toolchain

| Component | Pinned version | Authoritative project source |
|---|---:|---|
| Python | 3.12.14 | `.python-version` and root `requires-python` |
| uv | 0.12.7 | root `[tool.uv].required-version` |
| Node.js | 22.23.2 | `.node-version` and root `engines.node` |
| pnpm | 11.25.0 | root `packageManager` and `engines.pnpm` |

The root `uv.lock` and `pnpm-lock.yaml` are the only dependency-resolution lock sources. All direct development and build dependencies use exact versions in their manifests. Container images will be introduced and digest-pinned in execution 03; execution 02 contains no container manifest to pin.

## Upgrade procedure

1. Open a dedicated change and state the component, motivation, compatibility range, and rollback version. A baseline architecture change also requires a new ADR.
2. Read the upstream release notes and security advisories. Do not select prereleases or an unqualified `latest` tag.
3. For Python or Node.js, stay on the baseline series unless an accepted ADR changes it. Select the highest stable patch compatible with all locked dependencies.
4. Update every version anchor in the same change: version file, manifest requirement, package-manager declaration, documentation, and future CI variable.
5. Regenerate only the relevant lock file with the pinned tool version. Never hand-edit a lock file.
6. Run `scripts/check.ps1` on Windows or `sh scripts/check.sh` on POSIX, then verify a clean-cache install before merging.
7. If validation fails, restore the manifest and lock file together. Do not retain a partially upgraded graph.

## Reproducible commands

```powershell
# Windows, after activating Node 22.23.2 and uv 0.12.7
corepack pnpm install --frozen-lockfile
uv sync --locked --all-packages
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

```sh
# POSIX, after activating Node 22.23.2 and uv 0.12.7
corepack pnpm install --frozen-lockfile
uv sync --locked --all-packages
sh scripts/check.sh
```

Caches, `.venv`, `node_modules`, credentials, and generated coverage output must remain untracked.
