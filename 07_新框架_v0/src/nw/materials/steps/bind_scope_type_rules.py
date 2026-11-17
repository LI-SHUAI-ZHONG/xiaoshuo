"""规划收口步骤的《类型系统》层级、报告或条件原文。"""

TDV_020 = {
    'rule_id': 'TDV_020',
    'document_name': '类型动态验证规则.json',
    'source_text': '是否引用待恢复规则',
    'requirement_key': '912dc738ded2a670594df1edd0ac26f159804f8891482012936c463f481a6be3:TDV_020',
    'source_ref': {
        'id': '20131beebc7c0ebba51d65e38ec78faf5306548e309946f3a4fcbd90753e8ccf',
        'sha256': 'bbb6c245e84936c2fba3d6caebb1fd6026daeafd8f92c2cfa8b56889b3245627',
        'source_id': '6cd30d00d42a5b3410bed51599a705463517ef6316fbfc6c4319c45fc0a3cba5',
        'path': '02_原版资料/原始资料/类型系统.txt',
        'file_sha256': 'aa0ac0359d8fb51d35a95f76cc29a652bab7dbfdbdf283a3fcf7acedefb4e582',
        'line': 32773,
        'json_pointer': '/原始条目/19',
    },
}

DYNAMIC_CANDIDATE_USE = (
    '按 dynamic_filter.limits 核对本阶段已落实到本场的类型动态规则和原始动态规则，各自计数。'
    '同一规则多处使用只计一条，明确所选事件、动作、传播候选及采用证据对应的实际场景。'
    '暂无确定场景的保留待核。实际激活另按同场执行轨迹核对。'
)

