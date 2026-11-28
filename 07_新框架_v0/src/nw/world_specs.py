"""Executable World Rule-Engine Specification Library (`world_spec.json`).

Defines HOW world rules operate, constrain actions, conserve costs, run behind the scenes,
and enter prose semi-transparently (NEVER pre-baking fixed cultivation realms or lore encyclopedias).
Aligned 1-to-1 with Track 1 (`genre_world_rules`), Step 03 (`world_design`), Step 08 (`action_design`),
and Step 16 (`review`).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.craft_specs_base import (
    PRIORITY_ARBITRATION_NOTE,
    finalize_spec_payload,
    is_fingerprint_compatible,
    knob_option_map,
    load_spec_file,
    normalize_spec_knobs,
    rank_bases_for_genres,
    save_spec_file,
    truncate_lines_to_budget,
)
from nw.store import Store
from nw.studio.catalog import canonical_types

WORLD_SPEC_FILENAME = 'world_spec.json'

WORLD_FUNCTION_LABELS: dict[str, str] = {
    'rule_limit': '硬规则与限制边界',
    'resource_cost': '核心资源与使用代价',
    'opening_reveal': '开篇半透明渗入',
}

WORLD_KNOBS: dict[str, dict[str, Any]] = {
    'rule_hardness': {
        'label': '规则硬核度与可推导性',
        'multi': False,
        'options': [
            {
                'id': 'hard_conserved',
                'label': '硬规则精确守恒（可推演）',
                'directive': '所有规则、能量/资源消耗与制度门槛写明硬边界与守恒逻辑，主角靠在规则内算计与取舍破局。',
            },
            {
                'id': 'soft_atmospheric',
                'label': '软规则氛围留白（重质感）',
                'directive': '规则保持神秘感与克制边界，不给读者做数学公式讲解，但绝不违背前文已亮出的硬限制。',
            },
            {
                'id': 'discovery_unfolding',
                'label': '规则未知逐步揭晓（探索向）',
                'directive': '早期只暴露表层现象与直接惩罚，真实底层机制随主角踩坑试错分阶段揭开，未揭部分写入 unknowns。',
            },
        ],
    },
    'cost_severity': {
        'label': '能力/资源使用代价烈度',
        'multi': False,
        'options': [
            {
                'id': 'light_cost',
                'label': '轻代价（保爽感，有门槛即可）',
                'directive': '超额动用或违规需付出明确资源、冷却或暴露风险，但不轻易造成永久残废拖慢推进。',
            },
            {
                'id': 'medium_tradeoff',
                'label': '中代价（真实权衡取舍）',
                'directive': '每次越阶出手、违规取利或破例动用道具都必伴随可感知的损耗、人情债或制度追责，逼角色做取舍。',
            },
            {
                'id': 'high_irreversible',
                'label': '高代价（不可逆惨烈后果）',
                'directive': '动用禁忌力量、触碰世界禁区或失败必留下不可逆伤痕、污染、寿元折损或秩序崩塌。',
            },
        ],
    },
    'exposition_pace': {
        'label': '世界设定渗入正文节奏',
        'multi': False,
        'options': [
            {
                'id': 'action_only',
                'label': '纯行动带出（零设定讲解）',
                'directive': '严禁专门辟段解释世界观；全部规则只通过价格、禁令、处罚现场与人物习惯自然显露。',
            },
            {
                'id': 'micro_fragments',
                'label': '碎片微提示（顺手一句点清）',
                'directive': '仅在规则即将直接决定胜负生死前，借人物眼中所见或一句顺口行话点清必要常识，不超过两句。',
            },
            {
                'id': 'anchored_brief',
                'label': '关键处短锚点点明',
                'directive': '新舞台或新阶层初现时允许用 3–4 句具象制度/地标画面立住坐标，绝不堆砌编年史和百科全书。',
            },
        ],
    },
    'world_bans': {
        'label': '世界设计防崩坏禁忌（可多选）',
        'multi': True,
        'options': [
            {
                'id': 'no_lore_dump',
                'label': '禁开篇设定说明书',
                'directive': '严禁在开篇或单张世界卡里堆砌与当前故事无关的创世编年史、庞大地理名录或长篇体系讲解。',
            },
            {
                'id': 'no_power_inflation',
                'label': '禁战力与资源通货膨胀',
                'directive': '严禁前卷极度稀缺的资源或高阶门槛，在后卷突然贬值满大街都是而无制度/阶层切换依据。',
            },
            {
                'id': 'no_omnipotent_item',
                'label': '禁万能道具与无限制外挂',
                'directive': '任何关键道具、武器、制度权限或金手指都必须写清“不能做什么”与“反功能/反噬条件”。',
            },
            {
                'id': 'no_genre_pollution',
                'label': '禁跨题材体系污染',
                'directive': '现实/都市/悬疑/历史等常规题材严禁无故渗入灵气、血脉、奇幻种族；古风严禁渗入现代网游术语。',
            },
            {
                'id': 'no_free_breakthrough',
                'label': '禁无代价破格升级',
                'directive': '突破瓶颈、越级反制或打破规则必须具备清晰前置条件与不可豁免代价。',
            },
        ],
    },
}

_WORLD_KNOB_MAP = knob_option_map(WORLD_KNOBS)

WORLD_BASES: tuple[dict[str, Any], ...] = (
    {
        'id': 'WORLD_REALISTIC_INSTITUTION',
        'name': '现实制度与资源稀缺底座',
        'tagline': '钱、权、法、程序与时间构成真实硬阻力，严禁超自然与悬浮套路',
        'recommended_genres': (
            'GENRE_DUSHI', 'GENRE_XIANSHI', 'GENRE_ZHIYE', 'GENRE_SHANGZHAN',
            'GENRE_XUANYI', 'GENRE_TUILI', 'GENRE_QINGCHUN', 'GENRE_TIYU',
        ),
        'incompatible_genres': ('GENRE_XIANXIA', 'GENRE_XUANHUAN', 'GENRE_QIHUAN'),
        'default_knobs': {
            'rule_hardness': 'hard_conserved',
            'cost_severity': 'medium_tradeoff',
            'exposition_pace': 'action_only',
            'world_bans': ['no_lore_dump', 'no_omnipotent_item', 'no_genre_pollution'],
        },
        'dimensions': {
            'premise_law': '遵循当代物理常识、法律程序、行业流程与社会阶层规矩；任何越界行动都必须承担可核查的现实风险。',
            'scarcity_cost': '核心稀缺资源落到具体现金流、时间窗口、合法资质、人脉信用与有效证据，花一分少一分。',
            'institution_gate': '执法机构、审批流程、考核制度、合同条款与舆论边界构成主角必须正面应对或巧妙周旋的真实门槛。',
            'background_clock': '即便主角停下动作，截止日期、利率违约、市场波动、对手流程与司法时效仍在按真实日历倒数。',
            'exposition_policy': '行业与制度规则全部通过具体单据、术语、流程卡壳自然显露，不写行业科普大段说明。',
            'genre_firewall': '严禁未经作者显式叠加副类型就引入灵气、系统面板、超能力或玄幻血脉。',
        },
        'anti_drift_redlines': [
            '严禁在现实/职场/悬疑世界里出现违背常识的“一句话让全城公司破产”或无视法律程序的悬浮霸总操作。',
            '严禁把关键物证、资金或专业技能写成主角随手掏出、毫无来路与成本的万能道具。',
            '严禁混入修仙/奇幻/网游属性面板等跨题材污染元素。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'rule_limit',
                'label': '现实制度硬边界世界卡',
                'bad_ai': '规则：主角所在的城市商业发达，豪门林立，有钱就能为所欲为，反派家族一手遮天。',
                'target_craft': '规则：本市国资工程招投标须过三道公示与资金监管账户；limits：民企即便手握评委私交，也无法绕开垫资保证金与审计追责，违规串标一旦留痕将直接触发银行抽贷。',
                'why': '写清真实制度杠杆与互相制约的痛点，既限制主角也给主角留下可破局的合法缝隙。',
            },
            {
                'target_function': 'resource_cost',
                'label': '现实资源稀缺与代价',
                'bad_ai': '规则：主角缺钱创业，但只要写出好方案就能轻松拿到投资。',
                'target_craft': '规则：小微研发团队启动资金依赖对赌投资或账期回款；limits：接大客户订单需先垫付 90 天原料款，现金流断档两周即触发设备抵押违约。',
                'why': '把“缺钱”落到具体账期与违约红线，自然长出步步惊心的现实剧情。',
            },
            {
                'target_function': 'opening_reveal',
                'label': '现实世界半透明切入',
                'bad_ai': '开篇用六百字介绍该市经济结构、五大财团历史和主角行业十年发展史。',
                'target_craft': '只冻结前 3 章直接触发的“退租违约条款”与“行业黑名单规则”，其余商圈格局留白在 unknowns 中随调查逐步浮现。',
                'why': '只建当下真正起作用的规则卡，不造无用背景百科。',
            },
        ],
    },
    {
        'id': 'WORLD_TRANSCENDENT_COST',
        'name': '超凡代价与阶层法则底座',
        'tagline': '力量必有来源、损耗与突破反噬，资源垄断与宗门/阶层规则驱动冲突',
        'recommended_genres': ('GENRE_XIANXIA', 'GENRE_XUANHUAN', 'GENRE_GAOWU', 'GENRE_WUXIA'),
        'incompatible_genres': ('GENRE_DUSHI', 'GENRE_XIANSHI', 'GENRE_TUILI'),
        'default_knobs': {
            'rule_hardness': 'hard_conserved',
            'cost_severity': 'medium_tradeoff',
            'exposition_pace': 'micro_fragments',
            'world_bans': ['no_lore_dump', 'no_power_inflation', 'no_omnipotent_item', 'no_free_breakthrough'],
        },
        'dimensions': {
            'premise_law': '超凡力量遵循明确来源、媒介承载与能量三态转化边界；等阶差距体现在质变与手段上限，而非空洞数值翻倍。',
            'scarcity_cost': '丹药/灵脉/秘法/兵刃皆有产出上限、炼制损耗与服用抗性或反噬，高阶资源被上层势力结构性垄断。',
            'institution_gate': '宗门戒律、世家血统、朝廷律令、因果誓约或天劫压制构成硬门槛，强者之间亦有彼此忌惮的秩序成本。',
            'background_clock': '灵潮枯荣、宗门大比、秘境周期、兽潮/边患与旧债清算按独立时间表运转，不等主角准备好才发生。',
            'exposition_policy': '只提前确立当前卷用得到的 2–3 个阶层与核心禁忌，高阶秘辛列为 unknowns，随境界提升逐步掀开。',
            'genre_firewall': '保持古风/东方超凡物质肌理与修士寿元常识，严禁混入现代网游术语或现代凡人算账习惯。',
        },
        'anti_drift_redlines': [
            '严禁开篇一次抛出十几个大境界完整清单和万年上古神话编年史。',
            '严禁越阶反杀无代价或把法宝/功法写成无消耗、无冷却、包治百病的万能神器。',
            '严禁前期贵若性命的稀缺资源，到中后期毫无交代地突然烂大街。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'rule_limit',
                'label': '超凡边界与突破代价',
                'bad_ai': '规则：修炼分为九大境界，灵气越多实力越强，主角有混沌神体可以越三级秒杀。',
                'target_craft': '规则：真气外放须借经脉承载，跨阶强催会灼裂气海；limits：低阶修士借秘宝越阶出手最多维持十息，且必留下三日真气枯竭与灵气残痕，易被宗门执法司循迹锁定。',
                'why': '把超凡手段与真实承受力、暴露风险绑死，每场斗法都有悬念与代价。',
            },
            {
                'target_function': 'resource_cost',
                'label': '修行资源垄断与转化损耗',
                'bad_ai': '规则：下品灵石用来修炼，主角机缘巧合捡到一整条灵脉从此不缺钱。',
                'target_craft': '规则：杂灵气入体仅能转化三成，净灵丹由内堂按贡献额度配发；limits：私售丹药视同叛门，外门修士欲攒够筑基丹须在险地采药三年或拿寿元换黑市残丹。',
                'why': '资源稀缺直接逼出阶层压迫与人物冒险动机。',
            },
            {
                'target_function': 'opening_reveal',
                'label': '局部阶层先立，高阶留白',
                'bad_ai': '开篇完整列出凡界、灵界、仙界、神界四大界域全部势力分布。',
                'target_craft': '全书初期世界卡只锚定“外门杂役—内门执事—峰主”三级可见秩序及灵石税规，上界与古老秘闻记入 unknowns 待后期揭晓。',
                'why': '保留探索空间，同时防止前卷设定过重压垮节奏。',
            },
        ],
    },
    {
        'id': 'WORLD_RULE_ANOMALY',
        'name': '规则诡异与认知边界底座',
        'tagline': '日常秩序中的致命异常规则 + 不可逆代价 + 信息残缺制造压迫感',
        'recommended_genres': ('GENRE_LINGYI', 'GENRE_KONGBU', 'GENRE_JINGSONG', 'GENRE_MOSHI'),
        'incompatible_genres': ('GENRE_GAOXIAO', 'GENRE_YANQING', 'GENRE_QINGCHUN'),
        'default_knobs': {
            'rule_hardness': 'discovery_unfolding',
            'cost_severity': 'high_irreversible',
            'exposition_pace': 'action_only',
            'world_bans': ['no_lore_dump', 'no_omnipotent_item', 'no_free_breakthrough'],
        },
        'dimensions': {
            'premise_law': '诡异/污染/异变严格服从冷酷而古怪的触发条件与豁免逻辑（不讲人类善恶，只认规则满足与否）。',
            'scarcity_cost': '每一次试探规则、动用诡物或涉险求生，都以理智、记忆、身体异化、安全时间或同伴信任为不可逆筹码。',
            'institution_gate': '封闭空间、封锁令、生存据点配给制或收容条例限制主角行动自由，外部世界无法随意求援。',
            'background_clock': '污染扩散、天黑倒计时、异常升级与据点物资消耗持续恶化，拖延本身就是最致命的选择。',
            'exposition_policy': '严禁提前向读者公布完整怪物百科与规则全集；只通过前人残稿、目击惨状与试错代价一点点拼出真相。',
            'genre_firewall': '守住冷峻克制的恐怖/末世质感，严禁把诡异异象写成热血喊口号的对波大战。',
        },
        'anti_drift_redlines': [
            '严禁设定全知全能的克制神物或让主角轻松免疫核心诡异代价。',
            '严禁在前期就把异常现象的终极起源和全部弱点用旁白一次讲完（彻底毁掉未知恐惧）。',
            '严禁规则前后朝令夕改，主角利用过的规则漏洞必须严格自洽。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'rule_limit',
                'label': '冷酷自洽的异常规则卡',
                'bad_ai': '规则：夜里有恐怖怪物出没，实力极强，见人就杀，只有主角的护身符能挡住。',
                'target_craft': '规则：子夜敲钟后凡回应呼名者将被置换影子；limits：规则仅在室内门窗闭锁且不答话时可规避，借旧铜镜反弹一次需承受三日失明且镜面裂痕不可修复。',
                'why': '既有致命威胁又有精确可利用的缝隙与代价，悬疑与破题空间同时拉满。',
            },
            {
                'target_function': 'resource_cost',
                'label': '不可逆生存与理智消耗',
                'bad_ai': '规则：使用诡异道具会有点头晕，休息一晚就恢复如初。',
                'target_craft': '规则：每次借用收容物窥探死角会永久擦除使用者一段近七日记忆；limits：连续使用三次将导致无法辨认熟悉面孔，迫使角色靠手写笔记防迷失。',
                'why': '代价真实改变人物后续认知和行动方式，绝非口头说说。',
            },
            {
                'target_function': 'opening_reveal',
                'label': '未知留白纪律',
                'bad_ai': '世界卡直接写明“幕后大Boss是三百年前沉睡的古神，弱点是纯银”。',
                'target_craft': '公开世界卡仅记“停电后走廊镜面延迟两秒映影”的观测规律；幕后成因与彻底终结条件全部锁进 unknowns 等待实证。',
                'why': '保护恐怖与悬疑的核心资产——未知边界。',
            },
        ],
    },
    {
        'id': 'WORLD_GEOPOLITICAL_POWER',
        'name': '地缘势力与制度博弈底座',
        'tagline': '粮草、税赋、宗法、兵权与地理咽喉构成的硬核历史/权谋生态',
        'recommended_genres': ('GENRE_LISHI', 'GENRE_QUANMOU', 'GENRE_JUNSHI'),
        'incompatible_genres': ('GENRE_ERCIYUAN', 'GENRE_YOUXI', 'GENRE_SAIBO'),
        'default_knobs': {
            'rule_hardness': 'hard_conserved',
            'cost_severity': 'medium_tradeoff',
            'exposition_pace': 'anchored_brief',
            'world_bans': ['no_lore_dump', 'no_omnipotent_item', 'no_genre_pollution'],
        },
        'dimensions': {
            'premise_law': '权力运行受制于交通通信耗时、财政税源、官僚执行损耗与宗法礼制，绝非一道命令瞬间传遍天下。',
            'scarcity_cost': '钱粮、兵源、马匹、盐铁专卖、官位名额与政治信用都是零和博弈，多给一派必少给另一派。',
            'institution_gate': '三省六部/军机/地方藩镇/士族乡绅互相制衡，任何改革或军事动作必触发既得利益集团反噬。',
            'background_clock': '旱涝灾荒、边疆换季、漕运冰封、换届/大选/皇嗣更迭按历史时钟持续发酵。',
            'exposition_policy': '只勾勒当前冲突涉及的官制、地缘节点与两三股直接对峙势力，不抄历史教科书。',
            'genre_firewall': '严禁混入现代互联网话术、违背时代生产力极限的瞬时工业奇迹或玄幻飞升元素。',
        },
        'anti_drift_redlines': [
            '严禁无视后勤粮草与通信距离，写出“主角一声令下三日横扫十州”。',
            '严禁把复杂朝堂/战局简化为“好人忠臣 vs 纯坏蠢蛋奸臣”的二元脸谱。',
            '严禁开篇丢出完整朝代世系表和几十个一时用不上的地名官职。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'rule_limit',
                'label': '制度制衡与后勤约束',
                'bad_ai': '规则：皇帝拥有绝对权力，想杀谁就杀谁，想改税法立刻就能推行全国。',
                'target_craft': '规则：州县田赋造册握在地方书吏与乡绅之手，中央清丈须经御史复核；limits：单靠敕令强推清丈极易引发地方虚报灾情与税银滞缴，必须借漕运或兵权交换筹码。',
                'why': '写出真实历史运行的摩擦力，权谋才站得住脚。',
            },
            {
                'target_function': 'resource_cost',
                'label': '零和财政与军备代价',
                'bad_ai': '规则：主角练出一支无敌新军，装备精良战无不胜。',
                'target_craft': '规则：新军火器与厚甲每人年耗银三十两，为旧营三倍；limits：缺盐铁专卖分成撑不过两季，裁撤旧营又将直接激起边镇哗变。',
                'why': '每一项优势背后都有硬账本，逼出精彩的政治交换。',
            },
            {
                'target_function': 'opening_reveal',
                'label': '地缘节点聚焦',
                'bad_ai': '开篇详述全国十三省地理、民族、风俗与三百年历代帝王功过。',
                'target_craft': '仅立“西北两镇军饷欠发 + 江南盐运换引”两条眼下咬死的制度与地理枢纽，其余外患记入 unknowns。',
                'why': '聚焦当下棋盘，信息精干锐利。',
            },
        ],
    },
    {
        'id': 'WORLD_SPECULATIVE_ECOLOGY',
        'name': '宏阔异域与半透明渗入底座',
        'tagline': '强辨识异域物理/技术/生态自洽，靠日常物质细节半透明建立真实感',
        'recommended_genres': ('GENRE_QIHUAN', 'GENRE_KEHUAN', 'GENRE_SAIBO', 'GENRE_WEILAI'),
        'incompatible_genres': ('GENRE_XIANSHI', 'GENRE_LISHI'),
        'default_knobs': {
            'rule_hardness': 'hard_conserved',
            'cost_severity': 'medium_tradeoff',
            'exposition_pace': 'micro_fragments',
            'world_bans': ['no_lore_dump', 'no_power_inflation', 'no_omnipotent_item'],
        },
        'dimensions': {
            'premise_law': '确立 1–2 条彻底改写人类生活方式的核心异域/科技前提（如能源枯竭、义体排异、魔潮潮汐、星际光速上限），所有社会生态由其推导而出。',
            'scarcity_cost': '算力、氧气、高纯燃料、抑制剂、魔石或生态配额构成底层硬通货，科技/奇幻便利必伴随维护与阶层鸿沟。',
            'institution_gate': '巨企专利、教会仪轨、轨道安防、城邦行会或物理法则边界约束角色活动半径。',
            'background_clock': '星轨窗口、生态熵增、技术迭代、旧城衰败与阵营冷战在后台持续改写空间环境。',
            'exposition_policy': '坚持 70% 人类可直觉理解的常态 + 30% 高辨识异域细节；借日常衣食住行半透明渗入，绝不写世界观导游词。',
            'genre_firewall': '严禁把奇幻/科幻/赛博写成仅换个名词外壳的现代都市或修仙换皮。',
        },
        'anti_drift_redlines': [
            '严禁开篇连写五百字“大灾变纪元/七大教会/星际联邦成立史”说明书。',
            '严禁科技或魔法解决一切生活与剧情阻力（如随手瞬移/一键黑入任意核心主机）。',
            '严禁异域设定与普通市民日常生活脱节（如高科技星际社会却还像中世纪一样毫无信息记录）。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'rule_limit',
                'label': '单一核心前提推演社会生态',
                'bad_ai': '规则：这是赛博朋克未来世界，到处都是霓虹灯、义体和邪恶大公司。',
                'target_craft': '规则：神经义体需每 14 天注射巨企加密排异抑制剂，离线逾期 48 小时将触发神经灼痛锁死；limits：黑市仿制药虽便宜七成，但会永久侵蚀短期记忆并留下可追踪生物荧光。',
                'why': '一条核心生理/商业规则直接生成底层压迫、黑市生态与主角困境。',
            },
            {
                'target_function': 'resource_cost',
                'label': '异域技术维护与物理限制',
                'bad_ai': '规则：星舰可以随时曲率跳跃到任何星系，能源无限。',
                'target_craft': '规则：跃迁引擎单次启动须消耗主舱四成氦三燃料并冷却 72 小时；limits：航线偏离信标超过半光秒将无法校准重力井，强行盲跳有高概率撕裂船壳。',
                'why': '精确物理限制直接把星际逃亡写成惊心动魄的战术抉择。',
            },
            {
                'target_function': 'opening_reveal',
                'label': '日常物质肌理半透明渗入',
                'bad_ai': '先列出五大种族、八大魔法元素和千年战争史再进故事。',
                'target_craft': '首张世界卡只写清主角所居下城区的“鲸油灯配给、雾夜巡检规矩与旧钟楼禁忌”，宏大世界真相放进 unknowns。',
                'why': '读者通过眼前可触碰的小规则瞬间信服整个大世界。',
            },
        ],
    },
    {
        'id': 'WORLD_SYSTEM_SANDBOX',
        'name': '系统/副本/沙盒防崩坏底座',
        'tagline': '规则透明、奖惩对等、数值有天花板，不让金手指一键消灭剧情张力',
        'recommended_genres': ('GENRE_YOUXI', 'GENRE_DIANJING', 'GENRE_ZHUTIAN', 'GENRE_TONGREN', 'GENRE_ERCIYUAN'),
        'incompatible_genres': ('GENRE_XIANSHI', 'GENRE_LISHI'),
        'default_knobs': {
            'rule_hardness': 'hard_conserved',
            'cost_severity': 'light_cost',
            'exposition_pace': 'micro_fragments',
            'world_bans': ['no_lore_dump', 'no_power_inflation', 'no_omnipotent_item', 'no_free_breakthrough'],
        },
        'dimensions': {
            'premise_law': '系统/游戏/诸天规则必须有清晰触发条件、适用边界与不可篡改底层法则，主角靠机制理解与组合策略取胜。',
            'scarcity_cost': '积分、冷却、槽位上限、入场资格与任务失败惩罚构成硬约束，奖励越高风险或限制越明确。',
            'institution_gate': '赛季规则、阵营声望、防作弊判定、主神/平台条例或现实同步后果制约主角不能为所欲为。',
            'background_clock': '版本更新、排行榜竞争、倒计时征召、其他玩家/势力进度在后台同步滚动。',
            'exposition_policy': '只在首次触发某项机制时简洁亮出该条目，绝不一次性倾倒几十项无关子模块菜单。',
            'genre_firewall': '严禁系统变成有求必应、无条件送神装的“许愿机”，保持博弈感与规则趣味。',
        },
        'anti_drift_redlines': [
            '严禁系统或金手指没有任何限制条件、冷却或代价，一键秒杀所有危机。',
            '严禁前期精妙的数值与槽位体系，写到中期变成“直接加十万战力”的崩坏膨胀。',
            '严禁在世界卡或正文中大段复制无意义的空白属性菜单。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'rule_limit',
                'label': '防崩坏金手指/系统边界',
                'bad_ai': '规则：主角获得万能签到系统，每天签到就送顶级神装和满级技能。',
                'target_craft': '规则：系统仅在主角亲身经历高风险信息差事件后结算“推演点数”，且同时只能装配 3 个词条槽位；limits：替换旧词条将永久销毁原词条，超频使用会强制进入 24 小时冷却并暴露异常波动。',
                'why': '槽位取舍与风险挂钩，让系统本身成为精彩的策略博弈引擎。',
            },
            {
                'target_function': 'resource_cost',
                'label': '数值天花板与机制克制',
                'bad_ai': '规则：等级越高伤害越高，差十级就完全破不了防。',
                'target_craft': '规则：属性提升遵循边际递减，高阶优势在于机制权限与信息视野；limits：特定环境与克制词条可让低阶玩家完成局部反杀，但容错率极低。',
                'why': '避免纯数值碾压，保证长篇后半段依然靠战术和操作好看。',
            },
            {
                'target_function': 'opening_reveal',
                'label': '按需解锁机制条目',
                'bad_ai': '开篇把商城、抽奖、跨界、合成、宠物五大系统全部写进第1张世界卡。',
                'target_craft': '初期仅激活“任务判定 + 词条槽位”两项眼下必用规则，高阶权限标注为未解锁 unknowns。',
                'why': '清晰聚焦，便于前期快速起势和后期持续给新鲜感。',
            },
        ],
    },
    {
        'id': 'WORLD_HYBRID_BALANCED',
        'name': '多题材融合稳健底座',
        'tagline': '主类型底层逻辑压阵、副类型机制限定边界，确保规则自洽与可读性',
        'recommended_genres': ('GENRE_ZHONGDIAN', 'GENRE_QINGXIAOSHUO', 'GENRE_GAOXIAO', 'GENRE_YANQING', 'GENRE_CHENGZHANG'),
        'incompatible_genres': (),
        'default_knobs': {
            'rule_hardness': 'hard_conserved',
            'cost_severity': 'medium_tradeoff',
            'exposition_pace': 'micro_fragments',
            'world_bans': ['no_lore_dump', 'no_omnipotent_item', 'no_genre_pollution'],
        },
        'dimensions': {
            'premise_law': '以主类型的现实或幻想底座为不可动摇的根基，副类型要素作为局部特例明确写入适用范围，避免两套规则打架。',
            'scarcity_cost': '明确本书最核心的 2–3 种稀缺资源（钱/粮/时间/信任/特殊媒介），让所有人物行动绕着真实成本转。',
            'institution_gate': '确立故事发生的社区、行业、宗门或城邦的日常规矩与违规后果，为冲突提供稳定舞台。',
            'background_clock': '设定至少 1 条不以主角意志为转移的外部周期（季节、考核、租期、局势变化），推着故事往前走。',
            'exposition_policy': '只写当前卷真正参与冲突的规则，借人物生活和阻挠自然显露，禁设定说明书。',
            'genre_firewall': '严格守住立项选定的主副题材边界，绝不漂移到未勾选的体系中去。',
        },
        'anti_drift_redlines': [
            '严禁世界卡只写空泛背景氛围而不写可核查的限制（limits）与代价。',
            '严禁多题材融合时随意违背自己立下的核心前提。',
            '严禁提前在世界卡里写死具体分章剧情或单个人物情感结局。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'rule_limit',
                'label': '融合题材清晰边界卡',
                'bad_ai': '规则：这是一个轻松又带有神秘色彩的城市，主角既有日常工作又有神秘能力。',
                'target_craft': '规则：城市表面完全按现代市政与法律运转，仅极少数古董修复师能感知旧物残响；limits：能力无法直接改写物理事实或违抗法律，且每次深度共鸣都会让修复师短暂染上原主情绪惯性。',
                'why': '主底座写实、副特例精准有界，两层逻辑丝滑兼容。',
            },
            {
                'target_function': 'resource_cost',
                'label': '轻重结合的日常筹码',
                'bad_ai': '规则：大家生活都很富足轻松，没什么生存压力。',
                'target_craft': '规则：小店每月房租与原料进货雷打不动，口碑靠熟客口口相传；limits：接高价急单可解燃眉之急，但一旦砸招牌将丢失整条街的长期客源。',
                'why': '即便日常轻松题材，也有让人共情的真实小算盘与得失。',
            },
            {
                'target_function': 'opening_reveal',
                'label': '精炼开局舞台卡',
                'bad_ai': '世界卡堆砌几十个与前十章无关的远方国度与历史传说。',
                'target_craft': '聚焦眼前一条街/一座镇/一个部门的 3 条运作铁律，外部大背景留白在 unknowns。',
                'why': '轻盈好读，方便模型精准引用而不跑偏。',
            },
        ],
    },
)

WORLD_BASE_MAP: dict[str, dict[str, Any]] = {b['id']: b for b in WORLD_BASES}

WORLD_MECHANISM_EXECUTION_HINTS: dict[str, str] = {
    'PLOT_MECHANISM_SYSTEM': '系统世界边界：明确系统的任务触发条件、奖惩对等性、冷却/槽位限制与不可干预禁区。',
    'PLOT_MECHANISM_PARALLEL': '平行世界边界：明确两界差异点、通行媒介、时间流速比与物质带入限制。',
    'PLOT_MECHANISM_VR': '虚拟现实边界：写清虚拟痛感/时间倍率、登出限制及虚拟收益向现实传导的法律与物理后果。',
    'PLOT_MECHANISM_CYBERPUNK': '赛博世界边界：落实“高科技垄断 + 低生活成本压迫”，写清义体排异、数据追踪与巨企法外权限。',
    'PLOT_MECHANISM_UTOPIA': '乌托邦表里边界：写清表面完美秩序依赖的隐蔽成本与被排斥者的生存裂缝。',
    'PLOT_MECHANISM_MULTIVERSE': '多元宇宙边界：限定跨宇宙坐标锚点、能量法则兼容度与过度穿梭的因果反噬。',
    'PLOT_MECHANISM_GAMIFIED': '游戏化世界边界：明确谁受规则管辖、数据化异常如何影响生死与 NPC 独立意志。',
    'PLOT_MECHANISM_DUNGEON': '副本危机边界：规定入本条件、通关判据、失败惩罚与带出物限制。',
    'PLOT_MECHANISM_CONTAMINATION': '污染异变边界：规定接触传播途径、潜伏征兆、不可逆异化阶段与隔离代价。',
    'PLOT_MECHANISM_ALIEN': '外星接触边界：突出非人逻辑差异、技术/生物鸿沟与沟通误判风险。',
    'PLOT_MECHANISM_DISASTER': '灾难环境边界：落实基础设施瘫痪、物资衰减曲线与次生秩序崩溃。',
    'PLOT_MECHANISM_BIOCHEMICAL': '生化危机边界：写清病原传播方式、检测盲区、药物稀缺与封控冲突。',
    'PLOT_MECHANISM_MAIN_GOD': '主神空间边界：限定征召间隔、兑换门槛、抹杀条款与资深者生态压迫。',
    'PLOT_MECHANISM_RULE_TASK': '规则任务边界：规则条款字面严苛且无情，破题依赖精确发现条文边界与豁免条件。',
}


def recommend_world_bases(types: list[str] | tuple[str, ...] | None) -> list[dict[str, Any]]:
    return rank_bases_for_genres(WORLD_BASES, types, fallback_id='WORLD_HYBRID_BALANCED')


def default_world_base_id(types: list[str] | tuple[str, ...] | None) -> str:
    ranked = recommend_world_bases(types)
    return ranked[0]['id'] if ranked else 'WORLD_HYBRID_BALANCED'


def compile_world_spec(
    genre_ids: list[str] | tuple[str, ...],
    *,
    base_id: str | None = None,
    knobs: dict[str, Any] | None = None,
    world_mechanism_ids: list[str] | tuple[str, ...] = (),
    fingerprints: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    custom_notes: str = '',
    enabled: bool = True,
) -> dict[str, Any]:
    """Compile a single unified Book World Rule-Engine Spec (`world_spec.json`)."""
    norm_genres = canonical_types(list(genre_ids)) if genre_ids else []
    bid = base_id if (base_id and base_id in WORLD_BASE_MAP) else default_world_base_id(norm_genres)
    base = WORLD_BASE_MAP[bid]
    norm_knobs = normalize_spec_knobs(WORLD_KNOBS, knobs, base['default_knobs'])

    dims = dict(base['dimensions'])
    hard_opt = _WORLD_KNOB_MAP['rule_hardness'].get(norm_knobs['rule_hardness'])
    cost_opt = _WORLD_KNOB_MAP['cost_severity'].get(norm_knobs['cost_severity'])
    expo_opt = _WORLD_KNOB_MAP['exposition_pace'].get(norm_knobs['exposition_pace'])
    if hard_opt:
        dims['premise_law'] = f"【{hard_opt['label']}】{hard_opt['directive']}"
    if cost_opt:
        dims['scarcity_cost'] = f"【{cost_opt['label']}】{cost_opt['directive']}"
    if expo_opt:
        dims['exposition_policy'] = f"【{expo_opt['label']}】{expo_opt['directive']}"

    redlines: list[str] = list(base['anti_drift_redlines'])
    for ban_id in norm_knobs.get('world_bans', ()):
        ban_opt = _WORLD_KNOB_MAP['world_bans'].get(ban_id)
        if ban_opt and ban_opt['directive'] not in redlines:
            redlines.append(ban_opt['directive'])

    legacy_hints: list[str] = []
    for mid in world_mechanism_ids:
        if h := WORLD_MECHANISM_EXECUTION_HINTS.get(str(mid)):
            legacy_hints.append(h)

    accepted_fps: list[dict[str, Any]] = []
    for fp in fingerprints:
        if not isinstance(fp, dict):
            continue
        if norm_genres and not is_fingerprint_compatible(fp, norm_genres):
            continue
        body = fp.get('body') or {}
        accepted_fps.append({
            'id': fp.get('id', ''),
            'title': fp.get('title', '参考世界规则指纹'),
            'base_id': fp.get('base_id', bid),
            'techniques': list(body.get('techniques') or ())[:4],
            'drift_guards': list(body.get('drift_guards') or ())[:3],
            'function_notes': dict(body.get('function_notes') or {}),
        })
        for g in (body.get('drift_guards') or ())[:2]:
            if g and g not in redlines:
                redlines.append(g)

    spec = {
        'spec_version': 1,
        'domain': 'world',
        'enabled': bool(enabled),
        'genre_ids': norm_genres,
        'base_id': bid,
        'base_name': base['name'],
        'tagline': base['tagline'],
        'knobs': norm_knobs,
        'dimensions': dims,
        'anti_drift_redlines': redlines[:10],
        'micro_contrasts': deepcopy(base['micro_contrasts']),
        'legacy_hints': legacy_hints[:6],
        'fingerprint_ids': [fp['id'] for fp in accepted_fps if fp.get('id')],
        'fingerprints': accepted_fps,
        'custom_notes': str(custom_notes or '').strip()[:800],
    }
    return finalize_spec_payload(spec)


def load_world_spec(store: Store) -> dict[str, Any] | None:
    return load_spec_file(store, WORLD_SPEC_FILENAME)


def save_world_spec(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    return save_spec_file(store, WORLD_SPEC_FILENAME, spec)


def build_world_stage_packet(
    spec: dict[str, Any] | None,
    *,
    scope: str = 'book',
    max_chars: int = 900,
) -> dict[str, Any] | None:
    """Bounded craft packet for 03 `world_design` (<=900 chars)."""
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    preferred = ('rule_limit', 'opening_reveal') if scope == 'book' else ('rule_limit', 'resource_cost')
    contrasts = sorted(
        list(spec.get('micro_contrasts') or ()),
        key=lambda r: (0 if r.get('target_function') in preferred else 1),
    )[:2]
    lines = [f"【世界规则基座：{spec.get('base_name', '')}】{PRIORITY_ARBITRATION_NOTE}"]
    for dk, zh in (
        ('premise_law', '底层铁律'),
        ('scarcity_cost', '稀缺代价'),
        ('institution_gate', '制度制约'),
        ('background_clock', '后台时钟'),
        ('exposition_policy', '渗入纪律'),
        ('genre_firewall', '防污染墙'),
    ):
        if val := (spec.get('dimensions') or {}).get(dk):
            lines.append(f"- {zh}：{val}")
    for h in (spec.get('legacy_hints') or ())[:2]:
        lines.append(f"- 特殊机制：{h}")
    for fp in (spec.get('fingerprints') or ())[:2]:
        for t in (fp.get('techniques') or ())[:2]:
            lines.append(f"- 参考世界手法（{fp.get('title', '')}）：{t}")
    if spec.get('custom_notes'):
        lines.append(f"- 作者补充：{spec['custom_notes'][:140]}")
    for rl in (spec.get('anti_drift_redlines') or ())[:3]:
        lines.append(f"- 红线：{rl}")
    for mc in contrasts:
        lines.append(f"- 微对照[{mc.get('label', '')}] ❌{mc.get('bad_ai', '')[:65]} → ✅{mc.get('target_craft', '')[:85]}")
    return {
        'domain': 'world',
        'base_id': spec.get('base_id', ''),
        'base_name': spec.get('base_name', ''),
        'sha256': spec.get('sha256', ''),
        'prompt_block': truncate_lines_to_budget(lines, max_chars),
    }


def build_action_world_gate_packet(
    spec: dict[str, Any] | None,
    *,
    max_chars: int = 260,
) -> dict[str, Any] | None:
    """Compact rule & cost gate slice for 08 `action_design` (<=260 chars)."""
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    dims = spec.get('dimensions') or {}
    lines = [
        f"【行动门槛与代价标尺：{spec.get('base_name', '')}】",
        f"- 代价：{dims.get('scarcity_cost', '')}",
        f"- 制约：{dims.get('institution_gate', '')}",
    ]
    if rls := (spec.get('anti_drift_redlines') or ())[:2]:
        lines.append(f"- 红线：{'；'.join(rls)}")
    return {
        'domain': 'world',
        'base_id': spec.get('base_id', ''),
        'sha256': spec.get('sha256', ''),
        'prompt_block': truncate_lines_to_budget(lines, max_chars),
    }


def build_review_world_guard(spec: dict[str, Any] | None) -> str:
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return ''
    rls = [str(x).strip() for x in (spec.get('anti_drift_redlines') or ()) if str(x).strip()][:2]
    if not rls:
        return ''
    return f"【世界规则防漂移({spec.get('base_name', '')})】{'；'.join(rls)}"
