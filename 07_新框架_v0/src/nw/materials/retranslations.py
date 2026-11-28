"""Explicit, hash-pinned functional replacements; frozen source bytes stay intact."""
from hashlib import sha256
import re
import sqlite3

_LIBRARY_SHA256 = '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed'
_LIBRARY_SOURCE_ID = '92583cff03f6d4e5fd66dd4b5ec6ed7ba04103a92fd7a4e4a0cc4cc1e4e34c12'

REPAIRS = {
    'b7726fb4d79548ad0149b8c3ffac7a5ebccd50c6ea70c48053fc7b1f82931c20': {
        'file_sha256': _LIBRARY_SHA256,
        'sha256': 'a73e4c1f934d1fe55a71587f065efc0009424b79c2b8a23ee306c797620ae85d',
        'definition_id': 'bfc45fe9c88aa379b22006eb1d52596e0b6c370348036575e794d782c2bfedf9',
        'definition_sha256': '13d4bd01f140528b7b51a8cce379d57fecfc54e448aec0aa2e0ffda310f2c83f',
        'evidence_scope': 'book',
        'reason': '原定义明确比较不同章节叙述语言的句式、用词、叙述距离；角色身体信号、情绪压抑及一秒识别改变了作用对象。'
                  '运行层通用角色动作策略沿袭同一错位。依原定义重建全书叙述风格对照，节奏造成的合理差异保留解释。',
    }
}

_MISPASTED_DIRECTIVE = re.compile(
    r'作为角色决策的深层驱动，通过行为而非旁白呈现|'
    r'在场景中触发角色的.+?身体信号|'
    r'读者能否在1秒内通过身体信号识别出角色的'
)

_COMPLETION_NOTES = {
    '108.1_写作前检查': '写前状态衔接核查转为当前稿与上一已确认章节末尾的角色身体、精神、能量及关系状态一致性核验。',
    '109.5_叙述者声音': '补齐跨板块引用边界：叙述者声音四维（词汇、句式、态度、距离）在全书保持统一，跨章语体核验与板块106联动，情绪与节奏波动须有当场处境依据。',
    '112.7_结尾类型': '补齐结尾类型适用边界：封闭式、开放式、回环式与余韵式结尾须在终章前与开篇承诺及主线核心问题闭合方式对齐。',
    '119.6_成长轨迹认同': '补齐弧光五阶段核验序列：起点基准→触发打破→探索受挫→核心抉择转折→重塑定型，角色能力或认知跃迁须跨阶段留痕。',
    '119.10_读者自反时刻': '仅采用本条自身的读者自反定义（通过角色与读者的选择差异触发审视）；原片段后附的120–128夹入子项归各独立编号合同管辖。',
    '122.4_推进方式二：跳跃式推进': '补齐跳时重置衔接：跨时间或空间跳跃推进时，须按120.7与113.3在新场前三句内交代新观察者、锚定时间标记与当前行动处境。',
    '123.2_爆款标准模型': '补齐五要素协同边界：强开篇引力、清晰主线目标、持续信息差悬念、高频带代价爽点与鲜明人设声线须服务同一题材承诺。',
    '123.12_读者留存曲线': '补齐章尾钩子下限：连载期章尾默认保持中等以上悬念或局势钩子（对齐48.4），轻章弱钩子连续不得超过两章（对齐122.14）。',
    '127.4_设计到正文的转化路径': '补齐参数转化闭环：每项入选设计参数须映射为「场景前值→触发动作/台词→可观察正文结果→审稿核验点」，身体信号仅用于情绪外化条目。',
    '128.4_板块调用的三层筛选法': '补齐三层筛选闭环：先定本章/本场核心叙事功能→再选直接支撑该功能的板块→最终精确到必需子项并记录排除理由。',
    '板块140 角色未知性': '明确计数与使用边界：原指令“五类信息”实为「自己、他人、读者」三主体×「已知、未知」共六维知情矩阵；按六维核验信息获取与披露。',
}


