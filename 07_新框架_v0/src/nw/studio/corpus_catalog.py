"""Analytical fields describe observations and inferences, never universal quotas."""
from copy import deepcopy
from nw.studio.corpus_passages import CRAFT_KINDS, KINDS
from nw.studio.corpus_story_observations import STORY_DETAILS

SCHEMA_VERSION = 5
DOMAINS = {'main_plot': '全书主线', 'subplot': '支线与交汇', 'character_arc': '人物弧光',
           'hook': '钩子与回应', 'foreshadow': '伏笔与回收', 'information': '信息披露', 'pacing': '节奏与情绪',
           'world_rules': '世界规则、制度与资源约束', 'narration': '叙述时序、视角与呈现',
           'chapter_progress': '章场进展与跨章承接', 'cast_entry': '人物出场、剧情职责与身份披露',
           'cast_roster': '角色数量、种类与章节分布'}
CAST_ROSTER_OPTIONS = {
    'presence': {'onstage':'在本章事件中出场', 'mentioned':'本章仅提及', 'unknown':'无法判断是否出场'},
    'subject_kind': {'individual':'可区分的个人', 'group':'未拆分的群体', 'unknown':'个体归属不明'},
    'standing': {'protagonist':'主角','antagonist':'反派','major':'重要角色','supporting':'配角','ordinary':'普通角色','unknown':'全书地位未明'},
    'function_kind': {'driver':'推动事件','opponent':'构成阻力','ally':'协助行动','informant':'提供信息','handoff':'接洽交接','witness':'见证','other':'其他具体职责','unknown':'本章职责未明'},
}
NARRATION_CLAIMS = {'stated': '叙述明确交代的事实', 'attributed': '人物说法、记忆或信念',
                    'inferred': '分析者依据文字推断', 'unknown': '当前原文无法确定'}
LEVELS = {'book': '全书', 'volume': '卷', 'chapter': '章', 'scene': '场景'}
LINKS = {'causes': '导致', 'enables': '提供条件', 'opposes': '形成阻力', 'responds': '回应问题',
         'escalates': '升级问题', 'foreshadows': '埋设 / 暗示', 'hints': '再次提示',
         'pays_off': '回收兑现', 'reveals': '揭示信息', 'changes_character': '促成人物变化',
         'emotional_shift': '情绪转换', 'crosses': '主支线交汇'}
DETAILS = {
    'main_plot': {'central_question': '总问题', 'protagonist_goal': '主角目标', 'resistance': '主要阻力',
                  'stakes': '风险与代价', 'ending_payoff': '结局兑现'},
    'subplot': {'goal': '支线目标', 'function': '叙事职责', 'crossing': '交汇事件及作用', 'mainline_effect': '对主线的实际影响'},
    'character_arc': {'want': '人物欲望', 'belief_before': '初始信念 / 边界', 'pressure': '压力',
                      'decisive_choice': '关键选择', 'cost': '变化代价', 'belief_after': '最终变化'},
    'hook': {'question': '悬念 / 利益 / 危险', 'reader_expectation': '读者期待', 'response': '实际回应', 'escalation': '后续升级'},
    'foreshadow': {'setup': '埋设内容', 'expected_meaning': '预期含义', 'hints': '提示与误读',
                   'payoff': '实际回收', 'window_basis': '跨章位置与窗口依据'},
    'information': {'reader_before': '读者原先所知', 'reader_after': '读者后来所知',
                    'character_before': '人物原先所知', 'character_after': '人物后来所知', 'disclosure_order': '披露次序与效果'},
    'pacing': {'sequence': '事件节奏序列', 'tension_release': '紧张与释放', 'emotional_triggers': '情绪触发',
               'transitions': '章场转换', 'scope_basis': '统计 / 判断范围与限制'},
    'world_rules': {'rule': '原文可核对的运行规律、制度或资源门槛',
                    'scope': '约束谁、需要哪些条件、由谁或何物执行',
                    'boundary': '适用边界、例外或原文尚未说明的部分',
                    'decision_effect': '受约束的事件、选择及其实际后果'},
    'narration': {'time_order': '事件何时发生、读者何时得知；回到当下的落点',
                  'presentation': '这一段怎样讲述（如概述事实、重演过程、人物交流、内心或观察）',
                  'voice_access': '谁在讲、看、说或想；谁听得见、只能推测或还不知道',
                  'claim_status': '所述内容的证据性质', 'causal_basis': '前因与后果、原文怎样支持，或联系仍待证',
                  'character_response': '人物注意到什么、如何理解、怎样表达，回应带来了什么',
                  'reader_effect': '读者由哪些话明白什么、还在等待什么'},
    **STORY_DETAILS,
    'cast_roster': {'presence':'在场或仅提及', 'subject_kind':'个人、群体或归属未明',
                    'standing':'全书角色地位', 'function_kind':'本事件的剧情职责', 'chapter_function':'本章具体怎样发挥作用',
                    'appearance_evidence':'本次在场或提及的本章证据编号', 'standing_evidence':'判定全书地位的证据编号（未明留空）'},
}
FIELDS = {
    'units': {'id': '标识', 'level': '层级', 'title': '标题', 'parent_id': '上级', 'start': '字符起点',
              'end': '字符终点', 'boundary_basis': '边界依据（见 boundary_bases，场景填 analyst_inference）', 'summary': '本层职责 / 内容'},
    'characters': {'id': '标识', 'name': '人物', 'canonical_id': '同一人物的归并标识（未知填 null）', 'role': '作用', 'goal': '目标',
                   'initial_state': '初态', 'final_state': '末态', 'evidence_ids': '原作证据'},
    'events': {'id': '标识', 'unit_id': '所属卷章场', 'granularity': '总览 / 细节',
        'parent_event_ids': '对应总览节点', 'story_order': '故事时间顺序（未知填 null）', 'summary': '实际事件',
        'characters': '参与人物', 'goal': '目标', 'conflict': '阻力 / 冲突', 'choice': '选择', 'cost': '代价',
        'result': '结果', 'information_before': '事前所知', 'information_after': '事后所知',
        'emotion_before': '事前情绪', 'emotion_after': '事后情绪', 'evidence_ids': '原作证据'},
    'threads': {'id': '标识', 'domain': '制作职责', 'title': '线索 / 弧光名称', 'status': '未决 / 已兑现 / 存疑',
        'characters': '对应人物', 'node_ids': '有顺序的事件节点', 'initial_state': '进入状态',
        'final_state': '离开状态', 'explanation': '作用及不确定处', 'details': '具体分析', 'evidence_ids': '原作证据'},
    'links': {'id': '标识', 'kind': '关系', 'source': '前事件', 'target': '后事件', 'thread_id': '对应线索 / 弧光',
        'explanation': '为什么成立', 'certainty': '直接观察 / 分析推断', 'evidence_ids': '多处原作证据'},
    'evidence': {'id': '标识', 'start': '字符起点（唯一摘录可省略）', 'end': '字符终点（唯一摘录可省略）', 'quote': '原文短摘录', 'explanation': '证明什么'},
    'domains': {'domain': '制作职责', 'status': '已观察 / 当前范围未见 / 存疑',
                'explanation': '判断依据与限制', 'evidence_ids': '原作证据（未见或存疑可为空数组）'},
}
SURVEY_FIELDS = ('characters','events','evidence','uncertainties')
OVERVIEW = {'central_question': '全书总问题', 'mainline': '主线因果与结局', 'character_arcs': '主要人物变化',
            'information_payoffs': '信息与承诺兑现', 'structure': '卷章组织及转折', 'limitations': '未知与覆盖限制'}


