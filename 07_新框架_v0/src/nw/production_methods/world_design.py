"""Validate which project need and which new world rule an AI method actually serves."""
from nw.production_methods.contracts import at, require


def check_basis(rows: object, target: dict) -> None:
    require(isinstance(rows, list) and 0 < len(rows) <= 24, '世界方法须引用本轮具体的类型适配需求')
    found_adaptation = False
    seen = set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'kind', 'path'}, '需求依据须含前置名称和字段路径')
        kind, path = row['kind'], row['path']
        require(isinstance(kind, str) and kind in target['demand'], '需求依据不属于本次世界设计')
        value = at(target['demand'][kind], path)
        ident = (kind, tuple(path))
        require(ident not in seen, '需求依据重复')
        seen.add(ident)
        if kind == 'type_adaptation':
            valid = (len(path) >= 4 and path[0] == 'adaptations' and type(path[1]) is int
                     and path[1] in target['adaptation_indices'] and path[2] in ('parameters', 'limits'))
            require(valid, '应指向与实际选型匹配的适配参数或限制')
            found_adaptation = True
        elif kind == 'brief':
            require(path in (['text'], ['constraints']), '应引用立项需求或约束的实际内容')
        else:
            require(kind == 'type_selection' and len(path) >= 3 and path[0] == 'selection'
                    and path[-1] not in ('id', 'source_ids'), '类型依据应引用实际选型内容')
        require((isinstance(value, str) and bool(value.strip())) or type(value) in (int, float, bool),
                '前置依据须指向具体值')
    require(found_adaptation, '世界设计遗漏了已冻结的本轮类型适配需求')


def check_world_output(rows: list[dict], products: dict, method: dict) -> set[int]:
    fields = {'rule', 'limits'}
    covered = {}
    for row in rows:
        path = row['path']
        require(len(path) >= 2 and path[0] == 'members' and type(path[1]) is int, '世界方法应落到具体世界卡')
        index = path[1]
        slot = covered.setdefault(index, set())
        if len(path) == 2 or path[2:] == ['body']:
            slot.update(fields)
        elif len(path) == 4 and path[2] == 'body' and path[3] in fields:
            slot.add(path[3])
    require(bool(covered), '采用世界方法须交付本书具体规则和适用限制')
    quotes = [''.join(e['quote'].split()) for e in method['body']['evidence']]
    source_rules = {''.join(detail.split()) for thread in method['instance']['threads']
                    if thread['domain'] == 'world_rules' for field in ('rule', 'boundary')
                    if isinstance(detail := thread['details'].get(field), str)}
    placeholders = {'待定', '未知', '无', '无条件', '待补充', '待设计', '由作者决定', '由作者设定'}
    for index, keys in covered.items():
        require(keys == fields, '每个采用方法的世界卡须同时交付规则和限制')
        body = products['members'][index]['body']
        texts = [''.join(body[k].split()) for k in ('rule', 'limits')]
        require(all(t and t.strip('。.!！') not in placeholders for t in texts) and texts[0] != texts[1],
                '世界规则和适用限制须分别说明本项目的实际设计')
        require(not any(len(q) >= 12 and q in t for t in texts for q in quotes)
                and not any(len(t) >= 8 and t in source_rules for t in texts),
                '原作证据不能整段复制为本书世界规则或限制')
    return set(covered)


def check_receipt(receipt: dict, products: dict, stage: str) -> None:
    if stage not in ('plot_design', 'scene_design'):
        return
    plot_fields = {'conflict', 'consequence', 'resistance', 'choice', 'cost', 'ending_direction'}
    scene_fields = {'goal', 'conflict', 'choice', 'planned_result', 'entering_state', 'allowed_disclosure'}
    placed = set()
    for row in receipt['placements']:
        path = row['path']
        if stage == 'plot_design' and path[0] == 'directions':
            if len(path) == 1:
                placed.update(range(len(products['directions'])))
            elif len(path) == 2 or path[2] in plot_fields:
                placed.add(path[1])
        if stage == 'scene_design' and path[0] == 'members' and len(path) >= 2:
            member = products['members'][path[1]]
            if member['kind'] != 'scene':
                continue
            if (len(path) == 2 or path[2:] == ['body']) and any(member['body'].get(k) for k in scene_fields):
                placed.add(member['key'])
            elif len(path) >= 4 and path[2] == 'body' and path[3] in scene_fields:
                placed.add(member['key'])
    if stage == 'plot_design':
        require(placed and placed == set(range(len(products['directions']))),
                '请在每个可选剧情方向的冲突、选择、代价或后果中承接世界规则')
    else:
        require(placed and placed == {g['scene'] for g in receipt['scene_guidance']},
                '世界规则须在同一场景落实到实际设计字段和写审交接')
