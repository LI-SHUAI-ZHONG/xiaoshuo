# Network Connection Audit

- status: **REVIEW_REQUIRED**
- static actual connections: 1341
- dynamic original connections: 483
- dynamic generated connections: 1341
- dynamic final connections: 1824
- static-only connections: 0
- dynamic-only connections: 483
- needs review: 1341
- unresolved aliases: 177

## Reasons

- Static-derived dynamic records have unknown semantic fields and require review.
- Node names with the same numeric prefix were not merged automatically.
- Dynamic-only records are not present in the static source map.
- Dynamic-only classification counts: {"likely_alias_match": 215, "conflicting_semantics": 145, "missing_static_connection": 118, "invalid_or_unclear": 5}
- Generated field-source gaps: 0
