"""Read-only source ingestion; approved line spans are kept for offline replay."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from nw.store import Store
from nw.story_models import CardRef, SourceRef, SourceVersion
from nw.task_models import content_sha256


class SourceQuarantined(ValueError):
    def __init__(self, source_id: str, status: str) -> None:
        self.source_id, self.status = source_id, status
        super().__init__(f'Source quarantined: {status} ({source_id})')


def text_sha256(text: str) -> str:
    return sha256(text.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class _Source:
    id: str
    relative_path: str
    file_sha256: str
    byte_size: int
    status: str
    text: str

    def lines(self) -> list[str]:
        pieces = self.text.split('\n')
        return [line + '\n' for line in pieces[:-1]] + ([pieces[-1]] if pieces[-1] else [])


def _load_source(path: Path, root: Path) -> _Source:
    # Adapted from ACCOS KnowledgeService._extract_and_normalize. Preserve whitespace
    # and original line numbering; normalize only BOM and line terminators.
    root = root.resolve()
    resolved = (path if path.is_absolute() else root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('Source path is outside the repository root')
    relative = resolved.relative_to(root).as_posix()
    data = resolved.read_bytes()
    digest = sha256(data).hexdigest()
    status, text = 'READY', ''
    if b'\0' in data:
        status = 'NUL'
    else:
        try:
            text = data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
        except UnicodeDecodeError:
            status = 'INVALID_ENCODING'
        if status == 'READY' and not text.strip():
            status = 'EMPTY'
    return _Source(content_sha256([relative, digest]), relative, digest, len(data), status, text)


def _insert_version(store: Store, source: _Source) -> None:
    store.connection.execute(
        'INSERT INTO source_versions VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
        (source.id, source.relative_path, source.file_sha256, source.byte_size,
         None if source.status in ('NUL', 'INVALID_ENCODING') else 'utf-8-sig', source.status))


def _span(source: _Source, lines: list[str], start: int, end: int) -> tuple[SourceRef, str]:
    if source.status != 'READY':
        raise SourceQuarantined(source.id, source.status)
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise ValueError('Invalid source line range')
    text = ''.join(lines[start - 1:end])
    if not text.strip():
        raise ValueError('Empty source span')
    return SourceRef(source.id, start, end, text_sha256(text)), text


def _insert_span(store: Store, ref: SourceRef, text: str) -> None:
    # ACCOS KnowledgeService._chunk also uses source-version identity plus content digest.
    span_id = content_sha256([ref.source_id, ref.start_line, ref.end_line, ref.span_sha256])
    store.connection.execute(
        'INSERT INTO source_spans VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
        (span_id, ref.source_id, ref.start_line, ref.end_line, ref.span_sha256, text))


def register_source(store: Store, path: Path, root: Path, *,
                    start_line: int = 1, end_line: int | None = None) -> SourceRef:
    """Freeze the requested range (whole file by default); quarantine unreadable data."""
    source = _load_source(path, root)
    if source.status != 'READY':
        with store.connection:
            _insert_version(store, source)
        raise SourceQuarantined(source.id, source.status)
    lines = source.lines()
    ref, text = _span(source, lines, start_line, len(lines) if end_line is None else end_line)
    with store.connection:
        _insert_version(store, source)
        _insert_span(store, ref, text)
    return ref


def read_source_version(store: Store, source_id: str) -> SourceVersion:
    row = store.connection.execute(
        'SELECT id,relative_path,file_sha256,byte_size,encoding,status FROM source_versions WHERE id=?',
        (source_id,)).fetchone()
    if row is None:
        raise ValueError('Source version not found')
    return SourceVersion(*row)


def read_span(store: Store, ref: SourceRef) -> str:
    if (not isinstance(ref.source_id, str) or not ref.source_id or
            type(ref.start_line) is not int or type(ref.end_line) is not int or
            not 1 <= ref.start_line <= ref.end_line):
        raise ValueError('Invalid source reference')
    row = store.connection.execute(
        """SELECT s.text,s.span_sha256 FROM source_spans s JOIN source_versions v ON v.id=s.source_id
           WHERE s.source_id=? AND s.start_line=? AND s.end_line=? AND v.status='READY'""",
        (ref.source_id, ref.start_line, ref.end_line)).fetchone()
    if row is None:
        raise ValueError('Source span not registered or not usable')
    if row['span_sha256'] != ref.span_sha256 or text_sha256(row['text']) != ref.span_sha256:
        raise ValueError('Source span hash mismatch')
    return row['text']


def import_seed_cards(store: Store, path: Path, *, root: Path | None = None) -> list[CardRef]:
    from nw.seed_import import import_manifest

    return import_manifest(store, path, root=root)


def import_rule_cards(store: Store, path: Path, *, root: Path | None = None) -> list[CardRef]:
    from nw.seed_import import import_manifest

    return import_manifest(store, path, root=root, rules_only=True)
