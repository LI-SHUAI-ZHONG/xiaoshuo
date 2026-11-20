"""Project evidence shared by the world resource rules."""
import re


POLICY = 'world-resource-prerequisites-v1'
_WITHDRAWN = re.compile(
    r'(?:本卡|本规则|上述规则|该规则)(?:已|现已)?(?:停用|撤销|废止|取消)(?:[。；，,;]|$)|'
    r'(?:本项目|本作)(?:已|决定)?(?:撤销|废止|取消|不采用|不再采用)(?:本卡|上述规则|该规则|本资源规则)')


def resource_families() -> tuple:
    from nw.materials import world_resource_cycle, world_resource_scarcity, world_resource_types

    return ((world_resource_cycle.RULES, world_resource_cycle.approved_resource_cycle),
            (world_resource_types.RULES, world_resource_types.approved_resource_type),
            (world_resource_scarcity.RULES, world_resource_scarcity.approved_scarcity))


def approved_text(card: dict) -> tuple[str, str] | None:
    if (not isinstance(card, dict) or card.get('kind') != 'world' or card.get('status') != 'approved'
            or not isinstance(card.get('card_id'), str) or not card['card_id'].strip()
            or type(card.get('version')) is not int or card['version'] < 1):
        return None
    body = card.get('body')
    if not isinstance(body, dict):
        return None
    rule, limits = body.get('rule'), body.get('limits')
    if not all(isinstance(text, str) and text.strip() and not _WITHDRAWN.search(text) for text in (rule, limits)):
        return None
    return rule, limits


def card_proof(card: dict, rule: str, limits: str, evidence: dict) -> dict:
    ident = card['card_id']
    return {'card_id': ident, 'version': card['version'], 'rule': rule, 'limits': limits,
            'rule_ref': f'approved:{ident}:/body/rule', 'limits_ref': f'approved:{ident}:/body/limits',
            'evidence': evidence}
