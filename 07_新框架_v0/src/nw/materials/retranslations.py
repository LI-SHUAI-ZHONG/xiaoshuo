"""Explicit, hash-pinned functional replacements; frozen source bytes stay intact."""
from hashlib import sha256
import sqlite3

REPAIRS = {
    'b7726fb4d79548ad0149b8c3ffac7a5ebccd50c6ea70c48053fc7b1f82931c20': {
        'file_sha256': '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed',
        'sha256': 'a73e4c1f934d1fe55a71587f065efc0009424b79c2b8a23ee306c797620ae85d',
        'definition_id': 'bfc45fe9c88aa379b22006eb1d52596e0b6c370348036575e794d782c2bfedf9',
        'definition_sha256': '13d4bd01f140528b7b51a8cce379d57fecfc54e448aec0aa2e0ffda310f2c83f',
        'evidence_scope': 'book',
        'reason': '原定义明确比较不同章节叙述语言的句式、用词、叙述距离；角色身体信号、情绪压抑及一秒识别改变了作用对象。'
                  '运行层通用角色动作策略沿袭同一错位。依原定义重建全书叙述风格对照，节奏造成的合理差异保留解释。',
    }
}


def retranslate(db: sqlite3.Connection, row: dict, result: dict) -> dict:
    pin = REPAIRS.get(row['id'])
    if (not pin or row['layer'] != 'baseline' or result.get('owner_id') != row['id']
            or any(row[key] != pin[key] for key in ('file_sha256', 'sha256'))):
        return result
    definition = db.execute('SELECT * FROM material_units WHERE id=?', (pin['definition_id'],)).fetchone()
    fragment = db.execute('SELECT byte_start,payload FROM fragments WHERE id=?', (row['fragment_id'],)).fetchone()
    if definition is None or definition['fragment_id'] != row['fragment_id'] or definition['sha256'] != pin['definition_sha256']:
        raise ValueError('Retranslation definition pin differs from its source')
    data = fragment['payload'][definition['byte_start']-fragment['byte_start']:definition['byte_end']-fragment['byte_start']]
    if sha256(data).hexdigest() != definition['sha256']:
        raise ValueError('Retranslation definition hash mismatch')
    excluded = [dict(field) for field in db.execute("""SELECT id,kind,label,sha256 FROM material_units
        WHERE fragment_id=? AND origin='source' AND id<>? ORDER BY byte_start""", (row['fragment_id'], definition['id']))]
    contract = {'owner_id': row['id'], 'key': row['key'], 'definition': result['contract'].get('definition', []),
                'evidence_scope': {'kind': pin['evidence_scope'], 'complete_chapters_required': True,
                                   'author_scope_required': True}}
    return {**result, 'state': 'design_ready', 'can_offer_for_design': True, 'profile': 'scope_review',
            'meaning': data.decode('utf-8').strip(),
            'boundary': '这是根据明确原定义重建的执行用途，原件缺陷仍保留；须冻结全书范围，比较叙述而非人物状态。',
            'evidence_required': '引用完整书稿范围各章的叙述，比较句式、用词、叙述距离，并解释因节奏产生的合理变化。',
            'contract': contract, 'conflicts': [], 'missing': [],
            'source_retranslation': {'method': 'definition_grounded_retranslation', 'reason': pin['reason'],
                'adopted_fields': [definition['id']], 'excluded_fields': excluded,
                'original_state': result['state'], 'original_missing': result.get('missing', []),
                'original_conflicts': result.get('conflicts', []),
                'source_pin': {key: row[key] for key in ('id', 'file_sha256', 'sha256')}}}
