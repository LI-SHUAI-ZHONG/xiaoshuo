"""类型适配使用的作品参考来源核验与热度比较原文。"""

SOURCE_REVIEW_MATERIAL = r"""
【已有作品参考的来源核验】
本项目在当前步明确考虑有来源的作品参考时，依实际输入、已采用案例和现有核验记录核对。作品参考是可选择的创作依据，独立核对其来源与取用资格。作者已经确定的项目类型、事实和风格以实际项目为据。在原有 adaptations 或 boundaries 记录相关出处、取用限制和待核证据。作者和人工核验决定以项目实际记录为据。

【《类型系统》热门作品来源规则.json｜SOURCE[61]｜原文第 468,864 行】
【本条用法】实际采用热门作品作为类型或创作参考时，逐项查看作品存在、作者、平台、类型、排名和热度的来源及核验状态。原可靠性分值用于说明证据强弱。遇到冲突按下文处理，项目类型和写法依作者要求及当步需要确定。
【原文规则字段】{"schema_name":"热门作品来源规则","schema_version":"TYPE_F-1.0.0","created_at":"2026-07-31T12:08:30.700982","source_types":{"official_platform":{"reliability":0.9,"description":"官方平台直接数据"},"official_publisher":{"reliability":0.9,"description":"出版商官方信息"},"author_official":{"reliability":0.85,"description":"作者官方发布"},"library_catalog":{"reliability":0.8,"description":"图书馆目录"},"bibliographic_database":{"reliability":0.8,"description":"书目数据库"},"reputable_media":{"reliability":0.75,"description":"知名媒体"},"reputable_review":{"reliability":0.7,"description":"知名评论"},"public_catalog":{"reliability":0.6,"description":"公开目录"},"search_result":{"reliability":0.4,"description":"搜索结果，不能单独证明最热门"},"user_submitted":{"reliability":0.2,"description":"用户提交，不能作为高可信来源"},"unknown":{"reliability":0,"description":"未知来源"}},"verification_status":["verified","partially_verified","unverified","conflicting","unavailable","pending_review"],"rules":["search_result 不能单独证明最热门","user_submitted 不能直接作为高可信来源","unknown 来源不得标记 verified","没有来源的作品只能放入待核验清单","作品存在、作者、平台、类型、排名和热度必须分别核验","不同来源冲突时保留所有来源并生成冲突报告","不得静默选择一个来源"]}

【《类型系统》作品来源可信度规则.json｜SOURCE[81]｜原文第 603,375 行】
【本条用法】对照实际可回查的作品来源和原可信度区间，把可核验、部分可核和缺项分开。在本步已有依据中说明独立来源一致或冲突的情况。当原阈值没有覆盖实际精度时记录待核，具体来源事实逐项核对。
【原文规则字段】{"schema_name":"作品来源可信度规则","schema_version":"TYPE_F-1.0.0","reliability_levels":{"high":{"min":0.8,"max":1,"can_verify":true},"medium":{"min":0.5,"max":0.79,"can_verify":"partially"},"low":{"min":0,"max":0.49,"can_verify":false}},"combination_rules":["多个独立高可信来源一致时可以提升置信度","一个高可信来源+一个低可信来源冲突时保留冲突","不得用低可信来源覆盖高可信来源","搜索结果不能作为唯一最热门证据"]}

【《类型系统》作品知识库\来源记录\来源冲突处理说明.md｜SOURCE[339]｜原文第 637,925 行】
【本条用法】按已有作品来源中相互矛盾的字段识别冲突类型，核对现有解决记录与证据。重要冲突记录需人工复核。只在已存在可核审查结果时说明解决依据。
【原文】
# 来源冲突处理说明

> 本说明用于处理来源记录之间的冲突。本阶段仅建立结构，不采集真实作品。

## 一、冲突类型

- title_conflict：标题冲突
- author_conflict：作者冲突
- platform_conflict：平台冲突
- publication_date_conflict：出版日期冲突
- genre_conflict：类型冲突
- status_conflict：状态冲突
- ranking_conflict：排名冲突
- metric_conflict：指标冲突
- time_scope_conflict：时间范围冲突
- region_scope_conflict：地区范围冲突
- duplicate_work_conflict：重复作品冲突
- identity_conflict：身份冲突
- unavailable_source_conflict：来源不可用冲突

## 二、解决状态

- unresolved：未解决
- manually_resolved：人工解决
- resolved_by_primary_source：由主要来源解决
- merged_with_evidence：合并证据
- rejected_duplicate：拒绝重复
- pending_review：待复核

## 三、自动规则

- 不得静默解决冲突。
- 不得使用最低可信来源覆盖最高可信来源。
- 最高可信来源也不能自动解决全部冲突。
- 重要冲突必须 manual_review_required = true。
- 冲突未解决的作品不得标记 fully_verified。
- 来源互相矛盾时保留全部来源。
- 无法核验时使用 unverified、conflicting 或 pending_review。

## 四、处理流程

1. 检测到冲突时，创建来源冲突记录。
2. 记录冲突类型、涉及来源和冲突值。
3. 评估来源可信度比较。
4. 若为重要冲突，标记 manual_review_required = true。
5. 未解决前，相关作品不得标记 fully_verified。
6. 人工复核后更新 resolution_status。

## 五、禁止事项

- 不得静默选择冲突来源。
- 不得使用模型推理填补来源事实。
- 不得删除冲突来源记录。

【《类型系统》作品知识库\来源记录\来源冲突规则.json｜SOURCE[340]｜原文第 637,982 行】
【本条用法】依原七条规则核对当前来源是否能支持使用。读取现有 conflict_kinds 和 resolution_status，并在本步原有边界中写明实际冲突及须补的源证据。
【原文规则字段】{"schema_name":"来源冲突规则","schema_version":"H-0B-1.0.0","description":"来源冲突处理规则。本阶段仅建立结构，不采集真实作品。","conflict_kinds":["title_conflict","author_conflict","platform_conflict","publication_date_conflict","genre_conflict","status_conflict","ranking_conflict","metric_conflict","time_scope_conflict","region_scope_conflict","duplicate_work_conflict","identity_conflict","unavailable_source_conflict"],"resolution_status":["unresolved","manually_resolved","resolved_by_primary_source","merged_with_evidence","rejected_duplicate","pending_review"],"rules":[{"rule_id":"CONFLICT_RULE_01","rule":"不得静默解决冲突","description":"不得静默解决冲突。"},{"rule_id":"CONFLICT_RULE_02","rule":"不得使用最低可信来源覆盖最高可信来源","description":"不得使用最低可信来源覆盖最高可信来源。"},{"rule_id":"CONFLICT_RULE_03","rule":"最高可信来源也不能自动解决全部冲突","description":"最高可信来源也不能自动解决全部冲突。"},{"rule_id":"CONFLICT_RULE_04","rule":"重要冲突必须manual_review_required = true","description":"重要冲突必须manual_review_required = true。"},{"rule_id":"CONFLICT_RULE_05","rule":"冲突未解决的作品不得标记fully_verified","description":"冲突未解决的作品不得标记fully_verified。"},{"rule_id":"CONFLICT_RULE_06","rule":"来源互相矛盾时保留全部来源","description":"来源互相矛盾时保留全部来源。"},{"rule_id":"CONFLICT_RULE_07","rule":"无法核验时使用unverified、conflicting或pending_review","description":"无法核验时使用unverified、conflicting或pending_review。"}]}

【《类型系统》作品知识库\来源记录\来源核验检查清单.md｜SOURCE[344]｜原文第 638,526 行】
【本条用法】按人工清单核对已有来源记录和人工判断是否覆盖当前用途。检查相关类型、作品状态和所用热度口径，各项结论引用实际出处。
【原文】
# 来源核验检查清单

> 本清单用于人工核验来源记录。本阶段仅建立结构，不采集真实作品。

## 一、来源可信度优先级（仅作核验参考，不自动替代事实验证）

1. official_platform（官方平台）
2. official_publisher（官方出版社）
3. author_official（作者官方）
4. library_catalog（图书馆目录）
5. bibliographic_database（书目数据库）
6. reputable_media（权威媒体）
7. reputable_review（权威评论）
8. public_catalog（公共目录）
9. search_result（搜索结果）
10. user_submitted（用户投稿）
11. unknown（未知）

## 二、核验规则

- 搜索结果不能单独证明"热门"。
- 用户投稿不能自动作为高可信来源。
- 单一来源不能同时证明作品存在、作者、平台、类型、热度和排名。
- 作品存在、作者、平台、出版状态、类型和热度必须分别核验。
- 没有时间范围的热度不能用于年度比较。
- 没有平台范围的排名不能用于跨平台比较。
- 搜索热度不能直接等于阅读量。
- 榜单位置不能直接等于作品质量。
- 编辑推荐不能直接等于全网热门。
- 来源互相矛盾时保留全部来源。
- 不得静默选择冲突来源。
- 无法核验时使用 unverified、conflicting 或 pending_review。
- 不得使用模型推理填补来源事实。

## 三、核验状态枚举

- verified：已核验
- partially_verified：部分核验
- unverified：未核验
- conflicting：存在冲突
- unavailable：来源不可用
- pending_review：待复核

## 四、核验检查项

- [ ] 作品标题是否与来源一致
- [ ] 作者是否与来源一致
- [ ] 平台或出版社是否明确
- [ ] 作品是否存在
- [ ] 发布或出版状态是否明确
- [ ] 发布时间是否明确
- [ ] 类型是否明确
- [ ] 子类型是否明确
- [ ] 热度指标是否明确
- [ ] 热度统计时间是否明确
- [ ] 热度统计范围是否明确
- [ ] 来源可靠性是否评估
- [ ] 来源之间是否存在冲突
- [ ] 是否存在版权风险
- [ ] 是否允许进入后续拆解
- [ ] 是否需要补充来源

## 五、禁止事项

- 不得保存小说正文或长对白。
- 不得凭空补充作者、平台和排名。
- 不得使用模型推理填补来源事实。
- 不得静默解决来源冲突。

【《类型系统》作品知识库\来源记录\来源可信度规则.json｜SOURCE[346]｜原文第 638,682 行】
【本条用法】根据来源记录及其独立性按原优先级核对证据。热度、类型和其它作品事实分别核对出处，选择理由对应本步确实用到的字段。
【原文规则字段】{"schema_name":"来源可信度规则","schema_version":"H-0B-1.0.0","description":"来源可信度优先级与核验规则。来源优先级只作为核验参考，不自动替代事实验证。","priority_order":["official_platform","official_publisher","author_official","library_catalog","bibliographic_database","reputable_media","reputable_review","public_catalog","search_result","user_submitted","unknown"],"priority_notes":"来源优先级只作为核验参考，不自动替代事实验证。","rules":[{"rule_id":"SRC_RULE_01","rule":"搜索结果不能单独证明热门","description":"search_result来源不能单独作为作品热度的证明。"},{"rule_id":"SRC_RULE_02","rule":"用户投稿不能自动作为高可信来源","description":"user_submitted来源不能自动作为高可信来源。"},{"rule_id":"SRC_RULE_03","rule":"单一来源不能同时证明作品存在、作者、平台、类型、热度和排名","description":"单一来源不能同时证明作品存在、作者、平台、类型、热度和排名。"},{"rule_id":"SRC_RULE_04","rule":"作品存在、作者、平台、出版状态、类型和热度必须分别核验","description":"作品存在、作者、平台、出版状态、类型和热度必须分别核验。"},{"rule_id":"SRC_RULE_05","rule":"没有时间范围的热度不能用于年度比较","description":"没有时间范围的热度不能用于年度比较。"},{"rule_id":"SRC_RULE_06","rule":"没有平台范围的排名不能用于跨平台比较","description":"没有平台范围的排名不能用于跨平台比较。"},{"rule_id":"SRC_RULE_07","rule":"搜索热度不能直接等于阅读量","description":"搜索热度不能直接等于阅读量。"},{"rule_id":"SRC_RULE_08","rule":"榜单位置不能直接等于作品质量","description":"榜单位置不能直接等于作品质量。"},{"rule_id":"SRC_RULE_09","rule":"编辑推荐不能直接等于全网热门","description":"编辑推荐不能直接等于全网热门。"},{"rule_id":"SRC_RULE_10","rule":"来源互相矛盾时保留全部来源","description":"来源互相矛盾时保留全部来源。"},{"rule_id":"SRC_RULE_11","rule":"不得静默选择冲突来源","description":"不得静默选择冲突来源。"},{"rule_id":"SRC_RULE_12","rule":"无法核验时使用unverified、conflicting或pending_review","description":"无法核验时使用unverified、conflicting或pending_review。"},{"rule_id":"SRC_RULE_13","rule":"不得使用模型推理填补来源事实","description":"不得使用模型推理填补来源事实。"}]}

【《类型系统》作品知识库\来源记录\来源可信度枚举.json｜SOURCE[347]｜原文第 638,932 行】
【本条用法】读取 H-0B 来源的类别、核验状态、证据类型及记录状态时逐项沿用原枚举。当前用到的证据须保有原资格和判断范围。
【原文规则字段】{"schema_name":"来源可信度枚举","schema_version":"H-0B-1.0.0","description":"来源可信度相关枚举值定义。","source_type":["official_platform","official_publisher","author_official","library_catalog","bibliographic_database","reputable_media","reputable_review","public_catalog","search_result","user_submitted","unknown"],"verification_status":["verified","partially_verified","unverified","conflicting","unavailable","pending_review"],"evidence_type":["template","fixture","normalized","verified","audit"],"status":["active","fixture_only","pending","rejected","deprecated"],"reliability_scale":{"min":0,"max":1,"description":"来源可信度评分范围，0到1之间。"}}

【《类型系统》作品知识库\来源记录\来源字段说明.json｜SOURCE[348]｜原文第 639,027 行】
【本条用法】按项目收到的来源记录核对原字段含义。实际定位依 URL 或路径、检索时间、来源标识及范围。热度数据另外核对截止时间和统计窗口，未知字段沿用 null。
【原文规则字段】{"schema_name":"来源字段说明","schema_version":"H-0B-1.0.0","description":"来源记录各字段的详细说明与填写规范。本阶段仅建立结构，不采集真实作品。","fields":{"source_record_id":{"required":true,"type":"string","prefix":"SRC_","description":"来源记录唯一标识。正式对象使用SRC_前缀；测试夹具使用FIXTURE_H0B_前缀。不能为空，不能重复。"},"work_id":{"required":false,"type":"string|null","prefix":"WORK_","description":"关联作品标识。模板或未关联对象可为null。"},"source_type":{"required":true,"type":"enum","values":["official_platform","official_publisher","author_official","library_catalog","bibliographic_database","reputable_media","reputable_review","public_catalog","search_result","user_submitted","unknown"],"description":"来源类型。"},"source_name":{"required":true,"type":"string","description":"来源名称，不能为空。"},"source_url":{"required":false,"type":"string|null","description":"来源URL。与source_path至少有一个，正式核验对象才可标记verified。"},"source_path":{"required":false,"type":"string|null","description":"来源本地路径。与source_url至少有一个。"},"platform":{"required":false,"type":"string|null","description":"来源所属平台。未知使用null，不得凭空补充。"},"region":{"required":false,"type":"string|null","description":"来源地区范围。未知使用null。"},"language":{"required":false,"type":"string|null","description":"来源语言。未知使用null。"},"title_as_shown":{"required":false,"type":"string|null","description":"来源中显示的作品标题。不得凭空补充。"},"author_as_shown":{"required":false,"type":"string|null","description":"来源中显示的作者。不得凭空补充。"},"published_at":{"required":false,"type":"datetime|null","description":"来源发布或出版时间。未知使用null。"},"updated_at":{"required":false,"type":"datetime|null","description":"来源更新时间。未知使用null。"},"retrieved_at":{"required":true,"type":"datetime","description":"来源检索时间，必须记录。"},"data_as_of":{"required":false,"type":"datetime|null","description":"热度数据统计截止时间。热度数据必须有。"},"time_scope":{"required":false,"type":"string|null","description":"热度数据时间范围。热度数据必须有。"},"metric_name":{"required":false,"type":"string|null","description":"指标名称。metric_value必须同时有metric_name、metric_unit和time_scope。"},"metric_value":{"required":false,"type":"string|number|null","description":"指标值。"},"metric_unit":{"required":false,"type":"string|null","description":"指标单位。"},"ranking_scope":{"required":false,"type":"string|null","description":"排名范围。ranking_position必须同时有ranking_scope。"},"ranking_position":{"required":false,"type":"string|number|null","description":"排名位置。"},"source_reliability":{"required":true,"type":"float","min":0,"max":1,"description":"来源可信度评分。"},"verification_status":{"required":true,"type":"enum","values":["verified","partially_verified","unverified","conflicting","unavailable","pending_review"],"description":"核验状态。"},"source_summary":{"required":true,"type":"string","description":"来源简短摘要，不得保存小说正文或长对白。"},"evidence_excerpt":{"required":false,"type":"string|null","description":"证据摘录，不得保存小说正文或长对白。"},"copyright_safe":{"required":true,"type":"boolean","description":"是否无版权风险。"},"source_hash":{"required":false,"type":"string|null","description":"来源内容哈希。"},"source_refs":{"required":true,"type":"array","description":"来源引用列表。"},"evidence_type":{"required":true,"type":"enum","values":["template","fixture","normalized","verified","audit"],"description":"证据类型。template=空模板，fixture=测试夹具。"},"confidence":{"required":true,"type":"float","min":0,"max":1,"description":"置信度。"},"status":{"required":true,"type":"enum","values":["active","fixture_only","pending","rejected","deprecated"],"description":"对象状态。"},"schema_version":{"required":true,"type":"string","description":"Schema版本。"}},"rules":["source_url和source_path至少有一个，正式核验对象才可标记verified","source_name不能为空","retrieved_at必须记录","热度数据必须有data_as_of和time_scope","source_summary只能是简短摘要","evidence_excerpt不得保存小说正文","evidence_excerpt不得保存长对白","未知字段使用null","不得凭空补充作者、平台和排名"]}

【《类型系统》作品知识库\人工复核\来源核验表模板.json｜SOURCE[371]｜原文第 642,295 行】
【本条用法】以项目实际提供的人工核验表为据，读取关注字段、冲突、复核人、时间及决定。approve_with_limits 按表中的具体范围使用，模板值只供识别字段。
【原文规则字段】{"schema_name":"来源核验表模板","schema_version":"H-0B-1.0.0","description":"来源人工核验表模板。仅包含字段名和空值，不包含真实作品。","template":{"work_id":null,"source_record_ids":[],"checked_fields":[],"verified_fields":[],"unverified_fields":[],"conflicting_fields":[],"copyright_review":null,"reviewer":null,"reviewed_at":null,"review_decision":null,"review_notes":null,"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"},"review_fields":["作品标题","作者","平台或出版社","作品存在","发布或出版状态","发布时间","类型","子类型","热度指标","热度统计时间","热度统计范围","来源可靠性","来源之间冲突","是否存在版权风险","是否允许进入后续拆解","是否需要补充来源"],"review_decisions":["approve","approve_with_limits","reject","pending","needs_more_sources"]}

【《类型系统》作品知识库\人工复核\来源核验流程.md｜SOURCE[372]｜原文第 642,391 行】
【本条用法】使用项目确有的人工复核结果，通过已核验、未核验及冲突字段说明参考的取用范围。涉及本项目实际依赖的字段且证据仍缺失时，按本步原有边界记录。
【原文】
# 来源核验流程

> 本流程用于人工核验来源记录。本阶段仅建立结构，不采集真实作品。

## 一、核验字段

人工核验至少检查以下字段：

- 作品标题
- 作者
- 平台或出版社
- 作品存在
- 发布或出版状态
- 发布时间
- 类型
- 子类型
- 热度指标
- 热度统计时间
- 热度统计范围
- 来源可靠性
- 来源之间冲突
- 是否存在版权风险
- 是否允许进入后续拆解
- 是否需要补充来源

## 二、核验结果

核验结果至少包含：

- work_id：关联作品标识
- source_record_ids：涉及来源记录标识列表
- checked_fields：已检查字段列表
- verified_fields：已核验字段列表
- unverified_fields：未核验字段列表
- conflicting_fields：冲突字段列表
- copyright_review：版权审查结果
- reviewer：复核人
- reviewed_at：复核时间
- review_decision：复核决定
- review_notes：复核备注
- evidence_type：证据类型
- status：对象状态
- schema_version：Schema版本

## 三、复核决定

- approve：批准
- approve_with_limits：有条件批准
- reject：拒绝
- pending：待定
- needs_more_sources：需要更多来源

## 四、流程

1. 收集来源记录。
2. 逐项核验字段。
3. 记录已核验、未核验和冲突字段。
4. 进行版权审查。
5. 给出复核决定。
6. 更新来源记录状态。

## 五、禁止事项

- 不得使用模型推理填补来源事实。
- 不得静默解决冲突。
- 冲突未解决的作品不得标记 fully_verified。
"""

