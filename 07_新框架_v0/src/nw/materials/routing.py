"""Source-aware dispositions and evidence requirements for F2."""
from dataclasses import dataclass
import re

from nw.materials.reviews import CHARACTER_EDITOR, source_review


POLICY = 'material-routing-v1'


@dataclass(frozen=True)
class Profile:
    stage: str
    purpose: str
    applies_when: str
    product: str
    evidence: str
    depends_on: tuple[str, ...] = ()


PROFILES = {
    'metadata': Profile('来源核验','结构、词表和定位','核对来源版本或解析结构','来源与结构记录','冻结来源哈希、路径和对象定位'),
    'history': Profile('版本对账','比较历史原义、结构及别名','存在新旧版本对照任务','差异与候选映射','两份原文位置、哈希、对照理由'),
    'derived': Profile('来源核验','核对派生数据与现行原件','同族网络原始边可回读','派生边对照','同一关系的原始边与派生边字段'),
    'upgrade_review': Profile('资料治理','校对升级、补全和旧授权','有原文和升级候选可对照','差异及裁定记录','同一对象双来源、差异与确认'),
    'source_issue': Profile('资料治理','定位缺口、错译和冲突','索引标记异常或已知冲突','问题记录','原文定位、问题与复核结论'),
    'example': Profile('资料治理','比较示例、反例和参考作品','需要核对方法的边界或比较效果','对照记录','例子出处与适用边界'),
    'test_fixture': Profile('回归测试','验证解析和规则边界','运行隔离回归','测试输入与预期','用例结果与夹具身份'),
    'empty': Profile('资料治理','登记空表或空集合','当前任务确实需要该数据','缺口或合法空集合裁定','原文位置、预期数据及处理'),
    'unresolved': Profile('资料治理','核对缺少对应的用途','已有定位但不能判定阶段','待核记录','原文、依赖和裁定理由'),
    'brief': Profile('立项','确认题材、要求和边界','项目启动或需求改变','创作需求单','作者决定、明示要求、待定项'),
    'type_identity': Profile('类型定向','识别类型本体、层级和读者承诺','需要选择类型或确定类型特征','类型契约','类型原文、作者所选类型及承诺',('立项',)),
    'type_expression': Profile('类型定向','将类型期待映射到场景和文风','已确认类型且任务涉及该表达','类型适配及卷章兑现计划','类型契约、预期效果和场景对照',('类型契约',)),
    'type_link': Profile('类型组合','检查组成类型的机制、兼容和冲突','两端类型已确认且条目条件成立','组合机制与冲突决定','两端类型、条件、选择、代价及失败分支',('类型契约',)),
    'type_combination': Profile('类型组合','将类型、机制、结构和风格共同绑定到项目','原文各组成项可定位且项目选型已确定','多维类型组合合同','组成项、条件、互相限制及项目兑现方式',('类型契约',)),
    'type_transition': Profile('场景设计','把类型动态方法或状态限制绑定为候选变化','原条件、采用类型和当前状态均已明确','有条件的状态变化与选择合同','目标实体、前后状态、行动代价、失败边界及同稿独立核验',('已采用类型','当前状态',)),
    'world': Profile('世界设定','形成世界规则和可行动边界','场景或项目需要相应的制度、力量或资源','世界规则与行动限制','作者确认的规则、代价和可观察后果',('类型契约',)),
    'character': Profile('人物设计','确定目标、动机、关系和状态','人物参与当前冲突或行动','人物动机与关系状态','前后状态和有因果依据的行动'),
    'plot': Profile('卷章设计','安排目标、节奏、选择和承接','卷章或场景确实承担相应推进功能','卷章因果与节拍','目标、行动、代价及后续承接'),
    'opening': Profile('卷章设计','确定开篇承诺和进入冲突的位置','正在设计开篇或复核首章节奏','开篇目标与节拍','开篇文本与约定的读者期待对应'),
    'static_binding': Profile('关系设计','将静态资料边绑定到项目实体','两端身份及关系适用范围已确认','静态关系和行动边界','原始两端、项目对象和关系证据',('类型组合','项目实体',)),
    'dynamic_binding': Profile('场景设计','核对触发、行动与状态变化','前状态、前置关系和触发条件均成立','动态链与后场承接','行动、代价、前后状态及知情差异',('静态关系','当前状态',)),
    'static_relation': Profile('关系设计','把已核定资料关系落实到项目双方','双方来源身份和原条件成立','项目关系合同','两端实体、原条件、机制及行动限制'),
    'dynamic_relation': Profile('场景设计','将完整动态边绑定到状态变化','原触发、适用类型及前置关系均成立','可验状态变化合同','触发、选择、代价、失败分支及同稿状态证据'),
    'anchor': Profile('场景设计','选择能表现节拍变化的观察对象','有明确节拍、观察者、时机和可感对象','锚点与段落定位','正文中可观察的动作、感受或对象变化',('场景节拍','视角权限',)),
    'expression': Profile('写作','按视角和语体表达已确认设计','本场确需该表达手法且排除条件不成立','可观察的正文表现','段落定位、语言或行动效果及审稿结果',('场景设计','视角权限',)),
    'scene': Profile('场景设计','把章任务落实成场景目标和动作','正在编排具体场景且有上游约束','场景任务、阻力、选择与结果','场景卡和节拍，能解释如何承接下一场'),
    'editor': Profile('独立审稿','检查一致性、语言和真实落实','待审稿件版本已冻结且检查项适用','规则审查结论','同一稿件段落、哈希、理由及通过状态',('已冻结草稿',)),
    'prose_review': Profile('独立审稿','根据原文合同核查本稿的具体表现','稿件已冻结且原检查条件适用','逐条审稿结论','原检查点、同一稿件段落和判断理由',('已冻结草稿',)),
    'scope_review': Profile('范围审稿','按原判据核对整章、跨章或全书','作者明确范围且各章实际稿件齐全','冻结范围的独立审稿','范围内全部稿件版本、各章证据与逐来源字段结论',('完整范围稿件',)),
    'character_editor': Profile('独立审稿','对照人物卡检查行动边界和声音','本场出现已确认的人物','人物一致性审查','已采用的人物卡、稿件动作或台词和判断理由',('已确认人物卡','已冻结草稿')),
    'preflight': Profile('写作前检查','核对场景设计、已知状态和写作输入','准备冻结本场的写作工作包','写前检查与缺口','设计版本、事实和视角范围、规则所需输入',('场景设计',)),
    'knowledge': Profile('场景设计','划定人物认知、叙述视角和读者披露边界','场景涉及未知信息、误判或视角转换','知情与披露约束','谁在何时以何证据得知何事以及相关段落',('当前状态','视角权限',)),
    'continuity': Profile('接受与续写','维护接受后的事实和版本','稿件通过相应检查并获接受','状态更新、摘要及承接','接受稿、状态变更、人物所知和后场依赖',('已接受稿',)),
    'material_selection': Profile('资料装配','按任务功能、板块、必需子项三层选择','当前卷章或场景任务已明确','资料调用清单','任务功能、板块理由、具体必需子项及排除记录'),
    'material_conversion': Profile('场景设计','把所用规则转成参数、正文表现及检验点','已选条目直接支撑当前章节或场景','规则转化清单','每条依据的参数、表现及检验点相互对应',('资料调用清单',)),
    'legacy': Profile('流程对账','核对旧流程、调度步骤和适用边界','当前阶段需要迁移旧合同','旧新流程对应和差异','两版步骤、依赖、输入及验收结果'),
    **{name: Profile('阶段执行', purpose, '本项目明确采用对应流程', '结构化阶段产物和独立稿件核验',
                    '实际设计、同版本稿件、来源条件及执行记录') for name, purpose in {
        'timeline_process': '建立时间锚点并同步和核验章场时间线',
        'promise_process': '维护伏笔埋设、休眠、唤醒及回收',
        'pov_process': '规划视角切换并核验重置和周期比例',
        'preflight_process': '在开篇、收尾、人物及世界创建前核对具体产物',
        'usage_process': '冻结资料调用清单并按真实效果复盘'}.items()},
}

