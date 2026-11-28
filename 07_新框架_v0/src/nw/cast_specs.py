"""Executable Cast & Character Dynamics Specification Library (`cast_spec.json`).

Defines HOW cast rosters, protagonist flaws, antagonist intelligence, supporting-cast autonomy,
relation asymmetries, and cost-driven arcs operate (NEVER pre-baking stereotypical personality
templates!). Aligned 1-to-1 with Track 2 (`character_conflict`), Step 04 (`character_design`),
Step 05 (`static_relations`), and Step 16 (`review`).
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

CAST_SPEC_FILENAME = 'cast_spec.json'

CAST_FUNCTION_LABELS: dict[str, str] = {
    'protagonist_arc': '主角驱动与可验证盲点',
    'antagonist_logic': '反派独立利害与不降智',
    'supporting_relation': '配角复用与独立关系网',
}

CAST_KNOBS: dict[str, dict[str, Any]] = {
    'cast_density': {
        'label': '常驻核心阵容规模',
        'multi': False,
        'options': [
            {
                'id': 'tight_core',
                'label': '精简核心（3–5 人深度刻画）',
                'directive': '严格控制常驻核心人数，反复复用已出场人物承担多重功能，避免新面孔走马灯稀释笔墨。',
            },
            {
                'id': 'layered_standard',
                'label': '标准分层（6–10 人主次分明）',
                'directive': '按主角团/核心对手/关键中间人/功能配角四层管理，新人只在已有角色无法承接职责时才新建。',
            },
            {
                'id': 'broad_ensemble',
                'label': '宏阔群像（分批登场、多阵营并行）',
                'directive': '按卷分批亮出不同阵营代表人物，每阵营立住 1–2 个高辨识核心声线，避免一次塞入十张脸。',
            },
        ],
    },
    'antagonist_style': {
        'label': '主要阻力与反派形态',
        'multi': False,
        'options': [
            {
                'id': 'systemic_pressure',
                'label': '制度、环境与利益链条压迫',
                'directive': '阻力主要来自冷酷的规则体系、稀缺生态或各自自保的普通人利益碰撞，无人纯粹为坏而坏。',
            },
            {
                'id': 'rival_duel',
                'label': '势均力敌的智斗/宿敌对手',
                'directive': '核心反派与主角目标直接冲突、信息与手腕不逊于主角，会复盘止损、会设局反制，绝不降智送人头。',
            },
            {
                'id': 'tiered_factions',
                'label': '阶段递进的多方势力对手',
                'directive': '每卷换档亮出更高阶层的理性对手，旧对手败而不一定全死，可能转为暗处搅局者或被迫临时盟友。',
            },
        ],
    },
    'side_cast_autonomy': {
        'label': '配角自主度与独立支线',
        'multi': False,
        'options': [
            {
                'id': 'mainline_anchored',
                'label': '紧密咬合主线（但有独立诉求）',
                'directive': '配角戏份紧扣主线推进，但每个重要配角必须有自己非主角的私心与底线，绝不当无脑捧哏。',
            },
            {
                'id': 'active_subplots',
                'label': '独立支线占 30%+（自主引发转折）',
                'directive': '全书至少保留 2 条不经主角的配角间互动关系，30%–40% 的关键剧情转折由配角自主选择触发。',
            },
            {
                'id': 'multi_thread_autonomy',
                'label': '高度自治（多线交汇推动全局）',
                'directive': '多位核心人物各持独立议程在后台行动，与主角线在关键节点发生利害碰撞或信息交汇。',
            },
        ],
    },
    'cast_bans': {
        'label': '人物与关系防崩坏禁忌（可多选）',
        'multi': True,
        'options': [
            {
                'id': 'no_dumb_villain',
                'label': '禁反派降智送经验',
                'directive': '严禁反派明知风险却无脑嘲讽、放水、自爆底牌或看不见明摆着的陷阱以衬托主角聪明。',
            },
            {
                'id': 'no_tool_sidekick',
                'label': '禁配角全员工具人/捧哏',
                'directive': '严禁配角只负责夸主角、问设定问题或递完道具就消失；重要配角须有独立目标与标志性声线。',
            },
            {
                'id': 'no_quota_filler',
                'label': '禁为凑人数硬造新角色',
                'directive': '优先复用已建角色承接 cast_demands；凡新增角色必写清不可替代性与退场/复现安排。',
            },
            {
                'id': 'no_secret_leak',
                'label': '禁人物公开字段泄露暗身份',
                'directive': '暗身份、卧底立场与未揭真相的 secret/trigger 严格与公开 name/role/clue 物理隔离，绝不偷跑。',
            },
            {
                'id': 'no_cheap_turn',
                'label': '禁无代价嘴炮顿悟或秒速洗白',
                'directive': '人物立场反转、弧光蜕变或关系修复必须经过具体事件代价与行为验证，严禁几句嘴炮直接感化。',
            },
        ],
    },
}

_CAST_KNOB_MAP = knob_option_map(CAST_KNOBS)

CAST_BASES: tuple[dict[str, Any], ...] = (
    {
        'id': 'CAST_LONE_BREAKER',
        'name': '孤狼破局与强敌环伺型',
        'tagline': '主角独立扛压靠算计与手段破局，配角以真实利益聚散绝不盲从',
        'recommended_genres': ('GENRE_XIANXIA', 'GENRE_XUANHUAN', 'GENRE_GAOWU', 'GENRE_WUXIA', 'GENRE_MOSHI'),
        'incompatible_genres': ('GENRE_QINGCHUN', 'GENRE_YANQING'),
        'default_knobs': {
            'cast_density': 'tight_core',
            'antagonist_style': 'tiered_factions',
            'side_cast_autonomy': 'mainline_anchored',
            'cast_bans': ['no_dumb_villain', 'no_tool_sidekick', 'no_quota_filler', 'no_secret_leak', 'no_cheap_turn'],
        },
        'dimensions': {
            'protagonist_drive': '主角核心欲望具体切身（保命/查账/登顶/脱枷锁），同时自带可验证的行为盲点或信任缺口，靠代价修正判断。',
            'antagonist_logic': '每个阶层的强敌与执事都维护自身资源盘和规矩体面，出手狠辣且讲成本收益，绝不降智给主角当经验包。',
            'supporting_roster': '不强塞常驻话痨跟班；同行者、情报贩子、同门师兄妹各有自己的保命算盘，利益一致时合作、冲突时随时反水。',
            'relation_asymmetry': '突出强弱权力差、资源债与信息不对称：主角初期处弱势但握有对手在意的筹码或把柄。',
            'independent_side_ties': '宗门派系之间、对手与上级之间保持至少 2 条不经主角的利益摩擦线，为主角提供借势缝隙。',
            'arc_conversion': '主角从被动求生到主动控局的弧光必须落在一次次狠心取舍与真实伤疤上，不靠口号宣言。',
        },
        'anti_drift_redlines': [
            '严禁主角孤狼化写成毫无情绪波动的面瘫杀神，或让所有配角一见主角就纳头便拜。',
            '严禁反派每次都因轻敌、话多或无脑挑衅输给主角。',
            '严禁人物卡公开字段提前泄露暗身份或未触发的背叛结局。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'protagonist_arc',
                'label': '有盲点与代价的主角卡',
                'bad_ai': '主角：冷静睿智、杀伐果断、重情重义、隐藏绝世天赋，目标成为天下第一。',
                'target_craft': '主角：外门记账杂役，核心诉求是先保住性命再查清师父失踪真账；盲点是习惯独自兜底不肯分润信任，直到一次孤注一掷险些害死唯一证人，才被迫学会拿利益结盟。',
                'why': '具体处境+真实盲点+改变条件，人物立刻活起来而不是标签堆砌。',
            },
            {
                'target_function': 'antagonist_logic',
                'label': '不降智的理性反派卡',
                'bad_ai': '反派：恶毒长老，嫉妒主角天赋，天天派手下去送死并扬言要废掉主角。',
                'target_craft': '反派：外堂账房执事，私挪三年丹药灵石补自家突破缺口，本无意招惹主角，只因主角经手的旧账可能暴露亏空；行事重体面灭口，绝不亲自下场留把柄。',
                'why': '反派动机从自身硬利益长出，既狠又合理，读者才真替主角捏把汗。',
            },
            {
                'target_function': 'supporting_relation',
                'label': '独立互动防工具人关系网',
                'bad_ai': '配角A是主角忠犬跟班，配角B是主角美女红颜，两人只围着主角转。',
                'target_craft': '药童与黑市牙人私下存在欠债与假药换真丹的隐秘交易（不经主角），两人互相提防却又怕事情败露连累彼此，正好给主角制造撬动局势的第三条线。',
                'why': '配角彼此有独立生活与利害，整个世界立刻立体。',
            },
        ],
    },
    {
        'id': 'CAST_DUAL_TENSION',
        'name': '双强拉扯与关系镜像型',
        'tagline': '两位核心角色互为镜面与阻力，各自目标独立、立场碰撞张力拉满',
        'recommended_genres': ('GENRE_YANQING', 'GENRE_QINGCHUN', 'GENRE_CHENGZHANG'),
        'incompatible_genres': ('GENRE_KONGBU', 'GENRE_MOSHI'),
        'default_knobs': {
            'cast_density': 'tight_core',
            'antagonist_style': 'rival_duel',
            'side_cast_autonomy': 'mainline_anchored',
            'cast_bans': ['no_dumb_villain', 'no_tool_sidekick', 'no_quota_filler', 'no_cheap_turn'],
        },
        'dimensions': {
            'protagonist_drive': '两位核心主角各自有不依赖对方也能成立的事业/生存目标与专属心防，绝不把其中一方降格为挂件。',
            'antagonist_logic': '拆散或阻碍两人的外部阻力来自真实阶层、旧怨、商业/家族利益或观念分歧，而非无脑恶毒情敌。',
            'supporting_roster': '双方身边的亲友、同事或前辈各有护短立场，能放大两人的信息差与偏爱实证，不沦为纯助攻拉拉队。',
            'relation_asymmetry': '明确刻画情感投入错位、权力/话语权起伏与未还清的旧日人情债，让关系张力有清晰推拉支点。',
            'independent_side_ties': '双方各自原生社交圈之间存在独立利益或旧恩怨连接（不经主角），在关键节点卷入主关系。',
            'arc_conversion': '心防卸下与彼此成就靠实打实的共担风险和习惯改变验证，称呼、站位与底线让步循序渐进。',
        },
        'anti_drift_redlines': [
            '严禁把第二核心角色写成围着主角打转、失去独立判断与事业线的恋爱脑工具人。',
            '严禁制造纯靠恶毒女配/男配下药造谣推动关系的廉价套路。',
            '严禁两人说话声音、停顿习惯和处事逻辑同质化分不出彼此。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'protagonist_arc',
                'label': '双强各自独立目标卡',
                'bad_ai': '女主温柔善良但有点迷糊，男主高冷多金只对女主温柔。',
                'target_craft': '角色A：独立审计师，执念是保住恩师清白并守住职业底线，习惯把脆弱藏在公事公办的利落话术后；角色B：接盘家族烂摊子的次子，既要保企业现金流又必须查清内部蛀虫，习惯先用筹码试探人心。',
                'why': '两人各自撑得起半边天，相遇碰撞出的火花才有高级感。',
            },
            {
                'target_function': 'antagonist_logic',
                'label': '去狗血化真实外部阻力',
                'bad_ai': '反派：疯狂爱慕男主的千金，天天找人泼女主咖啡、造谣毁女主名声。',
                'target_craft': '阻力方：持股三成的家族元老，反对男主清查旧账只因当年违规担保牵连自己切身利益，因此精准利用角色A的审计报告向男主施压。',
                'why': '用真实利益博弈代替泼咖啡套路，同时考验两人的信任底线。',
            },
            {
                'target_function': 'supporting_relation',
                'label': '非拉拉队配角关系',
                'bad_ai': '闺蜜和助理整天在旁边起哄“你们俩好配快在一起”。',
                'target_craft': '角色A的律所合伙人与角色B的财务总监是旧年同窗兼竞争对手，两人各自给自家老板递刀子又暗中较劲，自然影响主线节奏。',
                'why': '配角各站各的立场，关系网鲜活真实。',
            },
        ],
    },
    {
        'id': 'CAST_SQUAD_COMPLEMENT',
        'name': '小队互补与分工试错型',
        'tagline': '成员能力与性格短板严格互补，团队内有真实分歧与信任磨合代价',
        'recommended_genres': ('GENRE_QIHUAN', 'GENRE_KEHUAN', 'GENRE_YOUXI', 'GENRE_DIANJING', 'GENRE_ZHUTIAN', 'GENRE_SAIBO', 'GENRE_WEILAI'),
        'incompatible_genres': ('GENRE_YANQING',),
        'default_knobs': {
            'cast_density': 'layered_standard',
            'antagonist_style': 'rival_duel',
            'side_cast_autonomy': 'active_subplots',
            'cast_bans': ['no_dumb_villain', 'no_tool_sidekick', 'no_quota_filler', 'no_cheap_turn'],
        },
        'dimensions': {
            'protagonist_drive': '主角在团队中有不可替代的核心职能（决策/破题/兜底）与明显短板，必须依赖队友补位才能闯过难关。',
            'antagonist_logic': '敌方队伍或环境危机同样具备完整配合与针对性战术，专门盯准主角小队的配合缝隙与资源短板下手。',
            'supporting_roster': '3–5 名核心队友分工互不重叠（如信息/执行/后勤/交涉），每人带着不同加入动机、脾气与声线。',
            'relation_asymmetry': '团队内部存在理念冲突（保守求稳 vs 冒险搏命）、分配分歧与过往心结，绝非一团和气喊口号。',
            'independent_side_ties': '队友之间有各自专属的默契、旧账或互相看不顺眼的互动关系（不经过主角调停）。',
            'arc_conversion': '从临时利益搭伙到真正把后背交给彼此，靠危机里扛住一次次失误与救场实打实攒出信任。',
        },
        'anti_drift_redlines': [
            '严禁全队只有主角一个人在想办法、出风头，其余队友沦为喊“666/队长牛逼”的背景板。',
            '严禁一次性拉入七八个技能与性格雷同的队员导致辨识度崩溃。',
            '严禁队内分歧靠主角发表一段鸡汤演讲就立刻全员统一思想。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'protagonist_arc',
                'label': '带短板的小队核心卡',
                'bad_ai': '队长：全能战神，指挥最强、输出最高、人缘最好，队友全听他指挥。',
                'target_craft': '队长：擅长临场拆解规则漏洞与豪赌破局，但体能续航差且常因激进战术把队友拉进险境；必须靠冷静抠门的后勤搭档拉住安全底线。',
                'why': '队长有硬短板，队友才真正拥有不可替代的存在价值。',
            },
            {
                'target_function': 'antagonist_logic',
                'label': '针对性拆招敌对团队',
                'bad_ai': '对手战队实力不如主角，赛前放狠话，比赛中失误连连惨败。',
                'target_craft': '卫冕强队复盘过主角队三场录像，开局直接封锁主角最擅长的快节奏切入点，逼迫主角队的薄弱新人位独立扛压。',
                'why': '对手懂得针对短板布置战术，比赛与冒险才有真实含金量。',
            },
            {
                'target_function': 'supporting_relation',
                'label': '队友间独立化学反应',
                'bad_ai': '队友A、B、C只分别和队长对话，彼此从不交流。',
                'target_craft': '精打细算的装备师一直嫌弃冲锋手耗材太费钱，两人私下签了“损毁装备按次扣宵夜”的土规矩，危急关头却总先保住对方后路。',
                'why': '队友间的活人摩擦让整个小队充满烟火气与凝聚力。',
            },
        ],
    },
    {
        'id': 'CAST_POWER_ENSEMBLE',
        'name': '多方势力与群像博弈型',
        'tagline': '三方以上势力各有理性盘算与鲜明阶层声线，无人沦为脸谱配角',
        'recommended_genres': ('GENRE_QUANMOU', 'GENRE_LISHI', 'GENRE_SHANGZHAN', 'GENRE_JUNSHI'),
        'incompatible_genres': ('GENRE_GAOXIAO', 'GENRE_QINGCHUN'),
        'default_knobs': {
            'cast_density': 'broad_ensemble',
            'antagonist_style': 'tiered_factions',
            'side_cast_autonomy': 'multi_thread_autonomy',
            'cast_bans': ['no_dumb_villain', 'no_tool_sidekick', 'no_quota_filler', 'no_secret_leak', 'no_cheap_turn'],
        },
        'dimensions': {
            'protagonist_drive': '主角身处庞大利益网中，既有野心/信念目标又受制于羽翼未丰，必须借各方矛盾生存并逐步掌局。',
            'antagonist_logic': '每个阵营掌权者皆为久经风浪的老手：重视长期政治/商业账本，懂得妥协、分化、弃子与留后手。',
            'supporting_roster': '按阵营与职级分批出场，核心人物在说话措辞、称谓习惯与决策风格上形成鲜明区分（遮名可辨）。',
            'relation_asymmetry': '精雕君臣/上下级猜忌、世交与政敌交错、债权债务、联姻掣肘等多层非对称张力。',
            'independent_side_ties': '各派系内部与派系之间持续存在不经主角的倾轧与交易，主角只是大棋局中的变数之一。',
            'arc_conversion': '群像角色随局势起伏经历立场迁移、理想磨损或绝境亮节，不把任何人写死成一成不变的纸片人。',
        },
        'anti_drift_redlines': [
            '严禁群像里五六个大臣/高管全用同一套腔调轮流念设定。',
            '严禁开篇前两章一口气甩出十几个陌生人名官职让读者彻底脸盲。',
            '严禁位高权重的对手像草包一样轻易被主角三言两语忽悠交出底牌。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'protagonist_arc',
                'label': '棋局变数型主角卡',
                'bad_ai': '主角：足智多谋、料事如神，所有朝臣都在他的算计之中。',
                'target_craft': '主角：寒门出身的户部主事，熟稔实务账目但缺门阀靠山；靠把两派都不敢碰的烂摊子做成筹码上位，代价是每进一步都不得不染上手中泥污。',
                'why': '既有实操硬本事又有真实资源软肋，上位之路步步惊心。',
            },
            {
                'target_function': 'antagonist_logic',
                'label': '老辣稳健的对手卡',
                'bad_ai': '宰相贪婪愚蠢，当众大骂主角并直接派刺客暗杀留下铁证。',
                'target_craft': '内阁次辅：老成持重，察觉主角动摇自身盐税盘子后不怒反笑，当堂提拔主角去查最难啃的边饷旧案——办不成名正言顺革职，办成了则逼主角与军方结死仇。',
                'why': '真正高段位的阳谋与借刀杀人，远比派刺客精彩十倍。',
            },
            {
                'target_function': 'supporting_relation',
                'label': '阵营间多维非对称关系',
                'bad_ai': 'A派全是好人互相团结，B派全是坏人互相勾结。',
                'target_craft': '清流御史与边镇总兵政见水火不容，却因同在十年前粮案中欠下旧人情而暗中互保底线；这种裂缝成为主角唯一能借力的支点。',
                'why': '复杂人性与多维利害交织，群像瞬间有了史诗质感。',
            },
        ],
    },
    {
        'id': 'CAST_SLICE_COMMUNITY',
        'name': '市井群像与活人烟火型',
        'tagline': '邻里/同僚/同行各有小算盘与怪癖，高频日常碰撞长出温暖与笑点',
        'recommended_genres': ('GENRE_DUSHI', 'GENRE_XIANSHI', 'GENRE_ZHIYE', 'GENRE_ZHONGDIAN', 'GENRE_QINGXIAOSHUO', 'GENRE_GAOXIAO', 'GENRE_ERCIYUAN', 'GENRE_TIYU'),
        'incompatible_genres': ('GENRE_KONGBU', 'GENRE_MOSHI'),
        'default_knobs': {
            'cast_density': 'layered_standard',
            'antagonist_style': 'systemic_pressure',
            'side_cast_autonomy': 'active_subplots',
            'cast_bans': ['no_tool_sidekick', 'no_quota_filler', 'no_cheap_turn'],
        },
        'dimensions': {
            'protagonist_drive': '主角诉求接地气（还清债、保住小店、搞出成果、过上好日子），有小精明也有护短软肋，像身边真认识的活人。',
            'antagonist_logic': '麻烦制造者多是爱占便宜的同行、卡流程的甲方、偏心长辈或现实规则本身，让人气得牙痒却又合情合理。',
            'supporting_roster': '常驻街坊、同事、熟客各带鲜明口头禅、抠门/热心/死要面子等可感习惯，复现率高、越熟越有戏。',
            'relation_asymmetry': '靠人情往来、嘴硬心软、同行竞争又互搭把手等生活化张力撑起日常趣味。',
            'independent_side_ties': '街坊与同事之间有自己的家长里短、互怼和合伙买卖，主角只是这条街/这个团队里的鲜活一员。',
            'arc_conversion': '人物变化藏在生活细节里（从防备精算到愿意兜底、从畏手畏脚到扛起担子），温润真实不喊口号。',
        },
        'anti_drift_redlines': [
            '严禁为了制造笑点把所有配角写成毫无生活常识的弱智丑角。',
            '严禁全员说着同一套网络热梗腔，遮住名字必须能听出谁在说话。',
            '严禁日常配角走马灯出场一次就忘，浪费已建立的熟悉感。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'protagonist_arc',
                'label': '烟火活人主角卡',
                'bad_ai': '主角：性格随和风趣，乐于助人，大家都喜欢他。',
                'target_craft': '主角：精打细算的修表店老板，嘴上标榜“绝不干赔本买卖”，真遇老街坊吃亏又总忍不住暗中垫料兜底，事后还要心疼账本念叨半天。',
                'why': '反差感与真实算计并存，读者一眼就能记住。',
            },
            {
                'target_function': 'antagonist_logic',
                'label': '生活化真实麻烦方',
                'bad_ai': '反派：隔壁店主是个纯粹大坏蛋，半夜放火烧主角店铺。',
                'target_craft': '对手：隔壁连锁店店长，受总部业绩指标逼迫打价格战挖主角熟客，嘴上客客气气递烟，背地里卡主角上游配件供货。',
                'why': '真实商业与生活摩擦，解决起来既解气又接地气。',
            },
            {
                'target_function': 'supporting_relation',
                'label': '常驻街坊独立戏份',
                'bad_ai': '熟客甲乙丙每次出现只负责排队夸主角手艺好。',
                'target_craft': '开早餐铺的大婶和爱捡漏的退休老爷子天天为两块钱葱油饼斗嘴，关键时刻却联手替主角盯梢拦下捣乱混混。',
                'why': '常驻配角自带小剧场，全书烟火气扑面而来。',
            },
        ],
    },
    {
        'id': 'CAST_MYSTERY_SUSPECTS',
        'name': '封闭嫌疑网与信息博弈型',
        'tagline': '人人藏隐情与自保动机，台词带防线误导，暗身份物理严封',
        'recommended_genres': ('GENRE_XUANYI', 'GENRE_TUILI', 'GENRE_JINGSONG', 'GENRE_LINGYI', 'GENRE_KONGBU'),
        'incompatible_genres': ('GENRE_GAOXIAO', 'GENRE_ZHONGDIAN'),
        'default_knobs': {
            'cast_density': 'layered_standard',
            'antagonist_style': 'rival_duel',
            'side_cast_autonomy': 'active_subplots',
            'cast_bans': ['no_dumb_villain', 'no_tool_sidekick', 'no_quota_filler', 'no_secret_leak', 'no_cheap_turn'],
        },
        'dimensions': {
            'protagonist_drive': '调查者/入局者怀有无法撒手的职业或私密执念，同时受制于自身信息盲区与对某人的固有偏见。',
            'antagonist_logic': '真凶与幕后操盘手具备严密的不在场算计、替罪羊预案与心理伪装，被怀疑时会借半真半假供词反误导。',
            'supporting_roster': '关键嫌疑人与目击者各有自己想遮掩的“次级秘密”（未必是真凶却足以让他们撒谎），形成真实迷雾。',
            'relation_asymmetry': '所有关系围绕“谁知道什么、谁以为别人不知道什么、谁握着谁的把柄”精确布设信息差。',
            'independent_side_ties': '嫌疑人之间存在隐秘旧交、勒索或互相包庇链条，调查一处必然惊动另一处反应。',
            'arc_conversion': '真相逼近过程持续撕开表面体面，迫使主角与证人在自保与揭黑之间做出艰难抉择。',
        },
        'anti_drift_redlines': [
            '严禁在人物公开字段（name/role/clue/public_identity）泄露卧底、真凶或未揭暗身份。',
            '严禁嫌疑人面对主角盘问毫无防备、有问必答主动交代全部隐情。',
            '严禁全书除了真凶外其余嫌疑人全是清白无辜的纯背景板（丧失推理张力）。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'protagonist_arc',
                'label': '带认知盲区的调查者卡',
                'bad_ai': '侦探：观察力逆天、一眼看穿所有谎言，从不犯错。',
                'target_craft': '刑警：对物证时间线极敏感，但因三年前办错一桩熟人证词案而本能过度怀疑直系亲属，恰被真凶利用这点引偏前两轮方向。',
                'why': '侦探有真实专业强项也有心理偏误，破案过程才有拉锯感。',
            },
            {
                'target_function': 'antagonist_logic',
                'label': '高伪装真凶卡（暗身份隔离）',
                'bad_ai': '公开角色名直接写成“真凶·医生张三”，说话阴森森一脸坏人相。',
                'target_craft': '公开身份：热心配合调查的急诊科值班医生，主动提供关键急救记录赢得信任；secret/trigger 严格锁入暗层，只在特定药瓶批号被核对时才露破绽。',
                'why': '严格执行暗身份隔离与合理伪装，审稿与读者体验双保险。',
            },
            {
                'target_function': 'supporting_relation',
                'label': '次级秘密制造迷雾',
                'bad_ai': '其他嫌疑人都在家睡觉，没有任何秘密和作案动机。',
                'target_craft': '死者秘书虽非凶手，却在案发前夜私吞了公司备用金，因此刻意隐瞒自己九点半回过办公室的事实，并与保安私下串供，自然造出逼真假线索。',
                'why': '每个人撒谎都有自洽理由，推理迷雾浑然天成。',
            },
        ],
    },
    {
        'id': 'CAST_HYBRID_BALANCED',
        'name': '全能稳健阵容型',
        'tagline': '严守角色复用、反派不降智与配角独立互动，适配任意单/多题材融合',
        'recommended_genres': ('GENRE_TONGREN',),
        'incompatible_genres': (),
        'default_knobs': {
            'cast_density': 'layered_standard',
            'antagonist_style': 'rival_duel',
            'side_cast_autonomy': 'active_subplots',
            'cast_bans': ['no_dumb_villain', 'no_tool_sidekick', 'no_quota_filler', 'no_secret_leak', 'no_cheap_turn'],
        },
        'dimensions': {
            'protagonist_drive': '确立主角清晰欲望、行事底线与待磨炼的认知盲点，让每一次选择都有真实心理与现实依据。',
            'antagonist_logic': '主要对手有自洽动机与合理手段，会根据主角的行动调整策略，绝不降智送经验。',
            'supporting_roster': '复用已有角色优先，新出场重要配角必须有独特目标、标志性说话习惯与不可替代功能。',
            'relation_asymmetry': '围绕利益、信任、信息差或情感债务建立非对称连接，避免人物间只有平淡好坏标签。',
            'independent_side_ties': '全书至少维持 2 条不经过主角的配角间独立互动线，让世界在主角视野外也在运转。',
            'arc_conversion': '所有人物成长与关系变化必须通过具体事件代价落地，并在后续场景中可见行为改变。',
        },
        'anti_drift_redlines': [
            '严禁凭空造一次性工具人应付剧情需求或为了凑人数堆砌空壳角色。',
            '严禁配角与反派沦为主角的复读机或经验包。',
            '严禁暗身份未到揭晓时机就在公开信息中泄密。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'protagonist_arc',
                'label': '立体主角卡基准',
                'bad_ai': '主角性格完美、善良聪明又果断，没有缺点。',
                'target_craft': '写清主角“想要什么、最怕失去什么、习惯用什么方式保护自己、这个习惯会在什么局面反噬自己”。',
                'why': '四个具体问题立住一个能演化长篇弧光的活人。',
            },
            {
                'target_function': 'antagonist_logic',
                'label': '站得住脚的对手卡',
                'bad_ai': '反派就是嫉妒主角，毫无理由地处处作对。',
                'target_craft': '写清对手眼中的“正当利益或生存恐惧”、手握的实际筹码以及面对受挫时的理性反制。',
                'why': '对手越真实可敬/可畏，主角赢下来才越痛快。',
            },
            {
                'target_function': 'supporting_relation',
                'label': '配角去工具化',
                'bad_ai': '配角只在主角需要线索时跳出来递纸条然后退场。',
                'target_craft': '给该配角一条与主角目标交叉但不重合的私事，递出线索本身也是他在替自己换取筹码。',
                'why': '交易与私心让每个配角都长出独立筋骨。',
            },
        ],
    },
)

CAST_BASE_MAP: dict[str, dict[str, Any]] = {b['id']: b for b in CAST_BASES}

CAST_MECHANISM_EXECUTION_HINTS: dict[str, str] = {
    'PLOT_MECHANISM_BLOODLINE': '血脉机制边界：明确血脉觉醒前的潜伏征兆、触发代价与招致外部觊觎的副作用。',
    'PLOT_MECHANISM_TALENT': '天赋机制边界：写清天赋的精准适用域与盲区短板，避免全能开挂。',
    'PLOT_MECHANISM_INVINCIBLE': '无敌流张力转化：实力碾压时冲突重心转向信息差、守护软肋、规则限制、身份隐藏或情绪反差，禁纯数值复读。',
    'PLOT_MECHANISM_GENE': '基因改造边界：明确改造排异代价、维持成本与伦理/制度排斥后果。',
    'PLOT_MECHANISM_TEAM': '团队协作边界：每名成员分工与短板严格互补，保留真实决策分歧与信任磨合曲线。',
}


def recommend_cast_bases(types: list[str] | tuple[str, ...] | None) -> list[dict[str, Any]]:
    return rank_bases_for_genres(CAST_BASES, types, fallback_id='CAST_HYBRID_BALANCED')


def default_cast_base_id(types: list[str] | tuple[str, ...] | None) -> str:
    ranked = recommend_cast_bases(types)
    return ranked[0]['id'] if ranked else 'CAST_HYBRID_BALANCED'


def compile_cast_spec(
    genre_ids: list[str] | tuple[str, ...],
    *,
    base_id: str | None = None,
    knobs: dict[str, Any] | None = None,
    character_mechanism_ids: list[str] | tuple[str, ...] = (),
    fingerprints: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    custom_notes: str = '',
    enabled: bool = True,
) -> dict[str, Any]:
    """Compile a single unified Book Cast & Character Dynamics Spec (`cast_spec.json`)."""
    norm_genres = canonical_types(list(genre_ids)) if genre_ids else []
    bid = base_id if (base_id and base_id in CAST_BASE_MAP) else default_cast_base_id(norm_genres)
    base = CAST_BASE_MAP[bid]
    norm_knobs = normalize_spec_knobs(CAST_KNOBS, knobs, base['default_knobs'])

    dims = dict(base['dimensions'])
    dens_opt = _CAST_KNOB_MAP['cast_density'].get(norm_knobs['cast_density'])
    ant_opt = _CAST_KNOB_MAP['antagonist_style'].get(norm_knobs['antagonist_style'])
    side_opt = _CAST_KNOB_MAP['side_cast_autonomy'].get(norm_knobs['side_cast_autonomy'])
    if dens_opt:
        dims['supporting_roster'] = f"【{dens_opt['label']}】{dens_opt['directive']}"
    if ant_opt:
        dims['antagonist_logic'] = f"【{ant_opt['label']}】{ant_opt['directive']}"
    if side_opt:
        dims['independent_side_ties'] = f"【{side_opt['label']}】{side_opt['directive']}"

    redlines: list[str] = list(base['anti_drift_redlines'])
    for ban_id in norm_knobs.get('cast_bans', ()):
        ban_opt = _CAST_KNOB_MAP['cast_bans'].get(ban_id)
        if ban_opt and ban_opt['directive'] not in redlines:
            redlines.append(ban_opt['directive'])

    legacy_hints: list[str] = []
    for mid in character_mechanism_ids:
        if h := CAST_MECHANISM_EXECUTION_HINTS.get(str(mid)):
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
            'title': fp.get('title', '参考人物群像指纹'),
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
        'domain': 'cast',
        'enabled': bool(enabled),
        'genre_ids': norm_genres,
        'base_id': bid,
        'base_name': base['name'],
        'tagline': base['tagline'],
        'knobs': norm_knobs,
        'dimensions': dims,
        'anti_drift_redlines': redlines[:10],
        'micro_contrasts': deepcopy(base['micro_contrasts']),
        'legacy_hints': legacy_hints[:5],
        'fingerprint_ids': [fp['id'] for fp in accepted_fps if fp.get('id')],
        'fingerprints': accepted_fps,
        'custom_notes': str(custom_notes or '').strip()[:800],
    }
    return finalize_spec_payload(spec)


def load_cast_spec(store: Store) -> dict[str, Any] | None:
    return load_spec_file(store, CAST_SPEC_FILENAME)


def save_cast_spec(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    return save_spec_file(store, CAST_SPEC_FILENAME, spec)


def build_character_stage_packet(
    spec: dict[str, Any] | None,
    *,
    scope: str = 'book',
    max_chars: int = 900,
) -> dict[str, Any] | None:
    """Bounded craft packet for 04 `character_design` (<=900 chars)."""
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    preferred = ('protagonist_arc', 'antagonist_logic') if scope == 'book' else ('antagonist_logic', 'supporting_relation')
    contrasts = sorted(
        list(spec.get('micro_contrasts') or ()),
        key=lambda r: (0 if r.get('target_function') in preferred else 1),
    )[:2]
    lines = [f"【人物群像力学基座：{spec.get('base_name', '')}】{PRIORITY_ARBITRATION_NOTE}"]
    for dk, zh in (
        ('protagonist_drive', '主角驱动'),
        ('antagonist_logic', '反派逻辑'),
        ('supporting_roster', '配角复用'),
        ('relation_asymmetry', '关系不对称'),
        ('independent_side_ties', '配角独立线'),
        ('arc_conversion', '弧光代价'),
    ):
        if val := (spec.get('dimensions') or {}).get(dk):
            lines.append(f"- {zh}：{val}")
    for h in (spec.get('legacy_hints') or ())[:2]:
        lines.append(f"- 特殊机制：{h}")
    for fp in (spec.get('fingerprints') or ())[:2]:
        for t in (fp.get('techniques') or ())[:2]:
            lines.append(f"- 参考人物手法（{fp.get('title', '')}）：{t}")
    if spec.get('custom_notes'):
        lines.append(f"- 作者补充：{spec['custom_notes'][:140]}")
    for rl in (spec.get('anti_drift_redlines') or ())[:3]:
        lines.append(f"- 红线：{rl}")
    for mc in contrasts:
        lines.append(f"- 微对照[{mc.get('label', '')}] ❌{mc.get('bad_ai', '')[:65]} → ✅{mc.get('target_craft', '')[:85]}")
    return {
        'domain': 'cast',
        'base_id': spec.get('base_id', ''),
        'base_name': spec.get('base_name', ''),
        'sha256': spec.get('sha256', ''),
        'prompt_block': truncate_lines_to_budget(lines, max_chars),
    }


def build_relations_stage_packet(
    spec: dict[str, Any] | None,
    *,
    max_chars: int = 400,
) -> dict[str, Any] | None:
    """Compact relation asymmetry & side-cast autonomy slice for 05 `static_relations` (<=400 chars)."""
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    dims = spec.get('dimensions') or {}
    lines = [
        f"【关系张力标尺：{spec.get('base_name', '')}】",
        f"- 不对称布局：{dims.get('relation_asymmetry', '')}",
        f"- 配角独立线：{dims.get('independent_side_ties', '')}",
    ]
    for mc in (spec.get('micro_contrasts') or ()):
        if mc.get('target_function') == 'supporting_relation':
            lines.append(f"- 微对照 ❌{mc.get('bad_ai', '')[:55]} → ✅{mc.get('target_craft', '')[:85]}")
            break
    return {
        'domain': 'cast',
        'base_id': spec.get('base_id', ''),
        'sha256': spec.get('sha256', ''),
        'prompt_block': truncate_lines_to_budget(lines, max_chars),
    }


def build_review_cast_guard(spec: dict[str, Any] | None) -> str:
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return ''
    rls = [str(x).strip() for x in (spec.get('anti_drift_redlines') or ()) if str(x).strip()][:2]
    if not rls:
        return ''
    return f"【人物行为防漂移({spec.get('base_name', '')})】{'；'.join(rls)}"
