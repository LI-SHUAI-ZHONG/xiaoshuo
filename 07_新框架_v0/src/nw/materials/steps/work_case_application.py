"""现有创作步骤对作品资料库抽象案例及风格案例的取用规则。"""

from nw.materials.steps import work_knowledge_case_application as knowledge_cases

ABSTRACT_CASE_FIELDS = r"""
【作品资料库的抽象案例】
【原文共用字段】{"schema_version":"TYPE_F-1.0.0","created_at":"2026-07-31T12:08:30.700982","fields":{"case_id":{"type":"string","prefix":"CASE_","required":true},"case_kind":{"type":"string","required":true},"work_id":{"type":"string","prefix":"WORK_","required":true},"type_ids":{"type":"array","required":false},"subtype_ids":{"type":"array","required":false},"mechanism_ids":{"type":"array","required":false},"structure_ids":{"type":"array","required":false},"style_ids":{"type":"array","required":false},"abstract_pattern":{"type":"string","required":true},"pattern_components":{"type":"array","required":false},"preconditions":{"type":"array","required":false},"candidate_uses":{"type":"array","required":false},"alternative_uses":{"type":"array","required":false},"not_guaranteed":{"type":"array","required":true},"similarity_features":{"type":"object","required":false},"source_refs":{"type":"array","required":false},"evidence_type":{"type":"string","default":"inferred","required":true},"confidence":{"type":"float","min":0,"max":1,"required":true},"status":{"type":"string","required":true}},"cases":[],"total_cases":0}
【共用字段用法】原表目前没有案例实例。项目已提供可回查、经确认采用的案例时，按本步所需的真实前置、abstract_pattern、candidate_uses、alternative_uses 和 not_guaranteed 核对用途，再写入本步产物。TYPE_F 原字段 work_id 为单项，用于查本条来源。H0D 的 source_work_ids 及其验证条款按实际来源版本分别核对。
"""

TYPE_CASE_CHECKS = r"""
【《类型系统》作品知识库\类型案例\类型案例验证规则.json｜SOURCE[363]｜原文第 641,794 行】
【原文规则字段】{"schema_name":"类型案例验证规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"TCC-01","description":"case_id必须非空且唯一"},{"rule_id":"TCC-02","description":"case_kind必须在枚举范围内"},{"rule_id":"TCC-03","description":"source_work_ids必须存在（可为空列表表示无真实来源）"},{"rule_id":"TCC-04","description":"必须包含not_guaranteed"},{"rule_id":"TCC-05","description":"必须包含similarity_features"},{"rule_id":"TCC-06","description":"必须包含originality_risk"},{"rule_id":"TCC-07","description":"evidence_type必须为template/fixture/inferred/pending"},{"rule_id":"TCC-08","description":"status必须为active/fixture_only/pending_review"},{"rule_id":"TCC-09","description":"不得保存原作正文或长对白"},{"rule_id":"TCC-10","description":"fixture对象不得进入正式总表"},{"rule_id":"TCC-11","description":"不得引用C00484-C00494"},{"rule_id":"TCC-12","description":"不得生成虚构作品案例作为source_fact"}]}
【本条用法】只在本项目实际读取《作品知识库》的 H0D 类型案例时核对以下十二条。核对案例标识、分类、证据及状态。source_work_ids 为空是本版本允许的记录形式，实际项目依据另查可回查的来源。来源不足、仅为夹具或未确认的条目保留其原资格。已选类型只用于比较检索范围，有实际用途才将抽象方法用于当前步骤。
"""

TYPE_ADAPTATION_CASES = r"""
【《类型系统》作品资料库\抽象案例\案例总表.json｜SOURCE[396]｜原文第 647,470 行】
【原文块字段】{"schema_name":"案例总表","case_kind":"case_kinds_overview"}
【本条用法】本项目确实采用作品资料库的案例时，从已选类型和实际任务确定需要的 case_kind，比较来源、可用条件和不保证的结果。以短说明说明案例想解决的项目问题，并把适用性转给相应的下游步骤。

【《类型系统》作品资料库\抽象案例\类型案例.json｜SOURCE[400]｜原文第 648,256 行】
【原文块字段】{"schema_name":"类型案例","case_kind":"genre_case"}
【本条用法】对照作者已选类型及当前适配目标，提取案例中确实可用的机制、结构或类型体验条件。在 adaptations 或 boundaries 说明选择的范围以及 not_guaranteed 边界。
"""

