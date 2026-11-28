"""类型适配步骤直接使用的《类型系统》混合类型原文。"""

MATERIAL = r"""#### 类型总表的 62 个混合类型
【类型系统原文位置】类型本体\类型总表.json 第3095行
【各条共用原文值】type_kind="HYBRID_GENRE" | parent_id=null | level=1 | scope="混合类型"
【逐条原文值】type_id原文行 | type_id | component_type_ids（按原顺序） | canonical_name、display_name、definition、combination_reason 的共同原值 | 本步核对
14533 | HYBRID_XUANHUAN_KEHUAN | ["GENRE_XUANHUAN","GENRE_KEHUAN"] | 玄幻与科幻融合，修炼体系与科技设定并存 | 核对已定修炼体系与科技设定各承担的作用。
14565 | HYBRID_XUANHUAN_LISHI | ["GENRE_XUANHUAN","GENRE_LISHI"] | 玄幻元素融入历史背景 | 核对历史背景范围及已采用的玄幻元素。
14597 | HYBRID_XUANHUAN_XUANYI | ["GENRE_XUANHUAN","GENRE_XUANYI"] | 玄幻世界中的悬疑解谜 | 核对玄幻世界设定与已确认的解谜任务。
14629 | HYBRID_XUANHUAN_JINGYING | ["GENRE_XUANHUAN","GENRE_ZHIYE"] | 玄幻世界中的经营发展 | 核对已确认的经营对象及其在玄幻世界中的发展作用。
14661 | HYBRID_XUANHUAN_ZHONGTIAN | ["GENRE_XUANHUAN","GENRE_XIANSHI"] | 玄幻世界中的种田经营 | 核对已确认的种田、生产或经营对象怎样适用于玄幻背景。
14693 | HYBRID_XUANHUAN_ZHANZHENG | ["GENRE_XUANHUAN","GENRE_JUNSHI"] | 玄幻世界中的大规模战争 | 核对作品已定的大规模战争与玄幻世界规则的关系。
14725 | HYBRID_XIANXIA_XUANYI | ["GENRE_XIANXIA","GENRE_XUANYI"] | 仙侠世界中的悬疑元素 | 核对作者在仙侠设定中选择的悬疑要素。
14757 | HYBRID_XIANXIA_TANAN | ["GENRE_XIANXIA","GENRE_TUILI"] | 仙侠世界中的探案解谜 | 核对仙侠设定与作者已定的探案、解谜方向。
14789 | HYBRID_XIANXIA_QUANMOU | ["GENRE_XIANXIA","GENRE_GONGTING"] | 仙侠世界中的权谋斗争 | 核对作者已定的权谋关系及其在仙侠世界中的作用。
14821 | HYBRID_XIANXIA_JINGYING | ["GENRE_XIANXIA","GENRE_ZHIYE"] | 仙侠世界中的宗门经营 | 核对宗门的身份及作品采用的宗门经营范围。
14853 | HYBRID_XIANXIA_AIQING | ["GENRE_XIANXIA","GENRE_YANQING"] | 仙侠世界中的爱情故事 | 核对作者已确认的仙侠背景与爱情关系各自承担的作用。
14885 | HYBRID_XIANXIA_GUIYI | ["GENRE_XIANXIA","GENRE_LINGYI"] | 仙侠世界中的诡异元素 | 核对已定仙侠设定与诡异元素的适用范围。
14917 | HYBRID_QIHUAN_MAOXIAN | ["GENRE_QIHUAN","GENRE_ZHUTIAN"] | 奇幻世界中的冒险探索 | 核对已定奇幻环境、冒险范围及诸天无限组成是否已由作者采用。
14949 | HYBRID_QIHUAN_ZHENGZHI | ["GENRE_QIHUAN","GENRE_GONGTING"] | 奇幻世界中的政治斗争 | 核对已经明确的奇幻政治背景及权力冲突。
14981 | HYBRID_QIHUAN_ZHANZHENG | ["GENRE_QIHUAN","GENRE_JUNSHI"] | 奇幻世界中的战争 | 核对奇幻世界与作者已定的战争题材范围。
15013 | HYBRID_QIHUAN_ZHONGTIAN | ["GENRE_QIHUAN","GENRE_XIANSHI"] | 奇幻世界中的种田经营 | 核对奇幻设定与已经确认的种田经营方向。
15045 | HYBRID_QIHUAN_JINGYING | ["GENRE_QIHUAN","GENRE_ZHIYE"] | 奇幻世界中的经营发展 | 核对奇幻设定中作者已定的经营发展对象。
15077 | HYBRID_DUSHI_YINENG | ["GENRE_DUSHI","GENRE_XUANHUAN"] | 都市背景中的超能力 | 核对现代都市背景与作者设定的超能力范围。
15109 | HYBRID_DUSHI_XIUXIAN | ["GENRE_DUSHI","GENRE_XIANXIA"] | 都市背景中的修仙元素 | 核对都市环境与作者已定的修仙元素。
15141 | HYBRID_DUSHI_XUANYI | ["GENRE_DUSHI","GENRE_XUANYI"] | 都市背景中的悬疑 | 核对已定都市背景与悬疑任务，并区分前处同 ID 详表。
15173 | HYBRID_DUSHI_LINGYI | ["GENRE_DUSHI","GENRE_LINGYI"] | 都市背景中的灵异 | 核对都市环境里已经确定的灵异现象范围。
15205 | HYBRID_DUSHI_ZHICHANG | ["GENRE_DUSHI","GENRE_ZHIYE"] | 都市背景中的职场 | 核对已定的职场关系、职业发展在都市背景中的作用。
15237 | HYBRID_DUSHI_YULE | ["GENRE_DUSHI","GENRE_ERCIYUAN"] | 都市背景中的娱乐产业 | 核对作品确定的娱乐行业范围及是否有作者确认的二次元组成。
15269 | HYBRID_DUSHI_SHANGYE | ["GENRE_DUSHI","GENRE_ZHIYE"] | 都市背景中的商业 | 核对作者采用的商业对象、经营活动在都市背景中的作用。
15301 | HYBRID_LISHI_CHUANYUE | ["GENRE_LISHI","GENRE_ZHUTIAN"] | 历史背景中的穿越 | 核对已定历史背景与作者确认的穿越方式，标明总表的诸天无限组成。
15333 | HYBRID_LISHI_CHONGSHENG | ["GENRE_LISHI","GENRE_ZHUTIAN"] | 历史背景中的重生 | 核对已定历史背景与作者确认的重生范围，标明总表的诸天无限组成。
15365 | HYBRID_LISHI_QUANMOU | ["GENRE_LISHI","GENRE_GONGTING"] | 历史背景中的权谋 | 核对已定的历史舞台和作品采用的权谋范围。
15397 | HYBRID_LISHI_ZHANZHENG | ["GENRE_LISHI","GENRE_JUNSHI"] | 历史背景中的战争 | 核对已定时期及作品采用的战争背景。
15429 | HYBRID_LISHI_JINGYING | ["GENRE_LISHI","GENRE_ZHIYE"] | 历史背景中的经营 | 核对已定历史背景与作品采用的经营方向。
15461 | HYBRID_LISHI_YANQING | ["GENRE_LISHI","GENRE_YANQING"] | 历史背景中的爱情 | 核对已定历史背景与核心情感关系的项目范围。
15493 | HYBRID_KEHUAN_MOSHI | ["GENRE_KEHUAN","GENRE_MOSHI"] | 科幻背景中的末世 | 核对科幻背景与已定末世条件各自的作用。
15525 | HYBRID_KEHUAN_XUANYI | ["GENRE_KEHUAN","GENRE_XUANYI"] | 科幻背景中的悬疑 | 核对科幻设定与作者已定的悬疑任务，并区分前处同 ID 详表。
15557 | HYBRID_KEHUAN_TUILI | ["GENRE_KEHUAN","GENRE_TUILI"] | 科幻背景中的推理 | 核对已设科技条件与作者确定的推理方向。
15589 | HYBRID_KEHUAN_KONGBU | ["GENRE_KEHUAN","GENRE_KONGBU"] | 科幻背景中的恐怖 | 核对科幻设定与作者要求的恐怖范围。
15621 | HYBRID_KEHUAN_YOUXI | ["GENRE_KEHUAN","GENRE_YOUXI"] | 科幻背景中的游戏 | 核对已定科幻背景与项目中的游戏设定。
15653 | HYBRID_YOUXI_YIJIE | ["GENRE_YOUXI","GENRE_QIHUAN"] | 游戏世界与异世界融合 | 核对已确认的游戏世界和异世界各自的作用。
15685 | HYBRID_YOUXI_JINGJI | ["GENRE_YOUXI","GENRE_DIANJING"] | 游戏与电竞融合 | 核对项目中的游戏和已采用的电竞题材分别承担什么。
15717 | HYBRID_YOUXI_MOSHI | ["GENRE_YOUXI","GENRE_MOSHI"] | 游戏与末世融合 | 核对作品中的游戏设定与已定末世背景。
15749 | HYBRID_YOUXI_WUXIAN | ["GENRE_YOUXI","GENRE_ZHUTIAN"] | 游戏与无限流融合 | 核对以游戏为先列组成的原条，依作者需求明确无限流作用。
15781 | HYBRID_XUANYI_LINGYI | ["GENRE_XUANYI","GENRE_LINGYI"] | 悬疑与灵异融合 | 核对已定悬疑任务与作者确认的灵异要素。
15813 | HYBRID_XUANYI_LISHI | ["GENRE_XUANYI","GENRE_LISHI"] | 悬疑与历史融合 | 核对作者已定的历史范围与悬疑任务。
15845 | HYBRID_XUANYI_XINGZHEN | ["GENRE_XUANYI","GENRE_TUILI"] | 悬疑与刑侦融合 | 核对已定悬疑任务与作者确定的刑侦范围，保留原推理组成。
15877 | HYBRID_LINGYI_XINGZHEN | ["GENRE_LINGYI","GENRE_TUILI"] | 灵异与刑侦融合 | 核对已定灵异现象与作者确定的刑侦方向，保留原推理组成。
15909 | HYBRID_LINGYI_DAOMU | ["GENRE_LINGYI","GENRE_XUANYI"] | 灵异与盗墓融合 | 核对作品已定的灵异和盗墓题材，按作者范围确认悬疑组成。
15941 | HYBRID_LINGYI_GUITAN | ["GENRE_LINGYI","GENRE_KONGBU"] | 灵异与规则怪谈融合 | 核对作品已定的规则怪谈范围和作者是否采用恐怖组成。
15973 | HYBRID_KONGBU_WUXIAN | ["GENRE_KONGBU","GENRE_ZHUTIAN"] | 恐怖与无限流融合 | 核对以恐怖为先列组成的条目及作者确认的无限流作用。
16005 | HYBRID_YANQING_XUANYI | ["GENRE_YANQING","GENRE_XUANYI"] | 言情与悬疑融合 | 核对作者已定的情感关系和作品采用的悬疑任务。
16037 | HYBRID_YANQING_GONGDOU | ["GENRE_YANQING","GENRE_GONGTING"] | 言情与宫斗融合 | 核对作者已定的情感关系与项目采用的宫斗范围。
16069 | HYBRID_YANQING_QUANMOU | ["GENRE_YANQING","GENRE_GONGTING"] | 言情与权谋融合 | 核对作者已定的情感关系与项目采用的权谋范围。
16101 | HYBRID_YANQING_MOSHI | ["GENRE_YANQING","GENRE_MOSHI"] | 言情与末世融合 | 核对情感关系与已定末世条件各自的作用。
16133 | HYBRID_YANQING_XUANHUAN | ["GENRE_YANQING","GENRE_XUANHUAN"] | 言情与玄幻融合 | 核对核心情感关系与作品采用的玄幻设定。
16165 | HYBRID_YANQING_XIANXIA | ["GENRE_YANQING","GENRE_XIANXIA"] | 言情与仙侠融合 | 核对以言情为先列组成的原条及作者确认的仙侠作用。
16197 | HYBRID_XIANSHI_XUANYI | ["GENRE_XIANSHI","GENRE_XUANYI"] | 现实与悬疑融合 | 核对已定现实议题及作者采用的悬疑方向。
16229 | HYBRID_XIANSHI_ZHIYE | ["GENRE_XIANSHI","GENRE_ZHIYE"] | 现实与职业融合 | 核对作品的现实题材与作者采用的职业发展范围。
16261 | HYBRID_XIANSHI_JIATING | ["GENRE_XIANSHI","GENRE_JIATING"] | 现实与家庭融合 | 核对已定现实议题与作品中的家庭关系范围。
16293 | HYBRID_QINGXIAOSHUO_YISHIJIE | ["GENRE_QINGXIAOSHUO","GENRE_QIHUAN"] | 轻小说与异世界融合 | 核对作者选定的轻小说身份与作品中的异世界设定。
16325 | HYBRID_QINGXIAOSHUO_XIAOYUAN | ["GENRE_QINGXIAOSHUO","GENRE_QINGCHUN"] | 轻小说与校园融合 | 核对作者选定的轻小说身份及已定校园背景。
16357 | HYBRID_TONGREN_ZONGMAN | ["GENRE_TONGREN","GENRE_ERCIYUAN"] | 同人与综漫融合 | 核对作者确认的原作与综漫范围，保留表内二次元组成。
16389 | HYBRID_TONGREN_WUXIAN | ["GENRE_TONGREN","GENRE_ZHUTIAN"] | 同人与无限流融合 | 核对作者指定的原作品与项目已采用的无限流方向。
16421 | HYBRID_WUXIAN_ZHUTIAN | ["GENRE_ZHUTIAN","GENRE_ZHUTIAN"] | 无限与诸天融合 | 核对作者是否明确两者的实际分工，记录原组成重复。
16453 | HYBRID_WUXIAN_KONGBU | ["GENRE_ZHUTIAN","GENRE_KONGBU"] | 无限与恐怖融合 | 核对以诸天无限为先列组成的原条及作者明确的恐怖范围。
16485 | HYBRID_WUXIAN_YOUXI | ["GENRE_ZHUTIAN","GENRE_YOUXI"] | 无限与游戏融合 | 核对以诸天无限为先列组成的原条及项目已采用的游戏设定。
【本步用法】
从已经确认的类型与作者明确的组合目标核对本表。以条目 ID、组成与融合原义辨认实际采用项。用 adaptations.type_refs 引用已经选择的项目类型，在 parameters 记录本项目中各组成承担的作用，在 limits 或 boundaries 记录已知限制和待确认事项。只有名称或组成相近时，依据作者已经确认的范围记录，仍缺的前提留待确认。
表内的 compatible_mechanisms、compatible_structures、compatible_styles、possible_conflicts、source_refs 均为空。适配时只根据实际项目材料和作者确认的要求确定具体风格、机制、结构与冲突处理；这些条目作为组合核对依据，采用状态依现有资料裁定和作者确认。
「玄幻与科幻融合」提供的原义是修炼体系与科技设定并存，用于核对项目明确采用的两部分如何分工。「都市背景中的职场」「都市背景中的商业」组成相同，按分别采用的职场或商业方向核对。
「历史背景中的穿越」「历史背景中的重生」同用历史与诸天无限；早处《混合类型.json》的 HYBRID_CHUANYUE_LISHI 另列 GENRE_CHUANYUE 与 GENRE_LISHI。核对时保留原 ID 和对象，是否使用穿越或重生机制以作者确定的方案为准。
HYBRID_KEHUAN_XUANYI 和 HYBRID_DUSHI_XUANYI 同时见于《混合类型.json》。这里各自只给总表的组成和融合说明，采用详细权重、风格或冲突处理时，依据已有详细条目及作者独立确认的要求。
「无限与诸天融合」两项都是 GENRE_ZHUTIAN，按作者已确认范围记录相同组成，仍缺的独立对象或两者分工写入 boundaries。"""
