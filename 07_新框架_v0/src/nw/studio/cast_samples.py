"""Describe observed cast sizes in approved references of the requested genres."""
from hashlib import sha256
import json

from nw.studio import catalog
from nw.studio.corpus_cast import cast_distribution
from nw.studio.corpus_catalog import SCHEMA_VERSION


def _range(values) -> dict | None:
    items = list(values)
    return {'min': min(items), 'max': max(items)} if items else None


def _category_ranges(rows: list[dict], field: str) -> dict:
    keys = sorted({k for row in rows for k in row[field]})
    return {key: _range(row[field].get(key, 0) for row in rows) for key in keys}


def _chapter_ranges(chapters: list[dict]) -> dict:
    return {key: _range(row[key + '_count'] for row in chapters) for key in ('appearing','first','returning')}


def genre_cast_samples(library, types: list[str]) -> dict:
    selected = catalog.canonical_types(types)
    groups = {name: [] for name in ('opening', 'middle', 'ending')}
    complete, chapters, sources = [], [], []
    seen = set()
    with library.connect() as conn:
        books = conn.execute("""
            SELECT b.*, h.approved_version AS version
            FROM staging_books b JOIN corpus_structures h ON h.book_id=b.id
            JOIN corpus_structure_versions v ON v.book_id=b.id AND v.version=h.approved_version
            LEFT JOIN corpus_jobs j ON j.id=v.job_id
            WHERE b.status!='rejected' AND json_extract(v.body_json,'$.schema_version')=?
              AND coalesce(json_extract(j.runtime_json,'$.provider'),'') NOT IN ('fake','test-only')
            ORDER BY CASE json_extract(v.body_json,'$.source_extent.status') WHEN 'complete' THEN 0 ELSE 1 END,
                     b.title,b.id
        """, (SCHEMA_VERSION,)) if selected else ()
        for book in books:
            if (not set(selected).issubset(json.loads(book['confirmed_types_json']))
                    or any(book[k].strip().startswith('[FAKE]') for k in ('title','filename'))):
                continue
            record = library._corpus_row(book['id'], book['version'], conn)
            if not record['available']:
                continue
            counts = cast_distribution(record['body'])
            if not counts or counts['unique_count'] is None:
                continue
            # An alternate whitespace edition of the same source counts once.
            text = library._book_text(book)
            identity = sha256(''.join(text.split()).encode('utf-8')).digest()
            if identity in seen or text.lstrip().startswith('[FAKE]'):
                continue
            seen.add(identity)
            all_chapters = counts['chapters']
            covered = [chapter for chapter in all_chapters if chapter['observed']]
            chapters.extend(covered)
            extent = record['body']['source_extent']['status']
            full = extent == 'complete' and len(covered) == len(all_chapters)
            if full:
                complete.append(counts)
                if len(covered) > 1:
                    for i, chapter in enumerate(covered):
                        frac = i / (len(covered) - 1)
                        band = 'opening' if frac < 1/3 else 'ending' if frac > 2/3 else 'middle'
                        groups[band].append(chapter)
            sources.append({'book_id':book['id'], 'title':book['title'], 'version':book['version'], 'extent':extent,
                            'chapter_count':len(covered), 'unique_count':counts['unique_count'],
                            'included_in_book_range':full, 'body_sha256':record['body_sha256']})
    labels = library.corpus_catalog().get('cast_roster_options', {})
    return {'types':selected, 'status':'observed' if sources else 'no_samples' if selected else 'no_types',
            'sample_count':len(sources), 'complete_count':len(complete), 'chapter_count':len(chapters),
            'book_range':_range(row['unique_count'] for row in complete),
            'position_ranges':_category_ranges(complete,'positions'), 'function_ranges':_category_ranges(complete,'functions'),
            'chapter_ranges':_chapter_ranges(chapters),
            'chapter_bands':{key:{'chapter_count':len(rows), **_chapter_ranges(rows),
                                  'positions':_category_ranges(rows,'positions'), 'functions':_category_ranges(rows,'functions')}
                             for key,rows in groups.items()},
            'position_labels':labels.get('standing',{}), 'function_labels':labels.get('function_kind',{}), 'sources':sources}


def design_reference(sample: dict) -> dict:
    """Keep the model input bounded as the reference library grows."""
    if not sample['sample_count']:
        return {}
    bands = {}
    for key, row in sample['chapter_bands'].items():
        if row['chapter_count']:
            band = {k: row[k] for k in ('chapter_count','appearing','first','returning')}
            for field in ('positions','functions'):
                band[field] = {name: [span['min'],span['max']] for name,span in row[field].items()}
            bands[key] = band
    return {k: sample[k] for k in ('types','sample_count','complete_count','chapter_count','book_range',
                                   'position_ranges','function_ranges','chapter_ranges')} | {
        'chapter_bands':bands,
        'source_set_sha256':sha256(json.dumps(sample['sources'], sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        'sources':[{k:s[k] for k in ('book_id','version')} for s in sample['sources'][:3]],
        'instruction':'本组为同类型参考作品实见人数范围。完整作品前中后三段的地位和职责分别给出逐章[最少,最多]。按本书剧情和已有人物决定复用、引入或推迟出场；'
                      '章内首次指该参考文本内首次观察，样本少或仅有摘录时保留不确定性。不得按人数配额造人。'}