_EXECUTION_HASH = 'f2e7725e845dcc349cb54df79992a411bbd034197fb811b287e8066993a04ef8'
_STAGES = (
    (9,'character'), (40,'world'), (45,'plot'), (47,'scene'), (48,'plot'),
    (60,'expression'), (86,'plot'), (87,'scene'), (88,'expression'), (89,'editor'),
    (90,'legacy'), (107,'editor'), (108,'preflight'), (109,'expression'),
    (110,'anchor'), (111,'plot'), (112,'opening'), (113,'plot'),
    (114,'type_expression'), (115,'scene'), (117,'knowledge'), (118,'continuity'),
    (119,'scene'), (120,'expression'), (121,'character'), (122,'plot'), (123,'opening'),
    (124,'type_identity'), (125,'world'), (126,'material_selection'),
    (127,'material_conversion'), (128,'material_selection'), (129,'world'),
    (130,'plot'), (131,'example'), (132,'brief'), (134,'continuity'),
    (135,'editor'), (136,'scene'), (137,'legacy'), (138,'plot'), (139,'example'),
    (140,'character'), (141,'plot'), (142,'knowledge'), (143,'scene'),
    (144,'character'), (145,'plot'), (146,'character'), (148,'anchor'),
    (151,'character'), (152,'scene'), (153,'character'), (155,'plot'),
    (156,'anchor'), (157,'expression'), (158,'knowledge'), (159,'scene'),
    (160,'expression'), (161,'unresolved'), (162,'material_conversion'),
)
_BLOCK = re.compile(r'^(?:板块\s*)?(\d+)(?=[. _：:]|$)')