METRIC_REVIEW_MATERIAL = r"""
【已有作品参考的热度与指标范围】
需要用已经提供的热度或排名解释参考取用时，才核对相应指标条目。按来源实际适用的版本、平台、地区、时间和单位说明比较依据。旧模板定义提供核对口径，各项统计值与结论用本项目提供的来源记录。

【《类型系统》作品热度口径.json｜SOURCE[82]｜原文第 603,451 行】
【本条用法】本项目的参考取用确实依赖热度时，按原定义检查指标、时间、范围及其它所需字段。使用可对照的结论作为候选选择依据。
【原文规则字段】{"schema_name":"作品热度口径","schema_version":"TYPE_F-1.0.0","metrics":{"platform_ranking":{"description":"平台排名","requires_scope":true},"view_count":{"description":"浏览次数","requires_time_range":true},"collection_count":{"description":"收藏数","requires_time_range":true},"recommendation_count":{"description":"推荐票数","requires_time_range":true},"rating":{"description":"评分","requires_sample_size":true},"review_count":{"description":"评论数","requires_time_range":true},"sales_rank":{"description":"销售排名","requires_scope":true},"library_circulation":{"description":"借阅量","requires_time_range":true},"citation_count":{"description":"引用数","requires_field":true},"award":{"description":"获奖","requires_award_name":true}},"rules":["不同平台的热度不能直接混合比较","热门只能在明确时间、平台和指标下成立","排名和热度必须保存来源和口径","无明确指标的不得声称最热门"]}

【《类型系统》作品知识库\来源记录\平台分类.json｜SOURCE[350]｜原文第 639,629 行】
【本条用法】评估两份平台数据前先查实际记录的平台类型与标识，区分连载平台、出版社、评论与其它来源的覆盖范围。平台类目只说明数据来自哪类渠道。
【原文规则字段】{"schema_name":"平台分类","schema_version":"H-0B-1.0.0","description":"平台分类定义。本阶段仅建立结构，不采集真实作品。","platform_types":["web_serial_platform","ebook_platform","print_publisher","library_catalog","audiobook_platform","comic_or_adaptation_platform","video_adaptation_platform","review_platform","search_engine","social_platform","official_author_channel","official_publisher_channel","other","unknown"],"platform_object_required_fields":["platform_id","platform_name","platform_type","region","language","public_or_private","access_method","access_status","available_metrics","unavailable_metrics","metric_update_frequency","source_reliability","platform_scope","notes","source_refs","evidence_type","confidence","status","schema_version"]}

【《类型系统》作品知识库\来源记录\平台指标兼容矩阵.json｜SOURCE[351]｜原文第 639,834 行】
【本条用法】按实际记录逐项确认指标组合、平台、统计窗口和地区。原标 comparable=false 的矩阵项保留为不可直接比较，实际结论附上下文和出处。
【原文表头】{"schema_name":"平台指标兼容矩阵","schema_version":"H-0B-1.0.0","description":"平台指标兼容矩阵，记录不同指标之间是否可直接比较。本阶段仅建立结构，不采集真实作品。","matrix_required_fields":["metric_a","metric_b","same_platform_required","same_time_scope_required","same_region_required","comparable","comparison_warning","source_refs","evidence_type","status"]}
【原文逐条字段】comparisons
【原文记录】{"metric_a":"reading_count","metric_b":"reading_count","same_platform_required":true,"same_time_scope_required":true,"same_region_required":true,"comparable":false,"comparison_warning":"不同平台阅读量不可直接比较","source_refs":[],"evidence_type":"template","status":"active"}
【原文记录】{"metric_a":"collection_count","metric_b":"collection_count","same_platform_required":true,"same_time_scope_required":true,"same_region_required":true,"comparable":false,"comparison_warning":"不同平台收藏量不可直接比较","source_refs":[],"evidence_type":"template","status":"active"}
【原文记录】{"metric_a":"comment_count","metric_b":"comment_count","same_platform_required":true,"same_time_scope_required":true,"same_region_required":true,"comparable":false,"comparison_warning":"不同平台评论量不可直接比较","source_refs":[],"evidence_type":"template","status":"active"}
【原文记录】{"metric_a":"ranking","metric_b":"ranking","same_platform_required":true,"same_time_scope_required":true,"same_region_required":true,"comparable":false,"comparison_warning":"不同时间范围排名不可直接比较","source_refs":[],"evidence_type":"template","status":"active"}
【原文记录】{"metric_a":"search_interest","metric_b":"reading_count","same_platform_required":true,"same_time_scope_required":true,"same_region_required":true,"comparable":false,"comparison_warning":"搜索指数与阅读量不可直接比较","source_refs":[],"evidence_type":"template","status":"active"}
【原文记录】{"metric_a":"editorial_selection","metric_b":"sales","same_platform_required":true,"same_time_scope_required":true,"same_region_required":true,"comparable":false,"comparison_warning":"编辑推荐与销量不可直接比较","source_refs":[],"evidence_type":"template","status":"active"}
【原文记录】{"metric_a":"ranking","metric_b":"rating","same_platform_required":true,"same_time_scope_required":true,"same_region_required":true,"comparable":false,"comparison_warning":"榜单排名与作品质量不可直接比较","source_refs":[],"evidence_type":"template","status":"active"}

【《类型系统》作品知识库\来源记录\平台字段说明.json｜SOURCE[352]｜原文第 639,987 行】
【本条用法】源记录给出平台资料时，查平台 ID、名称、渠道类型、地区、语言和实际声明的统计范围，判断排名与指标在本次是否适用。
【原文规则字段】{"schema_name":"平台字段说明","schema_version":"H-0B-1.0.0","description":"平台对象各字段的详细说明。本阶段仅建立结构，不采集真实作品。","fields":{"platform_id":{"required":true,"type":"string","prefix":"PLAT_","description":"平台唯一标识。"},"platform_name":{"required":true,"type":"string","description":"平台名称。"},"platform_type":{"required":true,"type":"enum","values":["web_serial_platform","ebook_platform","print_publisher","library_catalog","audiobook_platform","comic_or_adaptation_platform","video_adaptation_platform","review_platform","search_engine","social_platform","official_author_channel","official_publisher_channel","other","unknown"],"description":"平台类型。"},"region":{"required":true,"type":"string|null","description":"平台地区范围。未知使用null。"},"language":{"required":true,"type":"string|null","description":"平台语言。未知使用null。"},"public_or_private":{"required":true,"type":"enum","values":["public","private","unknown"],"description":"平台公开或私有。"},"access_method":{"required":true,"type":"string|null","description":"访问方式。未知使用null。"},"access_status":{"required":true,"type":"enum","values":["accessible","restricted","unavailable","unknown"],"description":"访问状态。"},"available_metrics":{"required":true,"type":"array","description":"平台可提供的指标列表。"},"unavailable_metrics":{"required":true,"type":"array","description":"平台不可提供的指标列表。"},"metric_update_frequency":{"required":true,"type":"string|null","description":"指标更新频率。未知使用null。"},"source_reliability":{"required":true,"type":"float","min":0,"max":1,"description":"平台来源可信度评分。"},"platform_scope":{"required":true,"type":"string|null","description":"平台范围（如全网、单平台）。未知使用null。"},"notes":{"required":true,"type":"string|null","description":"备注。"},"source_refs":{"required":true,"type":"array","description":"来源引用列表。"},"evidence_type":{"required":true,"type":"enum","values":["template","fixture","normalized","verified","audit"],"description":"证据类型。"},"confidence":{"required":true,"type":"float","min":0,"max":1,"description":"置信度。"},"status":{"required":true,"type":"enum","values":["active","fixture_only","pending","rejected","deprecated"],"description":"对象状态。"},"schema_version":{"required":true,"type":"string","description":"Schema版本。"}}}

【《类型系统》作品知识库\来源记录\热度比较规则.json｜SOURCE[353]｜原文第 640,299 行】
【本条用法】本项目依据热度挑选作品参考时，逐项核对原比较规则。用真实时间和平台范围判断能否比较，缺少来源或可比口径的项目在采用理由中标待核。
【原文规则字段】{"schema_name":"热度比较规则","schema_version":"H-0B-1.0.0","description":"热度指标比较规则。本阶段仅建立结构，不采集真实作品。","rules":[{"rule_id":"HEAT_RULE_01","rule":"热门不是一个无条件布尔值","description":"热门必须绑定具体指标、时间范围和平台范围。"},{"rule_id":"HEAT_RULE_02","rule":"爆款必须拆解为可验证指标","description":"爆款必须拆解为可验证指标。"},{"rule_id":"HEAT_RULE_03","rule":"2026热门必须绑定具体统计时间","description":"2026热门必须绑定具体统计时间。"},{"rule_id":"HEAT_RULE_04","rule":"年度榜单和实时榜单必须分开","description":"年度榜单和实时榜单必须分开。"},{"rule_id":"HEAT_RULE_05","rule":"平台榜单和全网榜单必须分开","description":"平台榜单和全网榜单必须分开。"},{"rule_id":"HEAT_RULE_06","rule":"单项指标不能自动代表作品综合质量","description":"单项指标不能自动代表作品综合质量。"},{"rule_id":"HEAT_RULE_07","rule":"缺少来源时只能标记pending","description":"缺少来源时只能标记pending。"},{"rule_id":"HEAT_RULE_08","rule":"不同平台阅读量不可直接比较","description":"不同平台阅读量不可直接比较。"},{"rule_id":"HEAT_RULE_09","rule":"不同平台收藏量不可直接比较","description":"不同平台收藏量不可直接比较。"},{"rule_id":"HEAT_RULE_10","rule":"不同平台评论量不可直接比较","description":"不同平台评论量不可直接比较。"},{"rule_id":"HEAT_RULE_11","rule":"不同时间范围排名不可直接比较","description":"不同时间范围排名不可直接比较。"},{"rule_id":"HEAT_RULE_12","rule":"搜索指数与阅读量不可直接比较","description":"搜索指数与阅读量不可直接比较。"},{"rule_id":"HEAT_RULE_13","rule":"编辑推荐与销量不可直接比较","description":"编辑推荐与销量不可直接比较。"},{"rule_id":"HEAT_RULE_14","rule":"榜单排名与作品质量不可直接比较","description":"榜单排名与作品质量不可直接比较。"}]}

【《类型系统》作品知识库\来源记录\热度指标Schema.json｜SOURCE[354]｜原文第 640,426 行】
【本条用法】评估来源提供的热度指标时，依原字段查单位、覆盖范围、聚合办法、来源要求及解释边界。用原原则说明当前指标能证明的具体事项。
【原文规则字段】{"schema_name":"热度指标Schema","schema_version":"H-0B-1.0.0","description":"热度指标对象Schema。本阶段仅建立结构，不采集真实作品。","object_kind":"heat_metric","required_fields":["metric_id","metric_name","metric_definition","metric_unit","platform_scope","region_scope","time_scope","aggregation_method","comparable_with","not_comparable_with","minimum_source_requirements","confidence_requirements","known_biases","interpretation_limits","source_refs","evidence_type","status","schema_version"],"fields":{"metric_id":{"type":"string","prefix":"M_","required":true,"description":"指标唯一标识"},"metric_name":{"type":"string","required":true,"description":"指标名称"},"metric_definition":{"type":"string","required":true,"description":"指标定义"},"metric_unit":{"type":"string","required":true,"description":"指标单位"},"platform_scope":{"type":"string","required":true,"description":"平台范围要求"},"region_scope":{"type":"string","required":true,"description":"地区范围要求"},"time_scope":{"type":"string","required":true,"description":"时间范围要求"},"aggregation_method":{"type":"string","required":true,"description":"聚合方法"},"comparable_with":{"type":"array","required":true,"description":"可比较指标列表"},"not_comparable_with":{"type":"array","required":true,"description":"不可比较指标列表"},"minimum_source_requirements":{"type":"string","required":true,"description":"最低来源要求"},"confidence_requirements":{"type":"string","required":true,"description":"置信度要求"},"known_biases":{"type":"array","required":true,"description":"已知偏差"},"interpretation_limits":{"type":"string","required":true,"description":"解释限制"},"source_refs":{"type":"array","required":true,"description":"来源引用列表"},"evidence_type":{"type":"enum","values":["template","fixture","normalized","verified","audit"],"required":true,"description":"证据类型"},"status":{"type":"enum","values":["active","fixture_only","pending","rejected","deprecated"],"required":true,"description":"对象状态"},"schema_version":{"type":"string","required":true,"description":"Schema版本"}},"principles":["热门不是一个无条件布尔值","爆款必须拆解为可验证指标","2026热门必须绑定具体统计时间","年度榜单和实时榜单必须分开","平台榜单和全网榜单必须分开","单项指标不能自动代表作品综合质量","缺少来源时只能标记pending"]}

【《类型系统》作品知识库\来源记录\热度指标口径.json｜SOURCE[355]｜原文第 640,731 行】
【本条用法】查本次实际出现的指标名称和原口径，核对单位、原列可比较性、最少来源、已知偏差与解释限制，再记录适用结论。
【原文表头】{"schema_name":"热度指标口径","schema_version":"H-0B-1.0.0","description":"热度指标口径定义。本阶段仅建立结构，不采集真实作品。","principles":["热门不是一个无条件布尔值","爆款必须拆解为可验证指标","2026热门必须绑定具体统计时间","年度榜单和实时榜单必须分开","平台榜单和全网榜单必须分开","单项指标不能自动代表作品综合质量","缺少来源时只能标记pending"]}
【原文逐条字段】metrics
【原文记录】{"metric_id":"M_RANKING","metric_name":"ranking","metric_definition":"榜单排名","metric_unit":"position","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"rank","comparable_with":[],"not_comparable_with":["rating","sales","reading_count"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["榜单位置不能直接等于作品质量"],"interpretation_limits":"榜单排名不能直接等于作品质量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_POPULARITY_SCORE","metric_name":"popularity_score","metric_definition":"综合热度评分","metric_unit":"score","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"composite","comparable_with":[],"not_comparable_with":["reading_count","view_count"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["综合评分口径不统一"],"interpretation_limits":"综合评分不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_READING_COUNT","metric_name":"reading_count","metric_definition":"阅读量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":["view_count","search_interest"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["不同平台阅读量口径不同"],"interpretation_limits":"不同平台阅读量不可直接比较","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_VIEW_COUNT","metric_name":"view_count","metric_definition":"浏览量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":["reading_count"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["浏览量口径不统一"],"interpretation_limits":"浏览量不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_COLLECTION_COUNT","metric_name":"collection_count","metric_definition":"收藏量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":["collection_count"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["不同平台收藏量口径不同"],"interpretation_limits":"不同平台收藏量不可直接比较","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_RECOMMENDATION_COUNT","metric_name":"recommendation_count","metric_definition":"推荐量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["推荐量口径不统一"],"interpretation_limits":"推荐量不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_COMMENT_COUNT","metric_name":"comment_count","metric_definition":"评论量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":["comment_count"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["不同平台评论量口径不同"],"interpretation_limits":"不同平台评论量不可直接比较","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_RATING","metric_name":"rating","metric_definition":"评分","metric_unit":"score","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"average","comparable_with":[],"not_comparable_with":["ranking","sales"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["评分不能直接等于作品质量"],"interpretation_limits":"评分不能直接等于作品质量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_SALES","metric_name":"sales","metric_definition":"销量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":["editorial_selection","rating"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["销量口径不统一"],"interpretation_limits":"销量不能直接等于作品质量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_AWARD","metric_name":"award","metric_definition":"获奖","metric_unit":"award","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"nominal","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["获奖不能直接等于全网热门"],"interpretation_limits":"获奖不能直接等于全网热门","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_EDITORIAL_SELECTION","metric_name":"editorial_selection","metric_definition":"编辑推荐","metric_unit":"selection","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"nominal","comparable_with":[],"not_comparable_with":["sales"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["编辑推荐不能直接等于全网热门"],"interpretation_limits":"编辑推荐不能直接等于全网热门","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_PLATFORM_FEATURE","metric_name":"platform_feature","metric_definition":"平台推荐位","metric_unit":"feature","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"nominal","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["平台推荐位不能直接等于全网热门"],"interpretation_limits":"平台推荐位不能直接等于全网热门","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_SEARCH_INTEREST","metric_name":"search_interest","metric_definition":"搜索指数","metric_unit":"index","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"index","comparable_with":[],"not_comparable_with":["reading_count","view_count"],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["搜索热度不能直接等于阅读量"],"interpretation_limits":"搜索热度不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_CITATION_COUNT","metric_name":"citation_count","metric_definition":"引用量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["引用量口径不统一"],"interpretation_limits":"引用量不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_SUBSCRIPTION_COUNT","metric_name":"subscription_count","metric_definition":"订阅量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["订阅量口径不统一"],"interpretation_limits":"订阅量不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_COMPLETION_COUNT","metric_name":"completion_count","metric_definition":"完读量","metric_unit":"count","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"sum","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["完读量口径不统一"],"interpretation_limits":"完读量不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_RETENTION_RATE","metric_name":"retention_rate","metric_definition":"留存率","metric_unit":"percent","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"rate","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["留存率口径不统一"],"interpretation_limits":"留存率不能直接等于阅读量","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_UPDATE_FREQUENCY","metric_name":"update_frequency","metric_definition":"更新频率","metric_unit":"frequency","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"rate","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["更新频率不能直接等于热度"],"interpretation_limits":"更新频率不能直接等于热度","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
【原文记录】{"metric_id":"M_USER_DEFINED_METRIC","metric_name":"user_defined_metric","metric_definition":"用户自定义指标","metric_unit":"custom","platform_scope":"required","region_scope":"required","time_scope":"required","aggregation_method":"custom","comparable_with":[],"not_comparable_with":[],"minimum_source_requirements":"必须有平台范围和时间范围","confidence_requirements":"来源可信度需评估","known_biases":["自定义指标口径需明确"],"interpretation_limits":"自定义指标需明确口径","source_refs":[],"evidence_type":"template","status":"active","schema_version":"H-0B-1.0.0"}
"""