def _retranslate_library_conflict(db: sqlite3.Connection, row: dict, result: dict) -> dict:
    contract = dict(result.get('contract') or {})
    first_embedded = None
    if (row.get('key') or '').startswith('119.10'):
        emb = db.execute(
            """SELECT MIN(byte_start) AS cut FROM material_units
               WHERE fragment_id=? AND kind IN ('embedded_entry','embedded_block') AND id<>?""",
            (row['fragment_id'], row['id']),
        ).fetchone()
        if emb and emb['cut'] is not None:
            first_embedded = int(emb['cut'])

    adopted_ids: list[str] = []
    excluded: list[dict] = []
    cleaned_contract: dict = {'owner_id': row['id'], 'key': row['key']}
    if 'evidence_scope' in contract:
        cleaned_contract['evidence_scope'] = contract['evidence_scope']

    list_keys = ('definition', 'directives', 'conditions', 'exceptions', 'checks', 'exclusions',
                 'alternatives', 'corrections', 'dependencies', 'grades', 'variations', 'mappings', 'notes', 'tags', 'identities')
    for cat in list_keys:
        items = contract.get(cat, [])
        if not isinstance(items, list):
            continue
        kept = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get('ref'), dict):
                continue
            ref = item['ref']
            uid = ref.get('id')
            text = str(item.get('text') or '')
            in_foreign_embedded = first_embedded is not None and int(ref.get('byte_start', 0)) >= first_embedded
            mispasted = cat in {'directives', 'checks'} and bool(_MISPASTED_DIRECTIVE.search(text))
            if in_foreign_embedded or mispasted:
                u_meta = db.execute('SELECT id,kind,label,sha256 FROM material_units WHERE id=?', (uid,)).fetchone()
                if u_meta is not None:
                    excluded.append(dict(u_meta))
                continue
            kept.append(item)
            if uid and uid not in adopted_ids:
                adopted_ids.append(uid)
        if kept or cat in contract:
            cleaned_contract[cat] = kept

    if not adopted_ids or not cleaned_contract.get('definition'):
        return result

    profile = result['profile']
    if profile == 'preflight':
        profile = 'prose_review'
    key = row.get('key') or ''
    extra_note = _COMPLETION_NOTES.get(key)
    if extra_note is None:
        for prefix, note in _COMPLETION_NOTES.items():
            if key.startswith(prefix.split('_')[0] + '_') and prefix.split('_')[0] in {'122.4', '123.2', '123.12', '127.4', '128.4'}:
                extra_note = note
                break

    defs = cleaned_contract.get('definition', [])
    meaning = str(defs[0].get('text') or result.get('meaning') or '').replace('\\', '').strip()[:300]
    boundary = (
        '已剥离原稿批处理错贴的角色动机/身体信号模板指令，按原定义、适用条件与判定标准重建本步契约。'
        + (f' {extra_note}' if extra_note else ' 原文未给定的项目对象、情境与数值须由当前作品设定明确。')
    )
    reason = (
        '原条目定义明确属于叙事、审稿、视角、篇幅或流程规范，批处理混入的角色决策/身体信号通用指令与原义冲突；'
        '保留原定义与同域核验条款并隔离错位指令。'
        if any(c.get('kind') == 'semantic_domain_conflict' for c in result.get('conflicts', []) if isinstance(c, dict))
        else '核定原条目的独立契约范围与六维知情口径，剥离夹入外板块字段或计数笔误后接入正常使用。'
    )
    return {
        **result,
        'state': 'design_ready',
        'can_offer_for_design': True,
        'profile': profile,
        'meaning': meaning,
        'boundary': boundary,
        'contract': cleaned_contract,
        'conflicts': [],
        'missing': [],
        'source_retranslation': {
            'method': 'definition_grounded_retranslation',
            'reason': reason,
            'adopted_fields': adopted_ids,
            'excluded_fields': excluded,
            'original_state': result['state'],
            'original_missing': result.get('missing', []),
            'original_conflicts': result.get('conflicts', []),
            'source_pin': {k: row[k] for k in ('id', 'file_sha256', 'sha256')},
        },
    }


def retranslate(db: sqlite3.Connection, row: dict, result: dict) -> dict:
    pin = REPAIRS.get(row['id'])
    if pin:
        if (row['layer'] != 'baseline' or result.get('owner_id') != row['id']
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
    if (row.get('family') == 'library' and row.get('layer') == 'baseline'
            and row.get('file_sha256') == _LIBRARY_SHA256
            and row.get('source_id') == _LIBRARY_SOURCE_ID
            and result.get('owner_id') == row['id']
            and result.get('state') == 'blocked'
            and not result.get('manual_reviewed')):
        return _retranslate_library_conflict(db, row, result)
    return result
