"""Author decisions linked from the current reference workflow."""
from nw.studio.corpus_catalog import SCHEMA_VERSION


def review_queue(library) -> dict:
    with library.connect() as conn:
        classifications = conn.execute("""
            SELECT id, title FROM staging_books WHERE status='pending_review'
            ORDER BY updated_at DESC, id
        """).fetchall()
        structures = conn.execute("""
            SELECT b.id, b.title, v.version
            FROM staging_books b JOIN corpus_structures h ON h.book_id=b.id
            JOIN corpus_structure_versions v ON v.book_id=b.id AND v.version=h.latest_version
            LEFT JOIN corpus_structure_reviews r ON r.book_id=b.id AND r.version=v.version
            WHERE b.status NOT IN ('rejected','pending_review') AND r.book_id IS NULL
              AND json_extract(v.body_json,'$.schema_version')=?
              AND NOT EXISTS (SELECT 1 FROM corpus_jobs j WHERE j.book_id=b.id AND j.kind='structure'
                              AND j.status IN ('pending','running'))
            ORDER BY v.created_at DESC, b.id
        """, (SCHEMA_VERSION,)).fetchall()
        methods = conn.execute("""
            SELECT m.id, v.version, json_extract(v.body_json,'$.title') AS title
            FROM production_methods m
            JOIN production_method_versions v ON v.method_id=m.id AND v.version=m.latest_version
            JOIN corpus_method_origins o ON o.method_id=m.id AND o.method_version=v.version
            JOIN corpus_structures h ON h.book_id=o.book_id AND h.approved_version=o.structure_version
            JOIN corpus_structure_versions s ON s.book_id=o.book_id AND s.version=o.structure_version
            JOIN staging_books b ON b.id=o.book_id
            LEFT JOIN production_method_reviews r ON r.method_id=m.id AND r.version=v.version
            WHERE b.status!='rejected' AND r.method_id IS NULL AND json_extract(s.body_json,'$.schema_version')=?
            ORDER BY v.created_at DESC, m.id
        """, (SCHEMA_VERSION,)).fetchall()
    return {'classifications': [dict(r) for r in classifications], 'structures': [dict(r) for r in structures],
            'methods': [dict(r) for r in methods]}