PLOT_DESIGN_CASES = r"""
【《类型系统》作品资料库\抽象案例\冲突案例.json｜SOURCE[397]｜原文第 647,610 行】
【原文块字段】{"schema_name":"冲突案例","case_kind":"conflict_case"}
【本条用法】按已定的人物、目标与已存在的约束，核对案例中可迁移的冲突机制。把适用部分落到 directions 的选择、代价和后果，并可在 event_nodes 写出项目实际的阻碍条件。

【《类型系统》作品资料库\抽象案例\伏笔案例.json｜SOURCE[398]｜原文第 647,750 行】
【原文块字段】{"schema_name":"伏笔案例","case_kind":"foreshadowing_case"}
【本条用法】按已知项目线索和合适的读者预期，比较案例中可迁移的伏笔结构。在 promise_plan 标明本项目的埋设、可见证据与回收安排，供后续步骤定位。

【《类型系统》作品资料库\抽象案例\信息案例.json｜SOURCE[403]｜原文第 648,676 行】
【原文块字段】{"schema_name":"信息案例","case_kind":"information_case"}
【本条用法】沿项目已知的线索、掌握信息的人及读者体验，挑选适用的知情差或揭示安排。把谁能知道、何时能披露和先后原因落实到 reader_plan。
"""

STATIC_RELATION_CASES = r"""
【《类型系统》作品资料库\抽象案例\关系案例.json｜SOURCE[399]｜原文第 648,003 行】
【原文块字段】{"schema_name":"关系案例","case_kind":"relationship_case"}
【本条用法】依据上游实际人物、组织、身份或已有关系，核对可用的稳定关系结构。用本步 relations 写出两端和成立条件。关系变化依据所选事件交后续步骤。
"""

CHARACTER_DESIGN_CASES = r"""
【《类型系统》作品资料库\抽象案例\人物案例.json｜SOURCE[401]｜原文第 648,396 行】
【原文块字段】{"schema_name":"人物案例","case_kind":"character_case"}
【本条用法】依实际人物在项目里的角色、需求和可知信息，参考案例中的人物功能或动机结构。用当前人物的设定、能力和限制归入本步产物。
"""

WORLD_DESIGN_CASES = r"""
【《类型系统》作品资料库\抽象案例\世界案例.json｜SOURCE[402]｜原文第 648,536 行】
【原文块字段】{"schema_name":"世界案例","case_kind":"world_case"}
【本条用法】依据项目已定的时间、空间、制度和题材要求，参考能解释当前世界问题的抽象结构。在世界规则和 limitations 里注明项目自己的条件和影响。

【《类型系统》作品资料库\抽象案例\资源案例.json｜SOURCE[404]｜原文第 648,929 行】
【原文块字段】{"schema_name":"资源案例","case_kind":"resource_case"}
【本条用法】依已定世界规则和项目现有资源，核对对当前故事有用的资源取得或限制机制。在世界产物写明来源、适用范围、消耗或分配条件。
"""

