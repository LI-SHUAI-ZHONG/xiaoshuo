"""作品知识库 H0D 类型和风格案例在现有创作步骤中的用法。"""

TYPE_CASE_FIELDS = r"""
【作品知识库 H0D 类型案例】
实际采用 H0D 案例时按这个版本的字段和原分类核对。原总表和各分类表的 items 均为空。有验过的抽象案例时，依据本步实有的项目前置确定能用的部分。
【原文共用字段】{"items":[],"count":0,"evidence_type":"template","status":"active","schema_version":"H0D-1.0.0"}

【《类型系统》作品知识库\类型案例\类型案例模板.json｜SOURCE[362]｜原文第 641,718 行】
【原文模板字段】{"case_id":"","case_kind":"","source_work_ids":[],"source_analysis_ids":[],"type_ids":[],"subtype_ids":[],"mechanism_ids":[],"structure_ids":[],"abstract_pattern":"","pattern_components":[],"preconditions":[],"candidate_uses":[],"alternative_uses":[],"failure_paths":[],"delayed_effects":[],"continuity_constraints":[],"similarity_features":[],"originality_risk":"","reuse_penalty_features":[],"not_guaranteed":[],"source_refs":[],"evidence_type":"template","confidence":0,"status":"active","schema_version":"H0D-1.0.0"}
【本条用法】读取 H0D 类型案例时，依实际来源核对 abstract_pattern、pattern_components、preconditions 和候选及备选用法。failure_paths、delayed_effects 与 continuity_constraints 随本次适用的内容落到已有产物及下游依据。保留 not_guaranteed、相似特征与原创性风险。模板示例用于识别字段，实际值来自本项目确认采用的案例。
"""

EXPRESSION_MATERIAL = r"""
【作品知识库 H0D 风格案例】
实际采用 H0D 案例时按这个版本的字段和原分类核对。原总表和各分类表的 items 均为空。表达设计以作者已定要求和本场视角、行动、已有信息为据。
【原文共用字段】{"items":[],"count":0,"evidence_type":"template","status":"active","schema_version":"H0D-1.0.0"}

【《类型系统》作品知识库\风格案例\动作呈现案例.json｜SOURCE[116]｜原文第 610,867 行】
【原文块字段】{"dimension":"动作呈现"}
【本条用法】本场动作已由上游确定时，核对案例里可迁移的动作细节、呈现顺序和节拍。用实际动作及其可见结果写入 guidance。

【《类型系统》作品知识库\风格案例\对话案例.json｜SOURCE[117]｜原文第 610,924 行】
【原文块字段】{"dimension":"对话"}
【本条用法】依已有人物的说话目的、关系和所知选择可用的对话方式。把语言特征及它所承载的信息对应到本场对白。

【《类型系统》作品知识库\风格案例\风格案例模板.json｜SOURCE[118]｜原文第 610,981 行】
【原文模板字段】{"style_case_id":"","source_work_ids":[],"source_analysis_ids":[],"style_ids":[],"tone_ids":[],"dimension":"","parameter_profile":{},"presentation_tendency":"","suitable_scene_types":[],"suitable_concept_groups":[],"suitable_character_states":[],"risks":[],"alternatives":[],"not_guaranteed":[],"similarity_features":[],"originality_risk":"","source_refs":[],"evidence_type":"template","confidence":0,"status":"active","schema_version":"H0D-1.0.0"}
【本条用法】读到 H0D 风格案例时，按 source_work_ids、source_analysis_ids 和 source_refs 核对来源，依 presentation_tendency、parameter_profile、场景、概念和人物条件比较可用做法。risks、alternatives、not_guaranteed、similarity_features 和 originality_risk 随实际案例核对。模板示例用来识别字段，实际值来自本项目确认采用的案例。

【《类型系统》作品知识库\风格案例\风格案例总表.json｜SOURCE[120]｜原文第 611,148 行】
【原文块字段】{}
【本条用法】按本场已明确的表达任务和视角，从实际有内容且可追溯的风格记录中判断哪个维度适用。检查原效果与当前场景能达到的效果。

【《类型系统》作品知识库\风格案例\感官呈现案例.json｜SOURCE[121]｜原文第 611,204 行】
【原文块字段】{"dimension":"感官呈现"}
【本条用法】根据本场观察者及其实际能接触的对象选择感官表现，核对可感的细节和出现位置。

【《类型系统》作品知识库\风格案例\节奏案例.json｜SOURCE[122]｜原文第 611,261 行】
【原文块字段】{"dimension":"节奏"}
【本条用法】根据上游事件、对白、动作和场景节拍选择可用的节奏方式。用可定位的停顿、动作顺序或叙述速度说明效果。

【《类型系统》作品知识库\风格案例\文风案例.json｜SOURCE[123]｜原文第 611,318 行】
【原文块字段】{"dimension":"文风"}
【本条用法】以作者已定文风及本场目的选取用词、句式或叙述距离的可用做法，按本场正文能观察到的表现核对。

【《类型系统》作品知识库\风格案例\心理描写案例.json｜SOURCE[124]｜原文第 611,375 行】
【原文块字段】{"dimension":"心理描写"}
【本条用法】依已有人物动机、心理状态及视角可知范围选择表达方式，确定心理表现出现的位置和可检查的细节。

【《类型系统》作品知识库\风格案例\叙述案例.json｜SOURCE[125]｜原文第 611,432 行】
【原文块字段】{"dimension":"叙述"}
【本条用法】结合已确认的叙述者、视角和叙述顺序选择合适的叙述方式，检查这些已定条件在本场保持一致。
"""

