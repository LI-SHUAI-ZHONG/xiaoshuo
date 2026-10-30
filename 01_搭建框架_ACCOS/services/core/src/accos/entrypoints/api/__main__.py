"""Module execution support for ``python -m accos.entrypoints.api``."""

from accos.entrypoints.api import main  # pragma: no cover

raise SystemExit(main())  # pragma: no cover - exercised by process smoke tests.
