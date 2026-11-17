"""表达设计使用的性别表达边界及独立语气表。"""

MATERIAL = r"""
【《类型系统》性别表达适配.json｜SOURCE[67]｜原文第 470,200 行】
【本步用法】依作者确认的人物资料、关系、场景目的和视角写 guidance。原列允许字段按本步职责处理；候选排序及故事触发等涉及上游的字段沿用已确认产物。保留全部事实边界。adaptations 为空，现有数据只说明可调整的表达范围；需要具体呈现时用项目已有依据，选择可见动作、对白或措辞及对应判据。
【原文规则字段】{"stable_id":"G1_2323","object_kind":"性别表达适配_adaptation","schema_version":"1.0.0","description":"性别表达适配：按类型调整性别表达呈现","type_adjustments_allowed":["候选排序","感官重点","表达密度","语言复杂度","反差强度","故事触发方式","社交冲突重点","资源和身份呈现","读者体验","节奏和信息揭示"],"type_adjustments_forbidden":["年龄真实值","物种","生理状态","人物能力事实","动物生态事实","正式项目状态"],"adaptations":[],"source_refs":["G1_SPEC_001"],"evidence_type":"template","confidence":0.7,"status":"active"}
【逐项用法】
1．在已有的表达候选之间说明当前对象和目标为何适合所选候选。
2．依当前视角及已定感知条件选感官着力点。
3．依场景功能决定哪些可见细节需要展开。
4．依作者要求及实际说话者或叙述者调整用词和句式。
5．核对项目已有对照项，在可见动作或话语中安排反差。
6．引用上游已定的触发与结果，表达步呈现可观察的触发过程。
7．沿已定的人际关系和冲突选能显露的反应或对白。
8．依已有人物所知、资源及身份约束安排可见呈现。
9．核对本步表现与当前已经选定的读者体验目标相符。
10．依已定披露顺序和场景节拍安排措辞与停连。
11．六项 forbidden 逐项守原义。人物年龄、物种、生理、能力、动物生态和正式状态全部按项目实际记录。

【《类型系统》语气.json｜SOURCE[68]｜原文第 470,282 行】
【本步用法】根据作者已确定的语气要求、当前说话者和场景目标取适用条目，在 guidance 写可见表达及核对位置。TONE_COLD、TONE_WARM、TONE_HUMOROUS、TONE_EPIC 与类型本体总表同 ID，各保留各自定义；差异影响本场时说明采用哪个原义。语气可以独立于本书类型和人物性格。
【原文表头】{"schema_version":"TYPE_A-1.0.0","updated_at":"2026-07-31T09:42:37.831980"}
【原文逐条字段】tones
【原文行 470289】{"tone_id":"TONE_TENSE","canonical_name":"紧张","definition":"制造紧张氛围的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】依本场已有压力，选可见动作、措辞或停顿表现紧张，核查叙述是否始终贴合当前视角。
【原文行 470302】{"tone_id":"TONE_COLD","canonical_name":"冷峻","definition":"克制、冷静甚至冷漠的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】按角色与情境，以克制的叙述或对白表现冷峻，检查叙述距离与情绪可见范围。
【原文行 470315】{"tone_id":"TONE_WARM","canonical_name":"温暖","definition":"温馨、治愈的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】用现有关系中的具体关照或措辞表现温暖，核查这一表现符合双方此时的关系。
【原文行 470328】{"tone_id":"TONE_HUMOROUS","canonical_name":"诙谐","definition":"幽默、轻松的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】依据说话者、场合和既有反应找诙谐落点，核查玩笑是否与本场目的相容。
【原文行 470341】{"tone_id":"TONE_SAD","canonical_name":"忧伤","definition":"伤感、忧郁的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】通过当前视角可见的动作、措辞或心理细节呈现忧伤，核查情绪与既有事件的对应。
【原文行 470354】{"tone_id":"TONE_EPIC","canonical_name":"史诗","definition":"宏大、庄严的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】从已有场面挑能显示尺度或仪式感的细节，核查措辞能否支持宏大、庄严的语气。
【原文行 470367】{"tone_id":"TONE_MYSTERIOUS","canonical_name":"神秘","definition":"神秘、悬疑的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】在当前允许披露的范围内处理意象、言语和信息留白，核查神秘感的落点。
【原文行 470380】{"tone_id":"TONE_RELAXED","canonical_name":"轻松","definition":"轻松、闲适的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】按已有动作和对白调节松紧，核查轻松语气下场景目标和冲突仍清楚。
【原文行 470393】{"tone_id":"TONE_OPPRESSIVE","canonical_name":"压抑","definition":"沉重、压抑的语气基调","scope":"语气基调","source_refs":["stylistics_standard"],"evidence_type":"template","confidence":0.9,"status":"active","schema_version":"TYPE_A-1.0.0"}
【本条用法】以人物可感的限制、压力或其后果体现压抑，核查叙述集中于已有情境证据。
"""
