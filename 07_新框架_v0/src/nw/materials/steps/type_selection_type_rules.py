"""类型选择步骤的《类型系统》层级、报告或条件原文。"""

SOURCE_MAPPING_USE = (
    'type_source_mappings 是 TYPE_A 来源映射的参考证据。按 target.source_ref 对照当前实际采用或正在比对的确切分表定义。'
    '在本步依据或边界说明采用了哪一处定义、字段及项目用途。类型总表里的同名同号项按其自己的模式、定义和层级核对。'
    '分别读取原 mapping_type、evidence_type 和 status。normalized、inferred、pending 按原字段解释。'
    '原 active 状态随原件保存，当前资格以 qualification 为准。'
    '映射用于辨认来源和对象，不自动决定选型、混合组件、机制、结构或写法。'
)

MATERIAL = r"""#### 类型选型的层级规则
【类型系统原文位置】类型层级规则.json 第26885行
【本步用法】按作者实际采用的类型、父级及现有出处核对 selection 与 boundaries，逐项给出实际判断依据。两处层级规则按各自原文回查。
【逐条原文值】rule_id 原文行 | rule_id | rule | severity | 本步核对
26892 | HR01 | 主类型(GENRE)只能位于层级1 | error | 核对作者所选主类型的原种类与层级 1，依据实际本体条目记录选型。
26897 | HR02 | 子类型(SUBGENRE)必须有合法的GENRE父节点 | error | 逐条核对所选子类型有可回查的 GENRE 父节点，层级待定时写入 boundaries。
26902 | HR03 | 混合类型(HYBRID_GENRE)必须引用至少2个组件 | error | 核对混合类型的组件 ID 和数量，同时按前处本体规则核对组件的主类型身份，两处原义都保留。
26907 | HR04 | 机制(TROPE_MECHANISM)不能作为类型的父节点 | error | 核对父节点的类型种类。遇到原字段 TROPE_MECHANISM 时保留原名，按有据的身份核对。
26912 | HR05 | 风格(STYLE)不能作为类型的父节点 | error | 所选 STYLE 按作者给定的写法使用，父节点按类型本体核对。
26917 | HR06 | 语气(TONE)不能作为类型的父节点 | error | 所选 TONE 按作者给定的语气使用，父节点按类型本体核对。
26922 | HR07 | 不能存在循环父子关系 | error | 沿实际采用的父节点逐层回查，发现返回自身或前序节点时记录循环关系。
26927 | HR08 | 读者体验标签(AUDIENCE_TAG)与类型不在同一层级维度 | warning | 受众标签按已确认的读者定位记录，所选类型的层级仍按原 ID 核对。
26932 | HR09 | 项目标签(PROJECT_TAG)不能与已有source_fact同名或冒充 | error | 核对项目标签和实际来源事实的原身份及同名处，按出处记录各自的依据。
26937 | HR10 | 空type_id不得进入正式索引 | error | 核对实际 selection 中的 ID 完整。原文索引要求在此用于检查进入正式选型的条目。

【《类型系统》类型动态验证规则｜类型选择】
【原文位置】来源块第 32,597 行。条目前缀是原件中的字段行。
【本步用法】按实际项目对象、已用资料和本步产物核对下列验证项，并将问题定位到已有产物和证据。原件规定 report_only=true、auto_fix_allowed=false。

32620｜reference｜{"validation_id":"TDV_003","check_description":"类型ID是否存在","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】用当前类型总表核对项目采用的准确 ID 及对应名称。别名或同名关系有歧义时如实记录。

【《类型系统》类型多样性策略的维度｜类型选择】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】沿用作者已确认的条件，比较当前步骤实际已有的适用候选。权重保留原值，具体比较依据采用本次已明确的范围。

32928｜reference｜{"id":"type","name":"类型维度","weight":0.08}
【本步用法】有多个已符合作者需求的类型候选时，比对各自承担的读者承诺及设计用途。原权重只提供比较参考。

32933｜reference｜{"id":"subtype","name":"子类型维度","weight":0.06}
【本步用法】在既有类型及本体允许的子类型范围内比较候选的具体差异，保留原父子关系。

【《类型系统》类型来源映射｜类型选择】
【原文位置】来源块第 35,204 行。每项前为对应条目的原件字段行。
【原文属性】{"schema_version":"TYPE_A-1.0.0","updated_at":"2026-07-31T09:42:37.831980"}
【本步用法】本表的来源、目标编码和现行 reference 裁定随条保留。使用本场或本项目实际采用的类型、结构、机制与原定义核对映射，沿用作者确认的项目选择。

35211｜reference｜{"mapping_id":"MAP_0001","source_name":"修仙","source_type":"genre_standard","target_id":"GENRE_XIANXIA","mapping_type":"normalized","reason":"标准化主类型：修仙","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 470,991 行。总表中 GENRE_XIANXIA 的显示名为「仙侠」，「修仙」还出现在子类型 SUB_XIANXIA_03。按作者实际意图核对主类型与子类型范围。

35225｜reference｜{"mapping_id":"MAP_0002","source_name":"玄幻","source_type":"genre_standard","target_id":"GENRE_XUANHUAN","mapping_type":"normalized","reason":"标准化主类型：玄幻","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,107 行。核对作者使用的「玄幻」与原目标 GENRE_XUANHUAN 的主类型定义、项目定位及实际采用依据。

35239｜reference｜{"mapping_id":"MAP_0003","source_name":"都市","source_type":"genre_standard","target_id":"GENRE_DUSHI","mapping_type":"normalized","reason":"标准化主类型：都市","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,208 行。核对作者使用的「都市」与原目标 GENRE_DUSHI 的主类型定义、项目定位及实际采用依据。

35253｜reference｜{"mapping_id":"MAP_0004","source_name":"科幻","source_type":"genre_standard","target_id":"GENRE_KEHUAN","mapping_type":"normalized","reason":"标准化主类型：科幻","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,311 行。核对作者使用的「科幻」与原目标 GENRE_KEHUAN 的主类型定义、项目定位及实际采用依据。

35267｜reference｜{"mapping_id":"MAP_0005","source_name":"悬疑","source_type":"genre_standard","target_id":"GENRE_XUANYI","mapping_type":"normalized","reason":"标准化主类型：悬疑","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,412 行。核对作者使用的「悬疑」与原目标 GENRE_XUANYI 的主类型定义、项目定位及实际采用依据。总表同名条目 SUBJECT_TAG_026 按各自类型身份回查。

35281｜reference｜{"mapping_id":"MAP_0006","source_name":"言情","source_type":"genre_standard","target_id":"GENRE_YANQING","mapping_type":"normalized","reason":"标准化主类型：言情","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,509 行。核对作者使用的「言情」与原目标 GENRE_YANQING 的主类型定义、项目定位及实际采用依据。

35295｜reference｜{"mapping_id":"MAP_0007","source_name":"武侠","source_type":"genre_standard","target_id":"GENRE_WUXIA","mapping_type":"normalized","reason":"标准化主类型：武侠","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,605 行。核对作者使用的「武侠」与原目标 GENRE_WUXIA 的主类型定义、项目定位及实际采用依据。

35309｜reference｜{"mapping_id":"MAP_0008","source_name":"历史","source_type":"genre_standard","target_id":"GENRE_LISHI","mapping_type":"normalized","reason":"标准化主类型：历史","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,706 行。核对作者使用的「历史」与原目标 GENRE_LISHI 的主类型定义、项目定位及实际采用依据。

35323｜reference｜{"mapping_id":"MAP_0009","source_name":"游戏","source_type":"genre_standard","target_id":"GENRE_YOUXI","mapping_type":"normalized","reason":"标准化主类型：游戏","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,806 行。核对作者使用的「游戏」与原目标 GENRE_YOUXI 的主类型定义、项目定位及实际采用依据。总表同名条目 SUBJECT_TAG_043 按各自类型身份回查。

35337｜reference｜{"mapping_id":"MAP_0010","source_name":"竞技","source_type":"genre_standard","target_id":"GENRE_JINGJI","mapping_type":"normalized","reason":"标准化主类型：竞技","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 471,907 行。总表另有「电竞」GENRE_DIANJING 和「体育竞技」GENRE_TIYU。按具体作品的竞赛对象和读者承诺核对本项目采用的定义。

35351｜reference｜{"mapping_id":"MAP_0011","source_name":"末日","source_type":"genre_standard","target_id":"GENRE_MORI","mapping_type":"normalized","reason":"标准化主类型：末日","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,007 行。总表的末世 ID 为 GENRE_MOSHI。按已采用的项目身份和两处原义回查各自的范围。

35365｜reference｜{"mapping_id":"MAP_0012","source_name":"穿越","source_type":"genre_standard","target_id":"GENRE_CHUANYUE","mapping_type":"normalized","reason":"标准化主类型：穿越","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,107 行。总表的「穿越」同时有子类型 SUB_YANQING_37 和题材标签 SUBJECT_TAG_001。结合作者实际选择和标签作用核对身份。

35379｜reference｜{"mapping_id":"MAP_0013","source_name":"军事","source_type":"genre_standard","target_id":"GENRE_JUNSHI","mapping_type":"normalized","reason":"标准化主类型：军事","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,203 行。核对作者使用的「军事」与原目标 GENRE_JUNSHI 的主类型定义、项目定位及实际采用依据。

35393｜reference｜{"mapping_id":"MAP_0014","source_name":"恐怖","source_type":"genre_standard","target_id":"GENRE_KONGBU","mapping_type":"normalized","reason":"标准化主类型：恐怖","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,303 行。核对作者使用的「恐怖」与原目标 GENRE_KONGBU 的主类型定义、项目定位及实际采用依据。总表同名条目 SUBJECT_TAG_028 按各自类型身份回查。

35407｜reference｜{"mapping_id":"MAP_0015","source_name":"奇幻","source_type":"genre_standard","target_id":"GENRE_QIHUAN","mapping_type":"normalized","reason":"标准化主类型：奇幻","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,398 行。核对作者使用的「奇幻」与原目标 GENRE_QIHUAN 的主类型定义、项目定位及实际采用依据。

35421｜reference｜{"mapping_id":"MAP_0016","source_name":"轻小说","source_type":"genre_standard","target_id":"GENRE_QINGSONG","mapping_type":"normalized","reason":"标准化主类型：轻小说","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,498 行。总表的「轻小说」主类型为 GENRE_QINGXIAOSHUO，同名子类型为 SUB_QINGXIAOSHUO_01。按所需层级和确切出处回查。

35435｜reference｜{"mapping_id":"MAP_0017","source_name":"童话/寓言","source_type":"genre_standard","target_id":"GENRE_TONGHUA","mapping_type":"normalized","reason":"标准化主类型：童话/寓言","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,593 行。总表相同 ID 的显示名为「童话与寓言」。按项目实际使用的类别与读者承诺核对两种写法。

35449｜reference｜{"mapping_id":"MAP_0018","source_name":"推理","source_type":"genre_standard","target_id":"GENRE_TUILI","mapping_type":"normalized","reason":"标准化主类型：推理","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,685 行。核对作者使用的「推理」与原目标 GENRE_TUILI 的主类型定义、项目定位及实际采用依据。总表同名条目 SUBJECT_TAG_029 按各自类型身份回查。

35463｜reference｜{"mapping_id":"MAP_0019","source_name":"同人","source_type":"genre_standard","target_id":"GENRE_TONGZHI","mapping_type":"normalized","reason":"标准化主类型：同人","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,781 行。总表将「同人」记为 GENRE_TONGREN。选用时分别核对两处定义和确切 ID。

35477｜reference｜{"mapping_id":"MAP_0020","source_name":"现实","source_type":"genre_standard","target_id":"GENRE_XIANSHI","mapping_type":"normalized","reason":"标准化主类型：现实","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「主类型.json」第 472,866 行。总表同 ID 显示为「现实题材」。核对项目实际体裁目标是否对应这里的来源名称。

35491｜reference｜{"mapping_id":"MAP_0021","source_name":"凡人流","source_type":"subgenre_standard","target_id":"SUBGENRE_XIANXIA_FANREN","mapping_type":"normalized","reason":"标准化子类型：凡人流，父类型GENRE_XIANXIA","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,018 行。用项目实际采用的父项与原表父级 GENRE_XIANXIA 核对「凡人流」的层级。总表同名位置 SUB_XIANXIA_01 依各自父项和定义确认。

35505｜reference｜{"mapping_id":"MAP_0022","source_name":"天才流","source_type":"subgenre_standard","target_id":"SUBGENRE_XIANXIA_TIANCAI","mapping_type":"normalized","reason":"标准化子类型：天才流，父类型GENRE_XIANXIA","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,079 行。用项目实际采用的父项与原表父级 GENRE_XIANXIA 核对「天才流」的层级。按原目标及分表定义回查。

35519｜reference｜{"mapping_id":"MAP_0023","source_name":"重生修仙","source_type":"subgenre_standard","target_id":"SUBGENRE_XIANXIA_ZHONGSHENG","mapping_type":"normalized","reason":"标准化子类型：重生修仙，父类型GENRE_XIANXIA","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,132 行。用项目实际采用的父项与原表父级 GENRE_XIANXIA 核对「重生修仙」的层级。按原目标及分表定义回查。

35533｜reference｜{"mapping_id":"MAP_0024","source_name":"异界玄幻","source_type":"subgenre_standard","target_id":"SUBGENRE_XUANHUAN_YISHIJIE","mapping_type":"normalized","reason":"标准化子类型：异界玄幻，父类型GENRE_XUANHUAN","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,186 行。用项目实际采用的父项与原表父级 GENRE_XUANHUAN 核对「异界玄幻」的层级。按原目标及分表定义回查。

35547｜reference｜{"mapping_id":"MAP_0025","source_name":"商战","source_type":"subgenre_standard","target_id":"SUBGENRE_DUSHI_SHANGZHAN","mapping_type":"normalized","reason":"标准化子类型：商战，父类型GENRE_DUSHI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,238 行。用项目实际采用的父项与原表父级 GENRE_DUSHI 核对「商战」的层级。按原目标及分表定义回查。

35561｜reference｜{"mapping_id":"MAP_0026","source_name":"校园","source_type":"subgenre_standard","target_id":"SUBGENRE_DUSHI_XIAOYUAN","mapping_type":"normalized","reason":"标准化子类型：校园，父类型GENRE_DUSHI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,291 行。用项目实际采用的父项与原表父级 GENRE_DUSHI 核对「校园」的层级。总表同名位置 SUB_DUSHI_18 依各自父项和定义确认。

35575｜reference｜{"mapping_id":"MAP_0027","source_name":"硬科幻","source_type":"subgenre_standard","target_id":"SUBGENRE_KEHUAN_YINGKEHUAN","mapping_type":"normalized","reason":"标准化子类型：硬科幻，父类型GENRE_KEHUAN","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,343 行。用项目实际采用的父项与原表父级 GENRE_KEHUAN 核对「硬科幻」的层级。总表同名位置 SUB_KEHUAN_01 依各自父项和定义确认。

35589｜reference｜{"mapping_id":"MAP_0028","source_name":"赛博朋克","source_type":"subgenre_standard","target_id":"SUBGENRE_KEHUAN_SAIBO","mapping_type":"normalized","reason":"标准化子类型：赛博朋克，父类型GENRE_KEHUAN","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,395 行。总表有主类型、两个子类型和题材标签使用「赛博朋克」。核对作者实际采用的层级、父项与出处。

35603｜reference｜{"mapping_id":"MAP_0029","source_name":"心理悬疑","source_type":"subgenre_standard","target_id":"SUBGENRE_XUANYI_XINLI","mapping_type":"normalized","reason":"标准化子类型：心理悬疑，父类型GENRE_XUANYI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,449 行。用项目实际采用的父项与原表父级 GENRE_XUANYI 核对「心理悬疑」的层级。总表同名位置 SUB_XUANYI_01 依各自父项和定义确认。

35617｜reference｜{"mapping_id":"MAP_0030","source_name":"古言","source_type":"subgenre_standard","target_id":"SUBGENRE_YANQING_GUYAN","mapping_type":"normalized","reason":"标准化子类型：古言，父类型GENRE_YANQING","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,501 行。用项目实际采用的父项与原表父级 GENRE_YANQING 核对「古言」的层级。按原目标及分表定义回查。

35631｜reference｜{"mapping_id":"MAP_0031","source_name":"现言","source_type":"subgenre_standard","target_id":"SUBGENRE_YANQING_XIANYAN","mapping_type":"normalized","reason":"标准化子类型：现言，父类型GENRE_YANQING","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,553 行。用项目实际采用的父项与原表父级 GENRE_YANQING 核对「现言」的层级。按原目标及分表定义回查。

35645｜reference｜{"mapping_id":"MAP_0032","source_name":"穿越历史","source_type":"subgenre_standard","target_id":"SUBGENRE_LISHI_CHUANYUE","mapping_type":"normalized","reason":"标准化子类型：穿越历史，父类型GENRE_LISHI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,605 行。本项将「穿越历史」记在历史子类型下。同名 MAP_0045 为混合组件映射，核对项目采用的具体身份及前置定义。

35659｜reference｜{"mapping_id":"MAP_0033","source_name":"网游","source_type":"subgenre_standard","target_id":"SUBGENRE_YOUXI_WANGYOU","mapping_type":"normalized","reason":"标准化子类型：网游，父类型GENRE_YOUXI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,659 行。用项目实际采用的父项与原表父级 GENRE_YOUXI 核对「网游」的层级。总表同名位置 SUB_YOUXI_01 依各自父项和定义确认。

35673｜reference｜{"mapping_id":"MAP_0034","source_name":"丧尸末日","source_type":"subgenre_standard","target_id":"SUBGENRE_MORI_SANGSHI","mapping_type":"normalized","reason":"标准化子类型：丧尸末日，父类型GENRE_MORI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,712 行。此项父级仍为 GENRE_MORI。用分表原条、总表末世定义以及作者实际采用的分类核对父子边界。

35687｜reference｜{"mapping_id":"MAP_0035","source_name":"重生","source_type":"subgenre_standard","target_id":"SUBGENRE_CHUANYUE_CHONGSHENG","mapping_type":"normalized","reason":"标准化子类型：重生，父类型GENRE_CHUANYUE","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,765 行。总表中的「重生」还见于 SUB_YANQING_36 和 SUBJECT_TAG_002。按作品实际采用的父项及题材用途核对。

35701｜reference｜{"mapping_id":"MAP_0036","source_name":"穿书","source_type":"subgenre_standard","target_id":"SUBGENRE_CHUANYUE_CHUANSHU","mapping_type":"normalized","reason":"标准化子类型：穿书，父类型GENRE_CHUANYUE","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,818 行。用项目实际采用的父项与原表父级 GENRE_CHUANYUE 核对「穿书」的层级。按原目标及分表定义回查。

35715｜reference｜{"mapping_id":"MAP_0037","source_name":"战争史诗","source_type":"subgenre_standard","target_id":"SUBGENRE_JUNSHI_ZHANZHENG","mapping_type":"normalized","reason":"标准化子类型：战争史诗，父类型GENRE_JUNSHI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,871 行。用项目实际采用的父项与原表父级 GENRE_JUNSHI 核对「战争史诗」的层级。按原目标及分表定义回查。

35729｜reference｜{"mapping_id":"MAP_0038","source_name":"剑与魔法","source_type":"subgenre_standard","target_id":"SUBGENRE_QIHUAN_JIANYU","mapping_type":"normalized","reason":"标准化子类型：剑与魔法，父类型GENRE_QIHUAN","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,923 行。用项目实际采用的父项与原表父级 GENRE_QIHUAN 核对「剑与魔法」的层级。总表同名位置 SUB_QIHUAN_02 依各自父项和定义确认。

35743｜reference｜{"mapping_id":"MAP_0039","source_name":"灵异","source_type":"subgenre_standard","target_id":"SUBGENRE_KONGBU_LINGYI","mapping_type":"normalized","reason":"标准化子类型：灵异，父类型GENRE_KONGBU","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 473,975 行。此处为恐怖子类型，现行总表同时有独立主类型 GENRE_LINGYI 和题材标签 SUBJECT_TAG_027。按作者所用的层级与出处核对。

35757｜reference｜{"mapping_id":"MAP_0040","source_name":"本格推理","source_type":"subgenre_standard","target_id":"SUBGENRE_TUILI_BENGE","mapping_type":"normalized","reason":"标准化子类型：本格推理，父类型GENRE_TUILI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 474,028 行。用项目实际采用的父项与原表父级 GENRE_TUILI 核对「本格推理」的层级。总表同名位置 SUB_TUILI_01 依各自父项和定义确认。

35771｜reference｜{"mapping_id":"MAP_0041","source_name":"电子竞技","source_type":"subgenre_standard","target_id":"SUBGENRE_JINGJI_DIANJING","mapping_type":"normalized","reason":"标准化子类型：电子竞技，父类型GENRE_JINGJI","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「子类型.json」第 474,080 行。本项使用竞技父级。总表另有 GENRE_DIANJING 和名为「电子竞技」的 SUB_DIANJING_05，按实际选用的定义与父项回查。

【《类型系统》类型枚举的类型身份｜类型选择】
【原文位置】来源块第 36,337 行。每项前为对应条目的原件字段行。
【原文属性】{"schema_version":"TYPE_A-1.0.0","updated_at":"2026-07-31T09:42:37.831980"}
【本步用法】以下名称及前缀来自 TYPE_A-1.0.0，对照当前条目所属原件核对。项目使用的 ID、类别和层级沿用各自已确认的本体定义。

36343｜{"GENRE":{"description":"主类型","id_prefix":"GENRE_"}}
【本步用法】用本项目实际采用的定义核对主类型身份及原 ID 前缀。

36347｜{"SUBGENRE":{"description":"子类型","id_prefix":"SUBGENRE_"}}
【本步用法】按当前采用的本体和父项核对子类型身份。不同原表前缀分别按来源回查。

36351｜{"HYBRID_GENRE":{"description":"混合类型","id_prefix":"HYBRID_"}}
【本步用法】核对当前候选是否有原件中的混合类型身份、已确认组件和出处。

36371｜{"AUDIENCE_TAG":{"description":"读者体验标签","id_prefix":"AUDIENCE_"}}
【本步用法】按作品真实需求和表现目标核对所用读者标签及其来源。

36375｜{"PROJECT_TAG":{"description":"项目自定义标签","id_prefix":"PROJECT_"}}
【本步用法】使用作者实际建立的项目标签与已确认的项目语义保存原身份。

【《类型系统》类型枚举的映射类型｜类型选择】
【原文位置】来源块第 36,337 行。每项前为对应条目的原件字段行。
【本步用法】以实际名称、规则、原件和项目产物为据记录所用映射的身份、条件与边界。

36388｜"exact"
【本步用法】按原名称和确切目标 ID 核验同一原条。

36389｜"normalized"
【本步用法】核对现有作者用词、规范名称及其来源指向的精确目标。

36390｜"alias"
【本步用法】沿原件已有别名记录和项目实际意义确认目标及适用层级。

36391｜"parent_child"
【本步用法】用本体中实际父项及目标层级核对父子指向。

【《类型系统》类型验证规则｜类型选择】
【原文位置】来源块第 40,879 行。条目前缀为 ID 字段的物理原件行。
【本步用法】按本步实际对象及证据核对适用的原验收项。涉及旧阶段 A、备份、文件清单或原测试的条目，按相应阶段和资料维护范围核对已有记录。

40896｜reference｜{"test_id":"TA03","test":"所有类型对象具有稳定ID","check":"all_ids_present"}
【本步用法】回查已用类型对象在对应原件中的稳定 ID 和类别来源。

40901｜reference｜{"test_id":"TA04","test":"类型ID前缀与type_kind一致","check":"id_prefix_match"}
【本步用法】按本次所用类型的实际来源模式核对 ID 前缀及 type_kind，说明对应原件。

40906｜reference｜{"test_id":"TA05","test":"主类型/子类型/混合类型/机制/结构/风格可区分","check":"type_kind_distinct"}
【本步用法】以当前作者需求和所用明确定义核对主类型、子类型、混合类型、机制、结构及风格的身份。

40911｜reference｜{"test_id":"TA06","test":"子类型父节点引用存在","check":"parent_refs_valid"}
【本步用法】核对实际所选子类型的父节点可从对应本体中的确切 ID 回查。

40921｜reference｜{"test_id":"TA08","test":"不存在循环父子关系","check":"no_circular_parentage"}
【本步用法】按已有父节点引用逐层回查，定位能以实际源位证明的循环。

40926｜reference｜{"test_id":"TA09","test":"不存在空ID","check":"no_empty_ids"}
【本步用法】核对本步引用的明确类型 ID，依原件登记具体空位及其现行资格。

40931｜reference｜{"test_id":"TA10","test":"不存在重复ID","check":"no_duplicate_ids"}
【本步用法】按同一原件及其作用域核对 ID 唯一性，定位实际重复记录的两端。

40936｜reference｜{"test_id":"TA11","test":"同名类型不会被无依据合并","check":"no_unfounded_merges"}
【本步用法】对同名条目核实层级、出处、定义和范围，按实际证据保留项目所用身份。

40946｜reference｜{"test_id":"TA13","test":"无法确认的类型标记pending","check":"unknown_marked_pending"}
【本步用法】用可查来源核对尚无法确认的类型项，保留实际待核条件和原 pending 状态。

40961｜reference｜{"test_id":"TA16","test":"机制不会被当成主类型","check":"mechanism_not_genre"}
【本步用法】按实际主类型和已用机制各自的来源类别核对本次选择及名称。

40966｜reference｜{"test_id":"TA17","test":"风格不会被当成主类型","check":"style_not_genre"}
【本步用法】对照已用主类型和作者指定的风格，核对其在项目产物中的实际身份。

【《类型系统》类型字段说明｜类型选择】
【原文位置】来源块第 42,359 行。条目前缀为对应字段的原件行。
【原文属性】{"schema_version":"TYPE_A-1.0.0","updated_at":"2026-07-31T09:42:37.831980"}
【本步用法】使用本表说明核对采用 TYPE_A-1.0.0 的字段。按该条所属的原模式和现有项目产物确认使用方式。

42365｜{"type_id":{"type":"string","description":"唯一类型ID，前缀标识对象种类","pattern":"^[A-Z]+_[A-Z_0-9]+$","required":true}}
【本步用法】依当前实际采用的类型和所属模式核对精确 ID、原定义及前缀。

42371｜{"type_kind":{"type":"string","description":"类型对象种类","enum":["GENRE","SUBGENRE","HYBRID_GENRE","TROPE_MECHANISM","NARRATIVE_STRUCTURE","STYLE","TONE","AUDIENCE_TAG","PROJECT_TAG"],"required":true}}
【本步用法】根据条目所属的 TYPE_A 原范围核对其类别及本次用途。

42387｜{"canonical_name":{"type":"string","description":"规范名称","required":true}}
【本步用法】依原件规范名记录作者所用对象，并核对同名项对应的实际定义。

42392｜{"display_name":{"type":"string","description":"显示名称","required":true}}
【本步用法】用当前已采用类型的原显示名核对给作者展示时的身份和范围。

42397｜{"aliases":{"type":"array","description":"别名列表","required":false}}
【本步用法】按原件已有别名和实际作者用词核对目标 ID 与定义。

42402｜{"parent_id":{"type":"string|null","description":"父类型ID，null表示顶层","required":true}}
【本步用法】用当前条目的真实父项核对子类型层级，并按原句记录 null 所表示的顶层。

42407｜{"ancestor_ids":{"type":"array","description":"所有祖先ID列表","required":false}}
【本步用法】依已有父子引用追溯完整祖先链，核对本次实际涉及的祖先范围。

42412｜{"child_ids":{"type":"array","description":"直接子类型ID列表","required":false}}
【本步用法】从已采用对象的确切 ID 回查直接子类以及这些子类的真实父项。

42417｜{"level":{"type":"integer|null","description":"层级深度","required":false}}
【本步用法】按所属原件层级和既有父子关系核对层深的含义。

42422｜{"definition":{"type":"string","description":"类型定义","required":true}}
【本步用法】采用原始定义及作者明确目标核对实际类型身份。

42427｜{"scope":{"type":"string","description":"适用范围描述","required":false}}
【本步用法】依原范围和本项目现有需求，核对选择能够覆盖的实际内容。

42432｜{"inclusions":{"type":"array","description":"明确包含的元素","required":false}}
【本步用法】对照已确认的创作需求及原件列明的包含项，说明具体选用的依据。

42437｜{"exclusions":{"type":"array","description":"明确排除的元素","required":false}}
【本步用法】根据原件明确排除的项目及作者需求核对应用边界。

42442｜{"distinguishing_features":{"type":"array","description":"区分特征","required":false}}
【本步用法】使用已有区分特征和当前项目关注点核对相近候选的差别。

42447｜{"common_confusions":{"type":"array","description":"常见混淆项","required":false}}
【本步用法】沿同名项、常见混淆及原定义核对本项目所用的确切身份。

【《类型系统》类型总表｜类型选择】
【原文位置】来源块第 42,543 行。条目前缀为对应字段的原件行。
【本步用法】核对 TYPE_A-1.0.0 原总表以及当前采用条目的名单、层级和计数范围。原件 all_type_ids 起于第 42,563 行，其 103 个 ID 与各层级的成员及顺序一致。

42669｜{"level_0_universal_base":{"description":"通用基础层：跨类型通用概念，不由类型系统定义","source":"通用概念/"}}
【本步用法】依已采用的通用概念来源核对当前类型的实际作用和通用概念原义。

42673｜{"level_1_main_genre":{"description":"主类型层：GENRE","items":["GENRE_XIANXIA","GENRE_XUANHUAN","GENRE_DUSHI","GENRE_KEHUAN","GENRE_XUANYI","GENRE_YANQING","GENRE_WUXIA","GENRE_LISHI","GENRE_YOUXI","GENRE_JINGJI","GENRE_MORI","GENRE_CHUANYUE","GENRE_JUNSHI","GENRE_KONGBU","GENRE_QIHUAN","GENRE_QINGSONG","GENRE_TONGHUA","GENRE_TUILI","GENRE_TONGZHI","GENRE_XIANSHI"]}}
【本步用法】用原主类型成员和各自定义核对作者实际采用的主类型及 ID。

42698｜{"level_2_subgenre":{"description":"子类型层：SUBGENRE","items":["SUBGENRE_XIANXIA_FANREN","SUBGENRE_XIANXIA_TIANCAI","SUBGENRE_XIANXIA_ZHONGSHENG","SUBGENRE_XUANHUAN_YISHIJIE","SUBGENRE_DUSHI_SHANGZHAN","SUBGENRE_DUSHI_XIAOYUAN","SUBGENRE_KEHUAN_YINGKEHUAN","SUBGENRE_KEHUAN_SAIBO","SUBGENRE_XUANYI_XINLI","SUBGENRE_YANQING_GUYAN","SUBGENRE_YANQING_XIANYAN","SUBGENRE_LISHI_CHUANYUE","SUBGENRE_YOUXI_WANGYOU","SUBGENRE_MORI_SANGSHI","SUBGENRE_CHUANYUE_CHONGSHENG","SUBGENRE_CHUANYUE_CHUANSHU","SUBGENRE_JUNSHI_ZHANZHENG","SUBGENRE_QIHUAN_JIANYU","SUBGENRE_KONGBU_LINGYI","SUBGENRE_TUILI_BENGE","SUBGENRE_JINGJI_DIANJING"]}}
【本步用法】对照本表原子类型成员、分表定义和真实父项核对项目采用的层级。

42724｜{"level_3_hybrid":{"description":"混合类型层：HYBRID_GENRE","items":["HYBRID_XIANXIA_YANQING","HYBRID_KEHUAN_XUANYI","HYBRID_DUSHI_XUANYI","HYBRID_CHUANYUE_LISHI","HYBRID_XUANHUAN_MORI"]}}
【本步用法】核对参加组合的候选身份，以及确切混合成员的原出处和实际组件。

42802｜{"level_7_audience":{"description":"读者体验标签层：AUDIENCE_TAG","items":["AUDIENCE_POWER_FANTASY","AUDIENCE_EASY_READ","AUDIENCE_SLOW_BURN","AUDIENCE_FAST_PACED","AUDIENCE_MALE_ORIENTED","AUDIENCE_FEMALE_ORIENTED"]}}
【本步用法】按作者实际确认的体验目标及所用标签的原定义核对对应成员。

42813｜{"level_8_project":{"description":"项目自定义层：PROJECT_TAG","items":[]}}
【本步用法】用作者已建立的项目标签核对这一层的具体用法，保留原表成员的空列表。

【《类型系统》类型组合约束｜类型选择】
【原文位置】来源块第 42,867 行。条目前缀为对应字段的原件行。
【本步用法】按当前选型、适配产物和正式来源证据核对原组合约束。原严重程度及现行参考裁定随条保留。

42879｜reference｜{"constraint_id":"CC02","constraint":"子类型必须引用合法的GENRE主类型","severity":"error"}
【本步用法】用当前子类型所属的原件、真实父节点及 GENRE 身份核对项目选用。

42889｜reference｜{"constraint_id":"CC04","constraint":"机制不能替代主类型","severity":"error"}
【本步用法】按实际选用的原定义和对象类别核对主类型及机制各自的身份。

42894｜reference｜{"constraint_id":"CC05","constraint":"风格不能替代主类型","severity":"error"}
【本步用法】依据作者已经确认的范围核对所用风格与实际主类型的原类别和作用。

42914｜reference｜{"constraint_id":"CC09","constraint":"同一种类对象不能重复使用同一ID","severity":"error"}
【本步用法】按所用模式和同类对象的实际记录核对 ID，定位同一类别内有据可查的重复。
"""