EXPRESSION_MATERIAL = r"""
【《类型系统》作品知识库\风格案例\风格案例验证规则.json｜SOURCE[119]｜原文第 611,053 行】
【原文规则字段】{"schema_name":"风格案例验证规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"SCC-01","description":"style_case_id必须非空且唯一"},{"rule_id":"SCC-02","description":"dimension必须在枚举范围内"},{"rule_id":"SCC-03","description":"source_work_ids必须存在"},{"rule_id":"SCC-04","description":"必须包含not_guaranteed"},{"rule_id":"SCC-05","description":"必须包含similarity_features"},{"rule_id":"SCC-06","description":"必须包含originality_risk"},{"rule_id":"SCC-07","description":"禁止保存原作独特句式、长对白和可直接模仿的段落"},{"rule_id":"SCC-08","description":"fixture对象不得进入正式总表"},{"rule_id":"SCC-09","description":"不得引用C00484-C00494"},{"rule_id":"SCC-10","description":"不得生成虚构作品案例作为source_fact"}]}
【本条用法】只在本项目实际读取《作品知识库》的 H0D 风格案例时核对以下十条。检查标识、来源、可用范围和原创性信息，依已知的项目场景、视角和表达目的判断是否采用。案例仅提供可迁移的表达方式。原故事的角色、对白和独特段落不进入本步表现。原文要求核对的字段缺失时，在既有项目判断中注明缺口。

【作品资料库的风格案例】
【原文共用字段】{"schema_version":"TYPE_F-1.0.0","created_at":"2026-07-31T12:08:30.700982","fields":{"style_case_id":{"type":"string","prefix":"STYLE_CASE_","required":true},"work_id":{"type":"string","prefix":"WORK_","required":true},"style_ids":{"type":"array","required":false},"tone_ids":{"type":"array","required":false},"dimension":{"type":"string","required":true},"parameter_profile":{"type":"object","required":false},"presentation_tendency":{"type":"string","required":true},"suitable_scene_types":{"type":"array","required":false},"suitable_concept_groups":{"type":"array","required":false},"suitable_character_states":{"type":"array","required":false},"risks":{"type":"array","required":false},"alternatives":{"type":"array","required":false},"not_guaranteed":{"type":"array","required":true},"source_refs":{"type":"array","required":false},"evidence_type":{"type":"string","default":"inferred","required":true},"confidence":{"type":"float","min":0,"max":1,"required":true},"status":{"type":"string","required":true}},"cases":[],"total_cases":0}
【共用字段用法】原表目前没有案例实例。本步有实际采用的案例和当前场景时，用 presentation_tendency、条件、风险、替代方法和 not_guaranteed 字段核对用途。按已确认的本场视角、人物和作者风格要求，把适用部分写成可观察的表现与判据。原表字段依 TYPE_F 使用。H0D 的相似度与原创性要求按其来源记录核对。

【《类型系统》作品资料库\风格案例\动作呈现案例.json｜SOURCE[405]｜原文第 649,069 行】
【原文块字段】{"schema_name":"动作呈现案例","dimension":"action_presentation"}
【本条用法】已明确本场人物及行动时，用动作呈现案例比较细节、顺序或节拍如何让动作可见。在 guidance 写出本场实际表现和可检查的位置。

【《类型系统》作品资料库\风格案例\对话案例.json｜SOURCE[406]｜原文第 649,201 行】
【原文块字段】{"schema_name":"对话案例","dimension":"dialogue"}
【本条用法】依本场已定说话者、目的、关系和知情条件，取用可迁移的对白方法。在 guidance 写明语气、潜台词或信息效果的可见表现。

【《类型系统》作品资料库\风格案例\风格案例总表.json｜SOURCE[407]｜原文第 649,333 行】
【原文块字段】{"schema_name":"风格案例总表","dimension":"style_overview"}
【本条用法】依据本场任务、作者写法要求和现有叙述视角选取风格案例维度。把表达目的和适用条件落到 guidance 的实际表现与检查点。

【《类型系统》作品资料库\风格案例\节奏案例.json｜SOURCE[408]｜原文第 649,465 行】
【原文块字段】{"schema_name":"节奏案例","dimension":"pacing"}
【本条用法】在既有事件和场景节拍下，参考可用的停连或节奏处理。用本场可查的动作、对白或段落位置说明阅读速度怎样变化。

【《类型系统》作品资料库\风格案例\视觉呈现案例.json｜SOURCE[409]｜原文第 649,597 行】
【原文块字段】{"schema_name":"视觉呈现案例","dimension":"visual_presentation"}
【本条用法】依据本场已有对象、视角和可感范围选取视觉表达方法。在 guidance 写明对读者有用的可见落点，以及它与本场目标的关系。

【《类型系统》作品资料库\风格案例\心理描写案例.json｜SOURCE[410]｜原文第 649,729 行】
【原文块字段】{"schema_name":"心理描写案例","dimension":"psychological_description"}
【本条用法】依叙述视角可知的心理状态、人物动机和本场事件，选取适用的心理表现方法。用可观察动作、内心描写或措辞保留原有信息边界。

【《类型系统》作品资料库\风格案例\信息揭示案例.json｜SOURCE[411]｜原文第 649,861 行】
【原文块字段】{"schema_name":"信息揭示案例","dimension":"information_revelation"}
【本条用法】沿场景卡的 allowed_disclosure 和既定披露顺序，用适用的案例方法决定本场从哪里呈现已经允许公开的信息。按读者能看见的证据核对。

【《类型系统》作品资料库\风格案例\语言风格案例.json｜SOURCE[412]｜原文第 649,993 行】
【原文块字段】{"schema_name":"语言风格案例","dimension":"language_style"}
【本条用法】根据作者已确定的风格或本场叙述目的，比较适用的用词、句式与叙述距离。在 guidance 写清出现位置和可检查的效果。
""" + "\n" + knowledge_cases.EXPRESSION_MATERIAL

TYPE_ADAPTATION_MATERIAL = '\n'.join((
    TYPE_CASE_CHECKS,
    ABSTRACT_CASE_FIELDS,
    TYPE_ADAPTATION_CASES,
    knowledge_cases.TYPE_ADAPTATION_MATERIAL,
))
PLOT_DESIGN_MATERIAL = '\n'.join((
    ABSTRACT_CASE_FIELDS,
    PLOT_DESIGN_CASES,
    knowledge_cases.PLOT_DESIGN_MATERIAL,
))
STATIC_RELATIONS_MATERIAL = '\n'.join((
    ABSTRACT_CASE_FIELDS,
    STATIC_RELATION_CASES,
    knowledge_cases.STATIC_RELATIONS_MATERIAL,
))
CHARACTER_DESIGN_MATERIAL = '\n'.join((
    ABSTRACT_CASE_FIELDS,
    CHARACTER_DESIGN_CASES,
    knowledge_cases.CHARACTER_DESIGN_MATERIAL,
))
WORLD_DESIGN_MATERIAL = '\n'.join((
    ABSTRACT_CASE_FIELDS,
    WORLD_DESIGN_CASES,
    knowledge_cases.WORLD_DESIGN_MATERIAL,
))