TYPE_ADAPTATION_CASES = r"""
【《类型系统》作品知识库\类型案例\类型案例总表.json｜SOURCE[364]｜原文第 641,897 行】
【原文块字段】{}
【本条用法】当实际案例已可采用时，按已定类型、项目需求及 H0D 原分类查对照，把使用理由、前置和非保证边界写入本步既有产物。
"""

PLOT_DESIGN_CASES = r"""
【《类型系统》作品知识库\类型案例\冲突案例.json｜SOURCE[357]｜原文第 641,433 行】
【原文块字段】{"case_kind":"冲突"}
【本条用法】按已确认的冲突双方、人物目标及限制判断抽象结构能否用来设计阻碍。采用时在 directions 说明项目实际选择、代价和可见后果。

【《类型系统》作品知识库\类型案例\伏笔案例.json｜SOURCE[358]｜原文第 641,490 行】
【原文块字段】{"case_kind":"伏笔"}
【本条用法】按项目已有或可采用的线索及其作用，比较可用的埋设和回收条件。用 promise_plan 记录这部作品的实际埋设、读者能看到的证据及预定回应。

【《类型系统》作品知识库\类型案例\钩子案例.json｜SOURCE[359]｜原文第 641,547 行】
【原文块字段】{"case_kind":"钩子"}
【本条用法】按项目已经确定的开篇目标或当前读者期待，比较钩子能引出什么具体问题及其兑现位置。把实际承诺写入 reader_plan。

【《类型系统》作品知识库\类型案例\剧情案例.json｜SOURCE[361]｜原文第 641,661 行】
【原文块字段】{"case_kind":"剧情"}
【本条用法】以已选择的剧情方向和当前事件的前提为据，核对适用抽象结构怎样帮助安排选择、后果和条件。把本项目的推进写入 event_nodes。

【《类型系统》作品知识库\类型案例\爽点案例.json｜SOURCE[367]｜原文第 642,067 行】
【原文块字段】{"case_kind":"爽点"}
【本条用法】结合本项目已有期待、铺垫及角色实际可做的选择，比对读者对兑现时机和呈现条件的需要。在 reader_plan 明确将由哪个项目事件体现。

【《类型系统》作品知识库\类型案例\信息案例.json｜SOURCE[368]｜原文第 642,124 行】
【原文块字段】{"case_kind":"信息"}
【本条用法】沿项目已知线索及各角色的来源，比较知情差与披露结构。在 reader_plan 说明谁凭什么知道、读者何时看见。

【《类型系统》作品知识库\类型案例\主题案例.json｜SOURCE[369]｜原文第 642,181 行】
【原文块字段】{"case_kind":"主题"}
【本条用法】用作者已选主题与人物当前困境核对抽象案例，说明本项目哪项选择或后果能实际承载主题，并对应剧情设计。
"""

STATIC_RELATIONS_CASES = r"""
【《类型系统》作品知识库\类型案例\关系案例.json｜SOURCE[360]｜原文第 641,604 行】
【原文块字段】{"case_kind":"关系"}
【本条用法】依上游已有角色、立场与关系，核对案例两端及形成关系的条件。按 relations 记录可验证的稳定结构及范围。
"""

CHARACTER_DESIGN_CASES = r"""
【《类型系统》作品知识库\类型案例\人物案例.json｜SOURCE[365]｜原文第 641,953 行】
【原文块字段】{"case_kind":"人物"}
【本条用法】用项目已有的角色定位、人物动机和可确认的能力范围核对适用的人物功能或行为倾向，在人物产物写明本项目真实选择及限制。
"""

WORLD_DESIGN_CASES = r"""
【《类型系统》作品知识库\类型案例\世界案例.json｜SOURCE[366]｜原文第 642,010 行】
【原文块字段】{"case_kind":"世界"}
【本条用法】以作者已定的世界方向和实际创作问题为据，核对可用的制度、条件或环境关系，在本项目世界规则与适用范围留下证据。

【《类型系统》作品知识库\类型案例\资源案例.json｜SOURCE[370]｜原文第 642,238 行】
【原文块字段】{"case_kind":"资源"}
【本条用法】以已确认的设定及实际资源用途为据，核对可复用的分配、取得及消耗边界，形成世界规则和限制。
"""

TYPE_ADAPTATION_MATERIAL = '\n'.join((TYPE_CASE_FIELDS, TYPE_ADAPTATION_CASES))
PLOT_DESIGN_MATERIAL = '\n'.join((TYPE_CASE_FIELDS, PLOT_DESIGN_CASES))
STATIC_RELATIONS_MATERIAL = '\n'.join((TYPE_CASE_FIELDS, STATIC_RELATIONS_CASES))
CHARACTER_DESIGN_MATERIAL = '\n'.join((TYPE_CASE_FIELDS, CHARACTER_DESIGN_CASES))
WORLD_DESIGN_MATERIAL = '\n'.join((TYPE_CASE_FIELDS, WORLD_DESIGN_CASES))
