from dataclasses import replace
from pathlib import Path

import pytest

from nw.store import Store


def test_duplicate_number_keeps_distinct_source_versions(tmp_path: Path) -> None:
    from nw.sources import read_source_version, read_span, register_source

    source = tmp_path / 'rules.txt'
    with Store(tmp_path / 'db', create=True) as store:
        source.write_bytes('5.6 第一处\r\n5.6 第二处\n'.encode())
        first = register_source(store, source, tmp_path, start_line=1, end_line=1)
        other = register_source(store, source, tmp_path, start_line=2, end_line=2)
        copy = tmp_path / 'copy.txt'
        copy.write_bytes(source.read_bytes())
        copied = register_source(store, copy, tmp_path, start_line=1, end_line=1)
        assert first.source_id != copied.source_id
        source.write_text('5.6 新版本\n', encoding='utf-8')
        second = register_source(store, source, tmp_path)
        assert first.source_id != second.source_id
        source.unlink()
        old = read_source_version(store, first.source_id)
        assert old.relative_path == 'rules.txt' and old.status == 'READY'
        assert old.file_sha256 != read_source_version(store, second.source_id).file_sha256
        assert read_span(store, first) == '5.6 第一处\n'
        assert read_span(store, other) == '5.6 第二处\n'
        assert read_span(store, second) == '5.6 新版本\n'
        with pytest.raises(FileNotFoundError):
            register_source(store, source, tmp_path)


@pytest.mark.parametrize(('data', 'status'), [(b'x\x00y', 'NUL'), (b'\xff', 'INVALID_ENCODING'), (b' \n', 'EMPTY')])
def test_bad_source_is_quarantined(tmp_path: Path, data: bytes, status: str) -> None:
    from nw.sources import SourceQuarantined, register_source

    source = tmp_path / 'source.txt'
    source.write_bytes(data)
    with Store(tmp_path / 'db', create=True) as store:
        with pytest.raises(SourceQuarantined) as error:
            register_source(store, source, tmp_path)
        assert error.value.status == status
        row = store.connection.execute('SELECT status FROM source_versions WHERE id=?', (error.value.source_id,)).fetchone()
        assert row[0] == status
        assert not store.connection.execute('SELECT * FROM source_spans').fetchall()


def test_span_roundtrip_and_hash(tmp_path: Path) -> None:
    from nw.sources import read_span, register_source

    path = tmp_path / 'rules.txt'
    path.write_bytes('甲\r\n乙\r末'.encode())
    with Store(tmp_path / 'db', create=True) as store:
        ref = register_source(store, path, tmp_path, start_line=2, end_line=2)
        assert read_span(store, ref) == '乙\n'
        with pytest.raises(ValueError, match='hash'):
            read_span(store, replace(ref, span_sha256='0' * 64))
        with pytest.raises(ValueError, match='outside'):
            register_source(store, path, tmp_path / 'db')
        row = store.connection.execute('SELECT COUNT(*) FROM source_spans').fetchone()
        assert row[0] == 1
