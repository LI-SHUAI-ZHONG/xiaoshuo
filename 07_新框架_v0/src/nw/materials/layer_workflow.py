"""Current-project translations and independent effect judgments for paired layers."""
from nw.task_models import _text

APPLICATION_FIELDS = {'trigger', 'operation', 'result', 'verification'}
PROMPT = (
    '有 layer_contract 的检查另回 layer_check，含 status（pass/failed/unverified）、reason、evidence。'
    '对照当前获批 layer_application 和原文，判断转译是否保持原义、条件与作用对象，'
    '且 result 所述效果是否在真实稿件成立。引用证据格式与同条检查相同。'
    '被拒绝的运行层字段和旧授权不作为执行依据；叙述检查评估叙述，流程规则核查阶段产物。'
)


def has_layers(row: dict) -> bool:
    return bool(row.get('review', {}).get('layer_contract', {}).get('execution'))


def validate_application(value: object, row: dict) -> None:
    if not has_layers(row):
        return
    application = value.get('layer_application') if isinstance(value, dict) else None
    if (not isinstance(application, dict) or set(application) != APPLICATION_FIELDS
            or any(not _text(text) or len(''.join(text.split())) < 8
                   or text.strip() in {row['source']['key'], row['source']['id'], '按原文要求逐条执行'}
                   for text in application.values())
            or len(set(application.values())) != len(APPLICATION_FIELDS)):
        raise ValueError('MATERIAL_TRANSLATION: explain the actual project trigger, operation, effect and verification')


def validate_layer_check(value: object) -> dict:
    if (not isinstance(value, dict) or set(value) != {'status', 'reason', 'evidence'}
            or value['status'] not in ('pass', 'failed', 'unverified')
            or not _text(value['reason']) or not isinstance(value['evidence'], list)):
        raise ValueError('MATERIAL_TRANSLATION_EVIDENCE: independent translation and effect result is required')
    return value
