"""Report a source-method gap against the same frozen needs used to adopt a world rule."""
from nw.materials.phase_schema import array, obj
from nw.production_methods.contracts import at, require
from nw.production_methods.world_design import check_basis


def schema(target: dict) -> dict:
    """An alternate whole-stage reply when none of the supplied methods applies."""
    ids = [candidate['method']['id'] for candidate in target['candidates']]
    require(bool(ids), '只有实际提供了候选才能逐项报告世界方法缺口')
    text = {'type': 'string', 'minLength': 1}
    basis = obj({'kind': {'enum': ['type_adaptation', 'type_selection', 'brief']},
                 'path': {**array({'type': ['string', 'integer']}, 1), 'maxItems': 12}})
    exclusion = obj({'method_id': {'enum': ids}, 'reason': text})
    gap = obj({
        'design_basis': {**array(basis, 1), 'maxItems': 24},
        'exclusions': {**array(exclusion, len(ids)), 'maxItems': len(ids)},
        'missing': text,
    })
    return obj({'stage': {'const': 'world_design'}, 'world_method_gap': gap})


def _concrete(value: object) -> bool:
    if not isinstance(value, str):
        return False
    content = value.strip().strip('。.!！').strip()
    return bool(content) and content not in {'无', '未知', '待定', '待补充', '不适用', '不匹配', '不符合需求', '没有合适的方法'}


def validate_gap(value: object, target: dict) -> str:
    require(target.get('selection_mode') == 'ai' and target.get('stage') == 'world_design' and bool(target.get('candidates')),
            '仅在世界设计按当前前置自动挑选候选时可报告方法缺口')
    require(isinstance(value, dict) and set(value) == {'stage', 'world_method_gap'} and value['stage'] == 'world_design',
            '世界方法缺口须单独提交，不能同时发布设计卡或取材请求')
    gap = value['world_method_gap']
    require(isinstance(gap, dict) and set(gap) == {'design_basis', 'exclusions', 'missing'},
            '请提交实际前置依据、每种候选的不适用原因和仍缺的方法')
    check_basis(gap['design_basis'], target)
    reasons = gap['exclusions']
    offered = {row['method']['id']: row['method'] for row in target['candidates']}
    require(isinstance(reasons, list) and len(reasons) == len(offered), '须逐项核对本轮全部世界方法候选')
    missing = gap['missing']
    require(_concrete(missing), '请说明实际需要补哪种方法及其用途')
    details = []
    for row in reasons:
        require(isinstance(row, dict) and set(row) == {'method_id', 'reason'} and isinstance(row['method_id'], str)
                and row['method_id'] in offered, '排除记录须对应本轮候选且每种方法只出现一次')
        require(_concrete(row['reason']), '请说明该候选方法为何不适合当前前置需求')
        method = offered.pop(row['method_id'])
        title = method.get('body', {}).get('title') or method['id']
        details.append(f'《{title}》{row["reason"].strip()}')
    field = next(r for r in gap['design_basis'] if r['kind'] == 'type_adaptation')
    need = at(target['demand']['type_adaptation'], field['path'])
    return '\n'.join([f'METHOD_DESIGN_REQUIRED: 本轮候选均不适用。当前类型适配依据为「{need}」。',
                      f'需要补充的方法为「{missing.strip()}」。', *details])