RECORD_REVIEW_MATERIAL = r"""
【已有作品来源记录与作品总表】
本项目确有作者已确认的作品参考时，对照实际提供的来源记录模板、核验结果和作品登记条目。各字段限于记录原来可支持的范围，选择理由仍按当前需求和已读证据落到本步 adaptations 或 boundaries。

【来源导入与来源记录的原文共用字段】{"source_record_id":null,"work_id":null,"source_type":null,"source_name":null,"source_url":null,"source_path":null,"platform":null,"region":null,"language":null,"title_as_shown":null,"author_as_shown":null,"published_at":null,"updated_at":null,"retrieved_at":null,"data_as_of":null,"time_scope":null,"metric_name":null,"metric_value":null,"metric_unit":null,"ranking_scope":null,"ranking_position":null,"source_reliability":null,"verification_status":null,"source_summary":null,"evidence_excerpt":null,"copyright_safe":null,"source_hash":null,"source_refs":[],"evidence_type":"template","confidence":null,"status":"active","schema_version":"H-0B-1.0.0"}

【《类型系统》作品知识库\来源记录\来源导入模板.csv｜SOURCE[341]｜原文第 638,227 行】
【本条用法】在项目确有 H-0B 格式的 CSV 记录时，用原 32 个列名核对来源、关联作品、统计和复核字段。空表用于识别格式，实际内容随收到的记录核对。
【原文】
source_record_id,work_id,source_type,source_name,source_url,source_path,platform,region,language,title_as_shown,author_as_shown,published_at,updated_at,retrieved_at,data_as_of,time_scope,metric_name,metric_value,metric_unit,ranking_scope,ranking_position,source_reliability,verification_status,source_summary,evidence_excerpt,copyright_safe,source_hash,source_refs,evidence_type,confidence,status,schema_version

【《类型系统》作品知识库\来源记录\来源导入模板.json｜SOURCE[342]｜原文第 638,232 行】
【本条用法】项目收到 H-0B 的 JSON 来源记录时，按原字段及十条导入规则核对可追溯性和已完成的导入状态。本步使用已经提供的核验依据。原 pending 一词须查看实际记录用在对象状态还是核验字段。
【原文表头】{"schema_name":"来源导入模板","schema_version":"H-0B-1.0.0","description":"来源记录导入模板。仅包含字段名和空值，不包含真实作品。","template_fields":["source_record_id","work_id","source_type","source_name","source_url","source_path","platform","region","language","title_as_shown","author_as_shown","published_at","updated_at","retrieved_at","data_as_of","time_scope","metric_name","metric_value","metric_unit","ranking_scope","ranking_position","source_reliability","verification_status","source_summary","evidence_excerpt","copyright_safe","source_hash","source_refs","evidence_type","confidence","status","schema_version"],"import_rules":["缺少source_record_id时拒绝","缺少source_name时拒绝","缺少source_url和source_path时标记unavailable或pending","缺少retrieved_at时拒绝正式verified","热度数据缺少data_as_of时标记pending","ranking_position必须同时有ranking_scope","metric_value必须同时有metric_name、metric_unit和time_scope","不允许把长文本、正文或长对白导入","不允许导入未标记来源的事实","导入失败不能覆盖已有数据"]}
【共用字段位置】原文 template 取本段的「来源导入与来源记录的原文共用字段」。

【《类型系统》作品知识库\来源记录\来源导入说明.md｜SOURCE[343]｜原文第 638,480 行】
【本条用法】核对已导入来源的出处与字段条件时读本条，与前面来源核验及人工复核结论合用。用当前实际输入说明记录能支持的取用范围。
【原文】
# 来源导入说明

> 本说明用于指导来源记录的导入。本阶段仅建立结构，不采集真实作品。

## 一、导入模板

- 来源导入模板.csv：CSV格式模板，仅包含字段名。
- 来源导入模板.json：JSON格式模板，仅包含字段名和空值。

模板不包含任何真实作品数据。

## 二、导入规则

1. 缺少 source_record_id 时拒绝。
2. 缺少 source_name 时拒绝。
3. 缺少 source_url 和 source_path 时标记 unavailable 或 pending。
4. 缺少 retrieved_at 时拒绝正式 verified。
5. 热度数据缺少 data_as_of 时标记 pending。
6. ranking_position 必须同时有 ranking_scope。
7. metric_value 必须同时有 metric_name、metric_unit 和 time_scope。
8. 不允许把长文本、正文或长对白导入。
9. 不允许导入未标记来源的事实。
10. 导入失败不能覆盖已有数据。

## 三、字段说明

- source_record_id：来源记录唯一标识，必填。
- source_name：来源名称，必填。
- source_url：来源URL，与 source_path 至少有一个。
- source_path：来源路径，与 source_url 至少有一个。
- retrieved_at：检索时间，正式 verified 必须记录。
- data_as_of：数据截止时间，热度数据必须记录。
- time_scope：时间范围，热度数据必须记录。
- ranking_scope：排名范围，ranking_position 必须同时有。
- metric_value：指标值，必须同时有 metric_name、metric_unit 和 time_scope。

## 四、禁止事项

- 不得导入小说正文、章节或长对白。
- 不得导入未标记来源的事实。
- 不得使用模型推理填补来源事实。
- 导入失败不得覆盖已有数据。

【《类型系统》作品知识库\来源记录\来源记录模板.json｜SOURCE[345]｜原文第 638,598 行】
【本条用法】对照共用原模板字段读实际来源记录，识别来源 URL、路径、记录时间、范围及复核状态。空默认值表示未提供相应证据。
【共用字段位置】其全部原文值取本段的「来源导入与来源记录的原文共用字段」。

【《类型系统》作品资料库\作品总表.json｜SOURCE[449]｜原文第 653,988 行】
【本条用法】核对实际提供的作品登记信息时，按原表区分作品状态及来源核验。source_verified、partially_verified、analyzed 等状态依实际字段和本项目已有的核验依据使用。原总表的 works 为空，统计值表示该原表的实际记录数。
【原文规则字段】{"schema_version":"TYPE_F-1.0.0","created_at":"2026-07-31T12:08:30.700982","works":[],"total_works":0,"by_status":{"candidate":0,"source_verified":0,"partially_verified":0,"analyzed":0,"pending_review":0,"conflicting":0,"rejected":0,"deprecated":0,"fixture_only":0}}
"""

MATERIAL = '\n'.join((SOURCE_REVIEW_MATERIAL, RECORD_REVIEW_MATERIAL, METRIC_REVIEW_MATERIAL))