def _library(row: dict) -> str:
    key = row['fragment_key'] or ''
    match = _BLOCK.match(key)
    number = int(match[1]) if match else 0
    if not 1 <= number <= 162:
        return 'unresolved'
    if row['kind'] in ('check','correction') and number not in {108,126,127,128}:
        return 'editor'
    if row['label'] == '写作指令' and number not in range(87,109) and number not in range(126,129):
        return 'expression'
    return next(profile for last, profile in _STAGES if number <= last)


def _execution(row: dict) -> str:
    if row['file_sha256'] != _EXECUTION_HASH:
        return 'legacy'
    line = row['line_start']
    for limit, profile in ((60,'brief'),(88,'type_expression'),(205,'world'),(283,'opening'),
                           (640,'character'),(1443,'legacy'),(1593,'plot'),(1620,'editor'),
                           (1712,'legacy'),(1788,'material_selection'),(1820,'plot'),
                           (1827,'expression'),(1834,'continuity'),(1841,'editor'),
                           (1876,'continuity'),(1918,'editor')):
        if line < limit:
            return profile
    return 'legacy'


def disposition(row: dict) -> tuple[str, str, str]:
    """Return profile, interpretation, and eligibility without project authorization."""
    kind, family, layer, origin = (row[k] for k in ('kind','family','layer','origin'))
    fragment_key = row['fragment_key'] or ''
    if kind in {'quarantined','residual','network_residual','unclassified','invalid_json','duplicate_member'} or origin == 'residual':
        return 'source_issue', 'needs_review', 'suspended'
    if ('夹具' in fragment_key or 'FIXTURE_' in fragment_key or '测试样例' in fragment_key):
        return 'test_fixture', 'classified', 'reference_only'
    if origin in {'upgrade','supplement'} or kind in {'anchor_upgrade','network_upgrade','library_upgrade'}:
        return 'upgrade_review', 'needs_review', 'reference_only'
    if layer == 'historical':
        return 'history', 'classified', 'reference_only'
    if layer == 'derived':
        return 'derived', 'classified', 'reference_only'
    if kind == 'empty_collection':
        return 'empty', 'needs_review', 'reference_only'
    if kind in {'example','counterexample'}:
        return 'example', 'classified', 'reference_only'
    if family == 'library' and fragment_key.startswith('106.1_') and kind in {
        'instruction','check','correction','grade','variation'
    }:
        return 'source_issue', 'needs_review', 'suspended'
    if kind in {'metadata','json_document','json_group','json_value','tag','identity','anchor_section'}:
        return 'metadata', 'classified', 'reference_only'
    if family == 'routing' or family == 'provenance' or '字段说明' in fragment_key or '枚举' in fragment_key:
        return 'metadata', 'classified', 'reference_only'
    selection_method = family == 'library' and re.match(r'^126\.(?:[3-9]|1[0126])(?:_|\s)', fragment_key)
    if ('模板' in fragment_key and not selection_method) or '候选作品' in fragment_key:
        return 'example', 'classified', 'reference_only'
    if kind == 'source_block':
        return 'metadata', 'classified', 'reference_only'
    if family == 'execution':
        if (layer == 'legacy_contract' and row['id'] == CHARACTER_EDITOR
                and source_review(row, 'character_editor') is not None):
            return 'character_editor', 'needs_review', 'candidate'
        return _execution(row), 'needs_review', 'reference_only'
    if family == 'library':
        profile = _library(row)
        if kind in {'embedded_entry', 'embedded_block'} or (row['locator'] or '').startswith(('embedded/', 'section/')):
            return profile, 'needs_review', 'candidate'
        return profile, 'needs_review', 'reference_only' if profile in {'example','unresolved'} else 'candidate'
    if family == 'types':
        if '原创性检查' in fragment_key or '案例重复风险规则' in fragment_key:
            profile = 'editor'
        elif '案例' in fragment_key:
            return 'example', 'classified', 'reference_only'
        elif '动态' in fragment_key or '传播' in fragment_key:
            profile = 'dynamic_binding'
        elif '表达' in fragment_key or '适配' in fragment_key or '风格' in fragment_key:
            profile = 'type_expression'
        elif '组合' in fragment_key or '相似' in fragment_key:
            profile = 'type_link'
        else:
            profile = 'type_identity'
        return profile, 'needs_review', 'candidate'
    if family in {'type_links','static','dynamic','anchors'}:
        profile = {'type_links':'type_link','static':'static_binding',
                   'dynamic':'dynamic_binding','anchors':'anchor'}[family]
        return profile, 'needs_review', 'candidate'
    return 'unresolved', 'needs_review', 'reference_only'
