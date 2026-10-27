"""Module execution support for ``python -m accos.entrypoints.worker``."""

from accos.entrypoints.worker import main  # pragma: no cover

raise SystemExit(main())  # pragma: no cover - exercised by process smoke tests.