def domains_for(version: int) -> dict:
    if type(version) is not int or not 1 <= version <= SCHEMA_VERSION:
        raise ValueError('不支持的拆解结构版本')
    added = {'world_rules': 2, 'narration': 3, **dict.fromkeys(STORY_DETAILS, 4), 'cast_roster':5}
    return {key: value for key, value in DOMAINS.items() if added.get(key, 1) <= version}


def require_current_schema(version: int | None) -> None:
    if version != SCHEMA_VERSION:
        raise ValueError(f'来源采用历史拆解规格 v{version or 1}，请先按现行 v{SCHEMA_VERSION} 补齐并批准结构后再用于新制作')


def corpus_catalog(version: int = SCHEMA_VERSION, *, passages: bool = True, craft: bool = True,
                   include_blueprint: bool = False) -> dict:
    domains = domains_for(version)
    techniques = KINDS | CRAFT_KINDS if craft else KINDS
    result = {'schema_version': version, 'domains': domains, 'levels': LEVELS, 'link_kinds': LINKS,
        **({'passage_sequences':{kind:{**deepcopy(item),'role_order':list(item['roles'])}
                                 for kind,item in techniques.items()}} if version>=5 and passages else {}),
        **({'evidence_roles':{'narrative':'故事正文', 'reader_address':'面向读者的题外互动', 'heading':'章名与标题'}}
           if version>=5 and craft else {}),
        **({'cast_roster_options':deepcopy(CAST_ROSTER_OPTIONS)} if version >= 5 else {}),
        **({'narration_claims': NARRATION_CLAIMS.copy()} if version >= 3 else {}),
        'overview_fields': OVERVIEW, 'row_fields': deepcopy(FIELDS), 'domain_details': {k: deepcopy(DETAILS[k]) for k in domains},
        'source_extents': {'complete': '作者确认完整作品', 'excerpt': '摘录 / 不完整文本', 'unknown': '完整性未确认'},
        'boundary_bases': {'source_file': '原始文件', 'source_heading': '原文标题', 'analyst_inference': '分析推断', 'author_confirmed': '作者核对'},
        'thread_statuses': {'open': '未决', 'resolved': '已兑现 / 已结束', 'uncertain': '存疑'},
        'domain_statuses': {'observed': '已观察', 'not_observed': '当前覆盖范围未见', 'uncertain': '存疑'},
        'certainty': {'observed': '直接观察', 'inferred': '分析推断'},
        'granularity': {'overview': '全书总览节点', 'detail': '章场细节节点'},
        'phases': {'survey': '通读原文', 'overview': '整合全书结构', 'detail': '卷章场细拆',
                   'relations': '跨章关系核对', 'methods': '提炼可复用方法', 'publish': '保存待审核版本'},
        'notes': ['读过全部已导入字符不代表原作本身完整，也不代表文学分析正确。',
                  '原始观察、分析推断与可迁移方法分开；新方法仍须单独审核。']}
    if include_blueprint:
        from nw.studio.corpus_direct import TARGETED_TRACKS
        from nw.studio.step_material_blueprint import (
            DECOMPOSITION_METHODOLOGY,
            MATERIAL_NATURES,
            domain_bindings,
        )
        result['decomposition_methodology'] = deepcopy(DECOMPOSITION_METHODOLOGY)
        result['material_natures'] = list(deepcopy(MATERIAL_NATURES).values())
        result['domain_bindings'] = domain_bindings(version)
        result['targeted_tracks'] = list(deepcopy(TARGETED_TRACKS).values())
    return result