MATERIAL = r"""#### 规划收口核对的类型动态冲突
【类型系统原文位置】类型动态冲突规则.json 第26990行
【各条共用原文值】{"detection":"report_only","auto_resolve":false,"severity":"error","schema_version":"TYPE_D-1.0.0"}
【本步用法】在实际项目产物上核对以下报告项，记录具体对象、时点、所涉字段及依据。原件规定 report_only，auto_resolve=false。报告按现有产物和待核说明保存。
【逐条原文值】conflict_id 原文行 | conflict_id | description | 本步核对
27043 | TDC_007 | 类型动态规则覆盖原始动态规则 | 核对原始动态规则和类型动态规则的身份与实际采用记录，报告覆盖冲突及相关来源。
27099 | TDC_014 | 类型规则引用待恢复规则 | 从实际采用记录核对规则资格，报告引用待恢复规则的步骤及影响。
27107 | TDC_015 | 类型规则引用fixture | 按来源与当前项目身份核对实际调用的记录，报告引用 fixture 的位置。

【《类型系统》类型动态规则隔离说明｜规划收口】
【原文位置】来源块第 28,188 行，原说明在第 28,190 行。
【本步用法】择用项目资料后，按当前源位、版本及裁定核对原始动态规则、类型扩展及待恢复项的来源。以下 483 条及 C00484–C00494 的待恢复标记对应旧说明。对同号现用正表引用，核对资料文件和条目哈希、原件位置、源端、目标端和关系类型，再沿现有项目采用记录查实际条件。旧编号的迁移须沿指定版本映射核对原关系，未恢复项和无确切出处的同号引用按隔离规则处理。

# 类型动态规则隔离说明

## 规则数量统计

- 原始动态规则数量：483
- 类型动态规则数量：30
- 原始规则 ID 范围：C00001 ~ C00483
- 类型规则 ID 前缀：TDR_*

## C00484至C00494的隔离状态

C00484至C00494 仍然是待恢复项，未被类型系统D引用或替代。

## 类型规则与原始规则的关系

1. 类型规则不替代缺失原始规则。
2. 类型规则不改变原始规则。
3. 类型规则只能作为独立扩展层。
4. 原始动态规则只能作为基础规则引用，不得直接覆盖。

## 正式调用时的区分方式

在正式调用时，通过 source_type 字段区分规则来源：

- source_type: "original_dynamic" — 原始动态网络规则（C00001至C00483）
- source_type: "type_dynamic" — 类型扩展动态规则（TDR_*）
- source_type: "pending_restore" — 待恢复规则（C00484至C00494）— 禁止使用

## 防止类型规则冒充原始规则的措施

1. ID 前缀严格区分：C* vs TDR_*
2. 类型规则 source_refs 必须标注原始来源
3. 类型规则 evidence_type 不允许使用 source_fact（除非有标记来源的事实）
4. 类型规则不得在原始动态网络文件中写入
5. 动态调用协议必须同时返回 source_type
6. 验证规则检测 ID 冲突和非法引用

生成时间：2026-07-31T10:55:56.465880

【《类型系统》类型动态筛选规则 TDF_001｜规划收口】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【原文属性】{"filter_id":"TDF_001","filter_name":"类型动态规则筛选","schema_version":"TYPE_D-1.0.0"}
【本步用法】按当前步骤的实际前置和已有产物落实适用的筛选动作，并保留原步骤编号及其现行裁定。

32495｜reference｜{"step":11,"action":"从类型动态规则索引筛选候选"}
【本步用法】依当前章场目标核对本次确有用的动态候选。保留准确来源及理由，沿用现有步骤的资料选择记录。

32499｜reference｜{"step":12,"action":"排除不满足前置条件的规则"}
【本步用法】回看候选所需的前置产物与实际项目证据，在现有选用或排除记录中说明缺失的条件。

32503｜reference｜{"step":13,"action":"排除pending、fixture和待恢复规则"}
【本步用法】依当前选定原件和确切源位核对 pending、fixture 及待恢复资格，记录被排除的规则及现有理据。

32511｜reference｜{"step":15,"action":"排除与当前连续性冲突的规则"}
【本步用法】对照现有时间线、角色所知和已经成立的事实，说明当前候选与哪些连续性约束冲突。

32515｜reference｜{"step":16,"action":"排序"}
【本步用法】对本场已满足条件的候选按已有优先依据排序，记录采用的具体依据及原字段。

32519｜reference｜{"step":17,"action":"返回少量候选规则"}
【本步用法】按原件列明的各类上限核对本场实际留下的候选，保留其来源、适用条件及可审查的理由。

【《类型系统》类型动态筛选规则每场上限 TDF_001｜规划收口】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】用已有场景或候选实际对应的实体、字段、时点和范围核对原上限。证据不足或计数所需产物未形成时，在本步已有说明中标明待核。

32536｜{"max_type_dynamic_rules":5}
【本步用法】按当前来源身份统计同场选用的类型动态规则，保留该类别的原上限。

32537｜{"max_original_dynamic_rules":5}
【本步用法】按选定动态网络中的确切源位统计同场的原始动态规则，核对该类别的原上限。

32538｜{"max_candidate_effects":10}
【本步用法】统计本场已有各域候选效果的实际条目数，并记录与本场效果数上限的比较。

【《类型系统》类型动态验证规则｜规划收口】
【原文位置】来源块第 32,597 行。条目前缀是原件中的字段行。
【本步用法】按实际项目对象、已用资料和本步产物核对下列验证项，并将问题定位到已有产物和证据。原件规定 report_only=true、auto_fix_allowed=false。

32602｜reference｜{"validation_id":"TDV_001","check_description":"规则ID是否存在","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按本次已采用规则 ID 核对它能否回查到选定资料版本中的确切条目。记录缺失或歧义的 ID。

32611｜reference｜{"validation_id":"TDV_002","check_description":"规则来源是否明确","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】对实际采用条目核对原件版本、物理源位及裁定，指出无法证实来源的引用。

32629｜reference｜{"validation_id":"TDV_004","check_description":"触发条件字段是否合法","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】对照实际采用规则的触发字段和本次可用的输入，指出不在现有依据中的具体字段。

32773｜reference｜{"validation_id":"TDV_020","check_description":"是否引用待恢复规则","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】用当前源位及裁定核对采用记录中的待恢复资格。对同号引用指出文件版本、条目位置、关系两端和类型。项目当前的授权、触发条件和实际落点按现有步骤分别核对。

32782｜reference｜{"validation_id":"TDV_021","check_description":"是否引用fixture规则","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】核对被引用规则或材料的实际来源和角色，指出进入本次采用记录的 fixture 项。

32836｜reference｜{"validation_id":"TDV_027","check_description":"是否与原始规则冲突","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】对照实际所采扩展和现有原始规则的出处、条件及结果，报告冲突所在的对象与字段。

32845｜reference｜{"validation_id":"TDV_028","check_description":"是否与类型静态连接混淆","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按已有来源身份与实际作用核对动态候选、类型静态连接，指出引用错位及所影响的绑定。

【《类型系统》类型多样性策略的比较范围｜规划收口】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【原文属性】{"strategy_id":"DIVERSITY_STRATEGY_V1","version":"1.0","created_at":"2026-07-31 11:55:45"}
【本步用法】按本次真实提供的项目、人物、场景、事件和稿件范围核对差异，现有产物提供实际比较依据。

33029｜"per_chapter"
【本步用法】仅在本次确有完整章范围时，比对已列章内的事件、行动和表达安排。

33030｜"per_volume"
【本步用法】本次材料覆盖同一卷时，依据该卷已知范围和可回查的各章设计比较差异。

33031｜"per_project"
【本步用法】有当前项目的完整设计或实际稿件时，用本项目已确认的范围和产物核对比较结论。

33032｜"cross_project_same_type"
【本步用法】作者已提供可比项目且同类型明确成立时，用各项目的真实设计或稿件核对差异。

33033｜"cross_scene_same_character"
【本步用法】对照可见的不同场景和同一实际人物的身份、处境与行动，定位表现差异。

33034｜"cross_expression_same_concept"
【本步用法】有相同概念及其多处实际表现时，按各场视角和写法核对具体表达差异。

33035｜"cross_event_different_consequence"
【本步用法】有真实事件及其不同已知后果时，按各自触发条件和行动选择回查变化来源。

【《类型系统》类型枚举的证据类型｜规划收口】
【原文位置】来源块第 36,337 行。每项前为对应条目的原件字段行。
【本步用法】核对实际采用的来源依据，按原件记录相应证据角色、出处和范围。

36381｜"source_fact"
【本步用法】将已确认采用的资料事实对应到它的确切原文、源位和当前作用范围。

36382｜"normalized"
【本步用法】核对标准化后的词与原名称的语义对应，保存双方的版本和来源。

36383｜"inferred"
【本步用法】记下推断采用的具体前提与项目证据，保留可复核的适用条件。

36384｜"template"
【本步用法】将模板作为候选的来源依据记录，实际使用落实到本场的目标、参数和表现。

36385｜"pending"
【本步用法】对未确认的来源说明本次尚缺的证据或适用条件，并按当前资格记录。

【《类型系统》类型枚举的映射类型｜规划收口】
【原文位置】来源块第 36,337 行。每项前为对应条目的原件字段行。
【本步用法】以实际名称、规则、原件和项目产物为据记录所用映射的身份、条件与边界。

36394｜"ambiguous"
【本步用法】当同一名称存在多个可疑指向时，记录实际候选的源位歧义。

36395｜"pending"
【本步用法】按实际采用记录核对仍待确认的映射及具体缺项。

36396｜"rejected"
【本步用法】保存本次排除的映射、源位及项目证据所支持的原因。

【《类型系统》类型枚举的原始状态｜规划收口】
【原文位置】来源块第 36,337 行。每项前为对应条目的原件字段行。
【本步用法】对照本次采用条目的原始状态及实际阶段资格，保留源位与可核证据。

36399｜"active"
【本步用法】核对来源条目在原模式记录的活动状态，以及其在当前项目和版本下的实际采用资格。

36400｜"pending"
【本步用法】把尚未确认的条目状态与当前证据缺口一起记录。

36401｜"deprecated"
【本步用法】回查旧条目的版本和已明确的适用结束条件，追溯历史采用时保留源位。

【《类型系统》类型适配冲突规则｜规划收口】
【原文位置】来源块第 38,207 行。条目前缀指原件字段行。
【原文属性】{"schema_version":"TYPE_B-1.0.0","updated_at":"2026-07-31T09:57:28","description":"类型适配冲突检测规则","total_rules":13}
【本步用法】按实际采用的项目条件和本步产物核对下列冲突。原记录为 report_only=true、auto_fix_allowed=false，按原警告及失败条件保留说明和可复核证据。

38406｜reference｜{"conflict_rule_id":"CONFLICT_B_011","rule_name":"类型适配试图覆盖动态规则","category":"type_dynamic_rule_override","description":"当类型适配试图替代或覆盖动态规则时检测","input_fields":["type_id","dynamic_rule_id"],"warning_condition":"类型适配中包含动态规则引用","fail_condition":"适配参数被当作动态规则执行","severity":"fail","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】按当前选定原件、规则 ID 和实际采用记录核对引用情况，定位将适配参数作为动态规则执行的证据。

38443｜reference｜{"conflict_rule_id":"CONFLICT_B_013","rule_name":"类型适配试图生成未来源支持的实体","category":"type_unsupported_entity","description":"当类型适配创建了没有来源支持的实体引用时检测","input_fields":["type_id","entity_reference","source_refs"],"warning_condition":"实体引用缺少source_refs","fail_condition":"实体引用作为正式数据","severity":"warning","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】把实际采用的实体引用与确认的人物、世界及原件对应，指出缺少出处的引用和它进入正式数据的具体位置。

【《类型系统》类型验证规则｜规划收口】
【原文位置】来源块第 40,879 行。条目前缀为 ID 字段的物理原件行。
【原文属性】{"schema_version":"TYPE_A-1.0.0","updated_at":"2026-07-31T09:42:37.831980"}
【本步用法】按本步实际对象及证据核对适用的原验收项。涉及旧阶段 A、备份、文件清单或原测试的条目，按相应阶段和资料维护范围核对已有记录。

40886｜reference｜{"test_id":"TA01","test":"阶段12验收允许进入类型系统","check":"phase0_prerequisites_passed"}
【本步用法】核对旧阶段 12 的实际验收记录和进入阶段 A 的依据。引用时写明对应阶段、日期和原报告。

40891｜reference｜{"test_id":"TA02","test":"类型系统备份成功","check":"backup_completed"}
【本步用法】溯及旧阶段的资料备份时，用实际备份位置和完成记录核对原要求。

40941｜reference｜{"test_id":"TA12","test":"类型来源映射包含evidence_type","check":"mapping_has_evidence"}
【本步用法】对本次确有采用的来源映射核对其 evidence_type、原出处及当步作用。

40951｜reference｜{"test_id":"TA14","test":"类型索引只保存ID和必要摘要","check":"index_no_full_objects"}
【本步用法】回查相应资料索引产物时，核对实际记录的 ID 和摘要范围，完整原对象依据原件定位。

40956｜reference｜{"test_id":"TA15","test":"类型索引不复制完整对象","check":"index_no_duplication"}
【本步用法】检查本次所用索引的实际内容，定位重复保存完整来源对象的记录及影响。

40996｜reference｜{"test_id":"TA23","test":"本阶段未生成类型静态连接","check":"no_static_connections"}
【本步用法】回查旧阶段 A 实际生成的资料清单及差异记录，确认原验收所指静态连接的范围。

41001｜reference｜{"test_id":"TA24","test":"本阶段未生成类型动态规则","check":"no_dynamic_rules"}
【本步用法】根据旧阶段 A 的实际产物及新增项核对原验收所指的动态规则范围。

41006｜reference｜{"test_id":"TA25","test":"本阶段未生成虚假的100种类型搭配","check":"no_100_combinations"}
【本步用法】核对旧阶段的实际组合清单、来源和计数依据，定位有数量声明却无相应记录的项目。

41011｜reference｜{"test_id":"TA26","test":"待恢复动态规则未被类型系统引用","check":"pending_rules_isolated"}
【本步用法】按现行选定原件与确切源位核对所用动态规则的待恢复资格，记录当前裁定与历史编号范围的实际差异。

41016｜reference｜{"test_id":"TA27","test":"测试夹具未进入类型正式数据","check":"fixture_isolated"}
【本步用法】用当前已采用的类型数据及来源角色核对夹具身份和实际影响范围。

41021｜reference｜{"test_id":"TA28","test":"原始文件未被修改","check":"original_untouched"}
【本步用法】在资料维护结项核对原规则时，以本次使用的原件哈希和已有变更记录为据。

41026｜reference｜{"test_id":"TA29","test":"新增JSON全部合法","check":"all_json_valid"}
【本步用法】在资料维护的输出范围内按实际新增 JSON 清单和已有校验结果核对。

41031｜reference｜{"test_id":"TA30","test":"阶段12原有测试全部通过","check":"stage12_tests_pass"}
【本步用法】回查旧阶段 12 验收时，使结论能定位到对应版本和已有测试运行记录。

41036｜reference｜{"test_id":"TA31","test":"版本信息正确记录阶段状态","check":"version_info_correct"}
【本步用法】用实际版本记录和对应阶段验收产物核对原文所指的状态。

41041｜reference｜{"test_id":"TA32","test":"文件目录包含新增文件","check":"file_catalog_updated"}
【本步用法】按资料维护范围的实际新增文件及其目录条目核对覆盖情况。

41046｜reference｜{"test_id":"TA33","test":"类型冲突可报告而非静默修复","check":"conflict_reporting"}
【本步用法】依实际采用的规则、冲突条件及对应产物定位报告，保留需要确认的原字段。

41051｜reference｜{"test_id":"TA34","test":"类型数量来自实际数据而非预设目标","check":"counts_from_data"}
【本步用法】用本次可回查的类型原件和实际有效条目核对数量及分母。

41056｜reference｜{"test_id":"TA35","test":"类型系统A完成后已停止后续阶段","check":"stopped_after_phase"}
【本步用法】查阅旧阶段 A 的结项及后续活动记录时，按原阶段边界核对当时停止位置。

【《类型系统》类型字段说明｜规划收口】
【原文位置】来源块第 42,359 行。条目前缀为对应字段的原件行。
【本步用法】使用本表说明核对采用 TYPE_A-1.0.0 的字段。按该条所属的原模式和现有项目产物确认使用方式。

42457｜{"source_refs":{"type":"array","description":"来源引用","required":true}}
【本步用法】回查本次采用对象关联的原文、物理源位、场景或产物所需证据。

42462｜{"evidence_type":{"type":"string","description":"证据类型","enum":["source_fact","normalized","inferred","template","pending"],"required":true}}
【本步用法】按采用对象自己的原模式和字段记录证据角色及其实际可支持范围。

42474｜{"confidence":{"type":"number","description":"置信度 0-1","required":true}}
【本步用法】用当前条目所属模式核对原置信度及其依据，记录待核值或证据。

42479｜{"status":{"type":"string","description":"状态","enum":["active","pending","deprecated"],"required":true}}
【本步用法】依 TYPE_A 原状态和当前采用资格分别回查实际源位和项目证据。

42489｜{"schema_version":{"type":"string","description":"模式版本","required":true}}
【本步用法】保留本次采用对象的确切原模式和版本，按对应字段范围复核。

【《类型系统》类型总表｜规划收口】
【原文位置】来源块第 42,543 行。条目前缀为对应字段的原件行。
【原文属性】{"schema_version":"TYPE_A-1.0.0","updated_at":"2026-07-31T09:42:37.831980"}
【本步用法】核对 TYPE_A-1.0.0 原总表以及当前采用条目的名单、层级和计数范围。原件 all_type_ids 起于第 42,563 行，其 103 个 ID 与各层级的成员及顺序一致。

42549｜{"main_genre_count":20}
【本步用法】按本表主类型层及实际所用原定义核对同口径数量。

42550｜{"subgenre_count":21}
【本步用法】按本表子类型层的精确 ID 和对应父项核对可回查子项数。

42551｜{"hybrid_genre_count":5}
【本步用法】按本表所列混合成员与实际组件来源核对数量。

42552｜{"mechanism_count":16}
【本步用法】按这一模式原机制名单及其确切 ID 核对范围和数量。

42553｜{"structure_count":15}
【本步用法】在本表实际结构成员范围内核对计数。

42554｜{"style_count":11}
【本步用法】回查本表风格列表及源位，按该列表核对数量。

42555｜{"tone_count":9}
【本步用法】回查同层的语气列表及来源，核对该原始口径。

42556｜{"audience_tag_count":6}
【本步用法】沿本表体验标签层和实际原件核对成员数。

42557｜{"source_fact_count":0}
【本步用法】从本次实际范围中的可查原始事实记录核对统计涵义。

42558｜{"normalized_count":46}
【本步用法】核对来源、标准化类别及其实际统计对象和范围。

42559｜{"inferred_count":0}
【本步用法】按本表原统计口径核对推断项及其具体依据。

42560｜{"template_count":103}
【本步用法】对照实际模板来源和统计范围核对本表所给数量。

42561｜{"pending_count":0}
【本步用法】按原计数范围中的待核资格与原件记录核对数量。

42818｜{"duplicate_ids":{}}
【本步用法】保留原表的空冲突记录。依本表精确 ID 列表和当前实际原件核对重复范围。

【《类型系统》类型组合约束｜规划收口】
【原文位置】来源块第 42,867 行。条目前缀为对应字段的原件行。
【本步用法】按当前选型、适配产物和正式来源证据核对原组合约束。原严重程度及现行参考裁定随条保留。

42899｜reference｜{"constraint_id":"CC06","constraint":"项目标签不能冒充source_fact","severity":"error"}
【本步用法】核对实际采用记录中项目标签的来源身份、证据角色及其用途。

42904｜reference｜{"constraint_id":"CC07","constraint":"类型冲突必须报告","severity":"warning"}
【本步用法】按当前采用的类型组合与实际产物，报告具体冲突、作用范围和来源证据。

42909｜reference｜{"constraint_id":"CC08","constraint":"空类型ID不得进入正式索引","severity":"error"}
【本步用法】回查本次所用索引的实际源位与类型对象，发现空 ID 时在现有说明中定位该条。
"""
