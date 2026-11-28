"""Executable Plot Engine, Length-Linked Pacing & Hook Specification Library (`plot_pacing_spec.json`).

Replaces vague structure/mechanism labels ("升级机制=通过修炼提升实力") and isolated word-count
numbers with:
  - 8 executable plot & pacing bases covering all 35 main genres (6 dimensions + anti-drift
    redlines + 3 plot-free ❌/✅ micro-contrasts each)
  - Deterministic 5-tier length-to-pacing compiler (`compute_scale_profile`) aligned with
    `nw.length_settings.WORD_TIERS` (30万/50万/100万/150万/200万字, 2000-2500字/章)
  - 4 orthogonal knobs (`pacing_speed`, `hook_style`, `payoff_ratio`, `plot_bans`)
  - Executable craft translations for all 15 `NARRATIVE_STRUCTURE_*` and 30 `PLOT_MECHANISM_*` IDs
  - Step-scoped packet builders: full card for 06 `plot_design` (<=1100 chars), compact slice for
    07/09 (<=340 chars), ultra-compact 2-3 line scene beat hint for 15 `writer` (<=150 chars),
    and same-source redlines for 16 `review`.
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

PLOT_SPEC_FILENAME = 'plot_pacing_spec.json'

PLOT_FUNCTION_LABELS: dict[str, str] = {
    'golden_three': '开篇与黄金三章',
    'chapter_split_rhythm': '卷章切分与重中轻节奏',
    'hook_aftermath': '章末真钩子与高潮余波',
}

PLOT_KNOBS: dict[str, dict[str, Any]] = {
    'pacing_speed': {
        'label': '推进速度与高潮密度',
        'multi': False,
        'options': [
            {
                'id': 'fast_punchy',
                'label': '疾走强推进（高频爆发）',
                'directive': '开篇即抛核心冲突，小高潮间隔压缩 20%，减少纯铺垫过渡章，每章必有可验证局势位移。',
            },
            {
                'id': 'steady_wave',
                'label': '稳健波浪递进（张弛交替）',
                'directive': '严格按重/中/轻章节奏交替波浪推进：蓄势有实操进度，爆发写足三拍，高潮后留半章消化与新局抬头。',
            },
            {
                'id': 'layered_build',
                'label': '蓄势厚积（长线深埋）',
                'directive': '允许在重大博弈或揭晓前用 2–3 章多方铺陈暗线与人物关系，但每章仍需交付至少 1 条新信息或筹码变化。',
            },
        ],
    },
    'hook_style': {
        'label': '章末主钩子形态',
        'multi': False,
        'options': [
            {
                'id': 'crisis_cliff',
                'label': '危机逼近与迫在眉睫抉择',
                'directive': '章尾优先停在退路收窄、时间截止或对手亮出硬筹码的具体瞬间，让读者追问“下一秒怎么接招”。',
            },
            {
                'id': 'reveal_twist',
                'label': '异常物证与认知翻盘',
                'directive': '章尾优先落在颠覆先前判断的具体细节或物证上，不替读者点破推论，留给读者自己倒吸一口凉气。',
            },
            {
                'id': 'payoff_anticipation',
                'label': '筹码到手与爽点预告',
                'directive': '章尾优先落在主角刚拿到新底牌/突破门槛并踏入下一个高利害赌局的瞬间，拉满下一章期待感。',
            },
            {
                'id': 'relation_shift',
                'label': '关系错位与情感悬念',
                'directive': '章尾优先落在信任裂痕、称呼变化、未说出口的真相或两人立场被迫对撞的微妙停顿上。',
            },
        ],
    },
    'payoff_ratio': {
        'label': '爽点与伏笔兑现配比',
        'multi': False,
        'options': [
            {
                'id': 'frequent_payoff',
                'label': '高频即时回馈（3–5章必见回报）',
                'directive': '主角每一次冒风险试错都在 3–5 章内见到实打实的筹码、地位或局势回报，绝不长憋屈无出口。',
            },
            {
                'id': 'balanced_arc',
                'label': '中波蓄力 + 卷末大结算',
                'directive': '日常保持小回报不断线，每 5–8 章一次中等破局结算，卷末集中回收本卷主伏笔并抬升格局。',
            },
            {
                'id': 'deep_foreshadow',
                'label': '深埋伏笔 + 延迟大反转',
                'directive': '伏笔允许跨越半卷至整卷休眠，但中间须有 1–2 次自然微提醒，反转揭晓时全部前置线索可严密回溯。',
            },
        ],
    },
    'plot_bans': {
        'label': '剧情与节奏防崩坏禁忌（可多选）',
        'multi': True,
        'options': [
            {
                'id': 'no_fake_cliffhanger',
                'label': '禁强行半句断章假钩子',
                'directive': '严禁在说话说一半或“门开了，来人竟然是——”处生硬断章；钩子必须来自完整节拍后的新局势。',
            },
            {
                'id': 'no_payoff_reset',
                'label': '禁赢完成果立刻清零',
                'directive': '严禁主角拼命赢下的资源、声望或关系突破，在下一段就被突降坏消息一键归零回到原点。',
            },
            {
                'id': 'no_filler_streak',
                'label': '禁连续三章同质水文',
                'directive': '严禁连续两章以上纯闲聊、纯跑路或重复同一冲突形态；每章必须改变信息、筹码、关系或危险度至少一项。',
            },
            {
                'id': 'no_deus_ex_machina',
                'label': '禁无铺垫机械降神反转',
                'directive': '严禁靠从未铺垫的巧合、神秘高人路过或临时加设定来解决死局，所有破局手段须有前文伏笔或代价依据。',
            },
            {
                'id': 'no_causal_inversion',
                'label': '禁跳过前驱完成门倒置因果',
                'directive': '严格遵守事件前驱完成条件（104.1），不得把前件尚未达成的后果提前当既定事实推进。',
            },
        ],
    },
}

_PLOT_KNOB_MAP = knob_option_map(PLOT_KNOBS)

PLOT_BASES: tuple[dict[str, Any], ...] = (
    {
        'id': 'PLOT_PRESSURE_BREAKTHROUGH',
        'name': '压迫蓄力—破局升级循环',
        'tagline': '门槛压迫→实操蓄筹码→当场破局反制→新阶层带来更高阻力',
        'recommended_genres': ('GENRE_XUANHUAN', 'GENRE_XIANXIA', 'GENRE_GAOWU', 'GENRE_WUXIA', 'GENRE_CHENGZHANG'),
        'incompatible_genres': ('GENRE_TUILI', 'GENRE_YANQING'),
        'default_knobs': {
            'pacing_speed': 'steady_wave',
            'hook_style': 'payoff_anticipation',
            'payoff_ratio': 'frequent_payoff',
            'plot_bans': ['no_fake_cliffhanger', 'no_payoff_reset', 'no_deus_ex_machina', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '每轮剧情由「眼前硬门槛/生存或尊严压迫 → 主角带缺陷手段试错攒筹码 → 关键赌局当场破局 → 收获改写地位并引出更高阶阻力」闭环驱动。',
            'golden_three': '第 1 章直接落进受压迫的窘境并亮出异常契机；第 2 章展示阻力与试错代价；第 3 章必须兑现第一次实打实的破局小回报与长期主线悬念。',
            'pacing_cadence': '压抑蓄力不超过 3 章必给可见回报；交手与突破属于重章给足篇幅，战后清账、整合收获与新格局露头用轻/中章承接。',
            'hook_contract': '优先回应上章遗留钩子，再把章末落在「新底牌刚到手撞上新试探」或「赌局落子后对手真实反扑」上。',
            'foreshadow_payoff': '金手指/传承/敌对暗手至少提前 2–8 章埋可见物证或异象，突破与反杀不靠临场空降新规则。',
            'aftermath_carry': '赢下来的战利品、身份变化或仇怨必须真实进入下一章筹码，绝不打完就忘或下一段被清零。',
        },
        'anti_drift_redlines': [
            '严禁连续三章只写“闭关修炼数值+1”或机械重复“换地图→被嘲讽→打脸”同质模板。',
            '严禁主角刚费尽代价突破或夺宝，下一段就被更强路人随便抢走或强制清零成果。',
            '严禁无前文铺垫的临阵悟道或神秘强者路过救场。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '黄金三章开篇推进',
                'bad_ai': '第1章介绍大陆九大宗门历史；第2章主角在杂役院被师兄嘲讽但忍气吞声；第3章主角睡觉时突然觉醒无敌系统。',
                'target_craft': '第1章杂役账目被栽赃三日后就要问斩，主角在废丹炉里摸到半块吸灵残骨；第2章借残骨试炼反吃掉一次灵气反噬并查清栽赃去向；第3章当堂用账目和残骨异象反咬执事脱险，同时惊动内门真正债主。',
                'why': '把倒计时危机、带代价的金手指试错、当场破局与牵出大局压进三章，零背景说明书。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '卷纲逐章切分与轻重轮换',
                'bad_ai': '第1章打外门弟子；第2章打执事；第3章打长老；第4章进秘境打妖兽（全员同质重章战斗）。',
                'target_craft': '第1章【中】查清规则漏洞拿到入场筹码；第2章【重】擂台受限条件逆转破局立威；第3章【轻】消化战利品、与盟友分账并发现旧账新线索；第4章【中】对手联盟改换规则围堵，逼主角另辟蹊径。',
                'why': '用重/中/轻章交替切换冲突类型（信息博弈/正面破局/关系消化/规则反制），彻底消灭疲劳感。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '章末真钩子与高潮余波',
                'bad_ai': '主角打赢比武拿到第一，正准备领奖，门外突然传来一声冷哼：“且慢！此子竟是——”（硬截断）。',
                'target_craft': '主角拿到甲等丹药和执事令牌，刚把旧账一笔勾销，盘点赏赐时却发现令牌内侧刻着失踪师父当年的私印——而发放令牌的正是下个月要带队进旧墟的副堂主。',
                'why': '先完整兑现胜利成果，再让成果本身带出新的具体线索与人物利害，读者自然想点下一章。',
            },
        ],
    },
    {
        'id': 'PLOT_CLUE_REVELATION',
        'name': '异常切入—线索博弈—反转重塑循环',
        'tagline': '具体异常抛钩→受限勘查与误导→物证对撞→真相颠覆前认知',
        'recommended_genres': ('GENRE_XUANYI', 'GENRE_TUILI', 'GENRE_JINGSONG', 'GENRE_LINGYI', 'GENRE_KONGBU'),
        'incompatible_genres': ('GENRE_GAOXIAO', 'GENRE_ZHONGDIAN'),
        'default_knobs': {
            'pacing_speed': 'steady_wave',
            'hook_style': 'reveal_twist',
            'payoff_ratio': 'deep_foreshadow',
            'plot_bans': ['no_fake_cliffhanger', 'no_filler_streak', 'no_deus_ex_machina', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '每轮剧情由「日常秩序出现精确物理异常 → 主角在信息残缺与时间压力下勘查/盘问 → 伪线索误导与嫌疑人反制 → 关键物证拼合颠覆先前假设并指向更深黑手」驱动。',
            'golden_three': '第 1 章必须抛出一件无法用常理解释的具体物证或异常事件；第 2 章展示首个看似合理的假解释被打破；第 3 章确立主角无法置身事外的切身风险与第一层真线索。',
            'pacing_cadence': '勘查取证（中）→ 逼近危机/审讯攻防（重）→ 复盘信息差发现新疑点（轻）严格交替，严禁连续纯会议室空谈推理。',
            'hook_contract': '章末优先落在「某条刚拿到的证据和之前某人说过的口供出现精确矛盾」，让读者自己察觉不对劲。',
            'foreshadow_payoff': '所有关键真相物证必须提前平淡埋在日常现场细节里（禁“他当时没多想”做记号），反转时 100% 可回溯。',
            'aftermath_carry': '每揭开一层小谜团必须真实改变人物信任关系或危险边界，同时撕开更大一层的动机追问。',
        },
        'anti_drift_redlines': [
            '严禁真相全靠凶手或知情者在结尾自爆长篇独白，或靠此前从未出场的新线索机械破案。',
            '严禁大纲提前剧透或把人物尚未证实的怀疑写成既定 WORLD 事实。',
            '严禁连续两章只有坐着聊天复盘而无现场行动与阻力反扑。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '悬疑开篇异常与切身绑定',
                'bad_ai': '第1章侦探介绍自己破案无数；第2章接到一起普通失踪案；第3章找到一张写着凶手名字的字条。',
                'target_craft': '第1章法医验收一具无名溺水尸体，发现死者口袋里的停车票时间竟比死亡鉴定晚了四小时；第2章调取停车场监控发现驾车离开的是死者本人，且车牌登记在主角失联三年的妹妹名下；第3章主角私查车库遭人灭口伏击，证实有人正在清理同一批目击者。',
                'why': '用精确时间矛盾立钩，迅速推翻表层假设并把主角切身利害死死锁进案件。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '悬疑信息差与行动交错',
                'bad_ai': '第1章盘问A；第2章盘问B；第3章盘问C；第4章主角突然想通真相。',
                'target_craft': '第1章【中】现场复勘发现与A口供矛盾的物证；第2章【重】二次对峙A却撞上证物被提前转移的危险突袭；第3章【轻】借外围旁证反推谁能拿到证物室权限；第4章【重】设局试探真凶露马脚，反引出案中案。',
                'why': '调查必然引发对手反制，让信息推进和现场危机咬合在一起。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '反转留白真钩子',
                'bad_ai': '他猛地瞪大眼睛，终于明白了真相：“原来凶手竟然是他！”（替读者说破且故弄玄虚）。',
                'target_craft': '化验报告发到手机上，毒物成分与十年前旧案完全一致。他顺手翻回昨晚拍下的证物照片，突然停在角落那只缺口茶杯上——那是刚才还坐在审讯室对面替他倒水的同事的私物。',
                'why': '摆出两个已经给出过的实证事实，让读者自己拼出寒意，不喊口号。',
            },
        ],
    },
    {
        'id': 'PLOT_FACTION_CHESS',
        'name': '立局试探—借势掀桌—格局洗牌循环',
        'tagline': '多方利益僵局→暗中换筹码试探→当场掀桌破局→各方反制洗牌',
        'recommended_genres': ('GENRE_QUANMOU', 'GENRE_LISHI', 'GENRE_SHANGZHAN', 'GENRE_JUNSHI'),
        'incompatible_genres': ('GENRE_ERCIYUAN', 'GENRE_QINGXIAOSHUO'),
        'default_knobs': {
            'pacing_speed': 'layered_build',
            'hook_style': 'crisis_cliff',
            'payoff_ratio': 'balanced_arc',
            'plot_bans': ['no_fake_cliffhanger', 'no_payoff_reset', 'no_deus_ex_machina', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '每轮剧情由「三方以上势力利益僵局 → 主角借信息/规则/人情杠杆暗中换筹码 → 关键议事或战役当场掀桌 → 利益重新切分并引发受损方联合反扑」驱动。',
            'golden_three': '第 1 章落进一场迫在眉睫的制度/财务/生死死局；第 2 章展示明面强敌与暗处潜在盟友的真实算盘；第 3 章主角用小筹码撬动第一次局部翻盘，暴露自身价值也招来真正大敌注视。',
            'pacing_cadence': '私下串连换筹码（中）→ 朝堂/商战/战场正面交锋（重）→ 战果落地与各方账本重算（轻），每步皆有实利流转。',
            'hook_contract': '章末优先落在「某方看似吃亏却悄悄递出新牌」或「期限逼近前最后一道防线突然松动」。',
            'foreshadow_payoff': '计谋成败全靠提前交待的规矩漏洞、人性私心与情报差，严禁事后靠主角复盘“其实我早料到了”硬圆。',
            'aftermath_carry': '每一局落子后，盟友未必永远可靠、败者仍握残余筹码，新局势自动长出下一轮博弈。',
        },
        'anti_drift_redlines': [
            '严禁全员降智配合主角演戏，或反派把明摆着的把柄主动送上门。',
            '严禁高潮过后用大段“主角向跟班讲解自己刚才如何算计”的复盘说明文拖字数。',
            '严禁只写抽象“双方斗智斗勇”，必须写清具体账目、兵力、票数、权限或时限筹码。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '权谋/商战死局破题',
                'bad_ai': '第1章介绍王朝三王夺嫡背景；第2章主角展示过目不忘的才华；第3章皇帝直接赏识提拔主角。',
                'target_craft': '第1章河工亏空案被推到主角这位新任小吏头上，五日内补不平就要抄家；第2章主角查账发现银子早进了两派大员私囊，找谁告状都是死；第3章主角故意放风给急缺军饷的兵部，借两派互咬在堂上保住性命，却从此被卷进盐铁大案漩涡。',
                'why': '用真实利益死局开场，主角靠借势而非皇帝降智赏识破局。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '博弈卷章多线推进',
                'bad_ai': '连续五章写主角不断想出妙计，反派不断中计跳脚。',
                'target_craft': '第1章【中】主角布下粮价试探局；第2章【重】对手识破半步反手切断漕运，主角方案受挫折损筹码；第3章【轻】稳住内部军心，从对手盟友的欠账里找到新切口；第4章【重】当堂甩出账册逼对手弃车保帅，格局彻底改写。',
                'why': '对手有真实反制与拆招，主角也会算漏吃亏，博弈才有惊心动魄的分量。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '洗牌后的新暗流钩子',
                'bad_ai': '主角大获全胜，众人佩服不已，但幕后黑手却阴冷地笑了：“游戏才刚刚开始。”',
                'target_craft': '新任巡盐御史的委任状落了红印，主角刚算清今年能多收三十万两税银，门房便递进一张匿名拜帖——发帖人正是刚才在朝堂上帮他投了赞成票的户部右侍郎，帖里只夹了一张十年前他父亲签押的旧盐引。',
                'why': '今日盟友手握明日把柄，利害瞬间反转，无需反派空喊“游戏开始”。',
            },
        ],
    },
    {
        'id': 'PLOT_GOAL_MISSION_LOOP',
        'name': '规则破题—阶梯结算—跨界递进循环',
        'tagline': '明面规则与时限任务→踩坑试错摸透隐藏条件→破题结算→更高难局',
        'recommended_genres': ('GENRE_YOUXI', 'GENRE_DIANJING', 'GENRE_ZHUTIAN', 'GENRE_KEHUAN', 'GENRE_SAIBO'),
        'incompatible_genres': ('GENRE_XIANSHI', 'GENRE_LISHI'),
        'default_knobs': {
            'pacing_speed': 'fast_punchy',
            'hook_style': 'payoff_anticipation',
            'payoff_ratio': 'frequent_payoff',
            'plot_bans': ['no_fake_cliffhanger', 'no_payoff_reset', 'no_deus_ex_machina', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '每轮剧情由「明确规则/赛制/副本任务 → 遭遇未明说陷阱或强敌机制 → 拆解底层逻辑反利用规则破题 → 透明结算奖励并解锁更高阶赛场或跨界后果」驱动。',
            'golden_three': '第 1 章立刻进入首个有清晰输赢规则与代价的局；第 2 章展示常规打法行不通的难点；第 3 章靠洞察机制破题拿下首胜与高价值结算。',
            'pacing_cadence': '入局探规则（中）→ 关键破题决胜（重）→ 场外结算、技能构筑与现实余波（轻），避免无休止连续刷本疲劳。',
            'hook_contract': '章末优先落在「新规则条目突然亮起反常限制」或「结算奖励里夹带出超出本轮认知的异常权限」。',
            'foreshadow_payoff': '破题用的机制漏洞或技能组合必须提前交代给读者，让读者拍案“原来还能这么用”，禁临时编新技能。',
            'aftermath_carry': '每轮结算获得的能力/装备/积分必须在下一轮有真实出场并改变打法，同时引发系统或现实层面的新注意。',
        },
        'anti_drift_redlines': [
            '严禁靠不断弹出大段冗长属性面板凑字数。',
            '严禁每个副本/比赛都完全割裂、结算收益对主线毫无长期积累。',
            '严禁临场给主角新开从未交代过的超模外挂强行过关。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '规则/副本开局破题',
                'bad_ai': '第1章花两千字列全套属性面板和系统介绍；第2章进副本一刀秒怪；第3章获得神器。',
                'target_craft': '第1章倒计时十分钟的封闭站台规则写着“禁止对检票员说谎”，已有两名玩家因答错当场出局；第2章主角发现提问本质是文字陷阱，拿自身残缺技能试出半条安全边界；第3章反利用规则把守门怪诱导进违规区间，拿下首轮隐藏结算却发现车票终点指向现实中的自己住所。',
                'why': '规则即时生效、破题靠脑子与实证、结算立刻和主线现实勾连。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '局内局外节奏切换',
                'bad_ai': '副本1刚出立刻传送副本2，副本2刚出立刻传送副本3，毫无喘息与主线推进。',
                'target_craft': '第1–2章【重】高难副本核心规则反转破题；第3章【轻】返回安全区透明结算、交易旧装备并发现同阵营玩家的异常记录；第4章【中】现实/安全区利益冲突爆发，决定下一局必须带上的新构筑与赌注。',
                'why': '局内紧张破题与局外结算博弈交替，既爽又有长线抓力。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '结算带出新悬念',
                'bad_ai': '叮！恭喜宿主完成任务，获得10000积分！敬请期待下一个世界！',
                'target_craft': '通关结算单滚到最后一行，除了应得的通行密钥，额外多出一行灰字：“已检测到现实锚点同步率 12%，下次强制征召将提前四十八小时。”而密钥编号恰好与失踪队友留下的旧怀表一致。',
                'why': '用结算结果的异常细节自然把爽感过渡成紧迫追读欲。',
            },
        ],
    },
    {
        'id': 'PLOT_RESOURCE_GROWTH',
        'name': '匮乏破局—经营积累—外部冲击循环',
        'tagline': '紧迫生存/资源缺口→实操改良换红利→红利引外部觊觎→规模升级',
        'recommended_genres': ('GENRE_ZHONGDIAN', 'GENRE_MOSHI', 'GENRE_WEILAI', 'GENRE_QIHUAN'),
        'incompatible_genres': ('GENRE_TUILI', 'GENRE_JINGSONG'),
        'default_knobs': {
            'pacing_speed': 'steady_wave',
            'hook_style': 'payoff_anticipation',
            'payoff_ratio': 'frequent_payoff',
            'plot_bans': ['no_fake_cliffhanger', 'no_payoff_reset', 'no_filler_streak', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '每轮剧情由「具体匮乏/断粮/负债/灾变缺口 → 主角拿具体工艺或资源置换赚出第一桶红利 → 红利切实改善吃穿与人手 → 丰饶引来同行打压/天灾/势力觊觎 → 被迫升级组织与防线」驱动。',
            'golden_three': '第 1 章落地具体困境（缺粮、破屋、濒死伤员或倒计时灾变）；第 2 章动手解决第一个眼前卡点并见实操阻力；第 3 章跑通首个看得见摸得着的增量收益与下一阶段盼头。',
            'pacing_cadence': '实操建设/改良（轻/中，写清关键卡点与成就感）与外部危机冲击（重）按 2:1 交替，既有过日子的满足感又不失大局紧张感。',
            'hook_contract': '章末优先落在「第一批成品/丰收刚落地，新的大买家或窥伺者已经找上门」。',
            'foreshadow_payoff': '季节气候、资源耗尽、周边势力动向提前数章种下征兆，让经营准备与危机来临严丝合缝。',
            'aftermath_carry': '建起的作坊、收编的工匠、修好的防线必须持续产出价值并成为后续章的真实据点，绝不写完即废弃。',
        },
        'anti_drift_redlines': [
            '严禁写成毫无波澜的流水账种田日记（每天早起浇水吃饭卖钱重复三章）。',
            '严禁靠凭空变出全套现代工业品碾压一切，必须尊重原料、工具、人手与工艺卡点。',
            '严禁辛辛苦苦建起的家业被无理由一把火烧光强行重来。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '经营/求生开篇实感与盼头',
                'bad_ai': '第1章穿越成穷书生；第2章想起来自己会做肥皂和玻璃；第3章立刻暴富成了首富。',
                'target_craft': '第1章冬雪封山前只剩半缸霉米，税吏还堵在院门要收三两丁银；第2章主角摸清村口碱滩和猪油来源，熬第一锅粗皂却因火候不对结块报废，差点赔光本钱；第3章改用滤灰法出成二十块去污皂，赶集换回冬粮和铁锅，却被镇上杂货行东家盯上断了原料路。',
                'why': '写清真实原料与失败试错，收益落地有温度，同时立刻长出新冲突。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '经营与外部冲击交替',
                'bad_ai': '连续四章分别写造纸、炼铁、酿酒、修路，没有任何外部阻力和人物关系变化。',
                'target_craft': '第1章【轻】新窑出砖改善营地保暖，收留两名手艺老匠；第2章【中】周边商队听闻风声抬价卡死燃料供应；第3章【重】寒潮提前夜袭，新防线扛住冲击并反吞对手逃散货车；第4章【中】清点战损与人手，定下开春扩建水渠的新目标。',
                'why': '每项基建成果都在下一次危机里真正派上用场，读者爽感扎实。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '红利落地引新局钩子',
                'bad_ai': '这一天大家吃得很开心，主角看着星空，心想明天一定会更好。',
                'target_craft': '第一批精盐装满六只木桶，全村头一回在腊月里闻见炖肉香味。主角刚把账本合上，哨塔的铁铃却急响了两声——官道尽头亮起一排火把，打的不是土匪的破旗，是州府盐运司的青灯。',
                'why': '把温热的成就感与紧逼而来的制度新考题并排摆在章尾，张力拉满。',
            },
        ],
    },
    {
        'id': 'PLOT_EMOTION_ESCALATION',
        'name': '处境错位—并肩破局—信任裂变循环',
        'tagline': '现实事件锁死交集→偏爱与误解交替拉扯→共担代价→关系不可逆升级',
        'recommended_genres': ('GENRE_YANQING', 'GENRE_QINGCHUN'),
        'incompatible_genres': ('GENRE_KONGBU', 'GENRE_MOSHI', 'GENRE_JUNSHI'),
        'default_knobs': {
            'pacing_speed': 'steady_wave',
            'hook_style': 'relation_shift',
            'payoff_ratio': 'balanced_arc',
            'plot_bans': ['no_fake_cliffhanger', 'no_filler_streak', 'no_deus_ex_machina', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '每轮剧情由「外部具体事件把两人绑在同一处境 → 各自防备/立场差产生微妙拉扯 → 共同扛过一次真实风险或偏爱实证 → 信任前进一步，同时更大一层旧伤或现实阻碍浮出水面」驱动。',
            'golden_three': '第 1 章用一件具体事务让双方产生带张力的第一交集（禁无聊偶遇撞怀）；第 2 章展示双方各自隐藏的顾虑与防线；第 3 章给一次微小却扎心的偏爱或互相兜底，确立非他/她不可的化学反应。',
            'pacing_cadence': '情感拉扯（中）→ 共同应对现实风波/关系摊牌（重）→ 细水长流偏爱余温（轻），避免无事硬吵或无铺垫发糖。',
            'hook_contract': '章末优先落在「某句没说穿的真心被对方捕捉到」「旧伤证据意外撞破」或「两人被迫在人前/私下做出倾向选择」。',
            'foreshadow_payoff': '人物心防来源、旧日误会或第三方阻力须通过具体物品、习惯与日常细节早早埋下，不临场硬编狗血绝症/失忆。',
            'aftermath_carry': '每一次关系推进（称呼变化、钥匙/底牌交付、公开护短）必须永久改写后续相处距离，严禁下章又莫名退回陌生人。',
        },
        'anti_drift_redlines': [
            '严禁全靠“长嘴不说一句话硬拖三十章误会”的降智狗血虐恋。',
            '严禁脱离现实事件与生活细节、干巴巴连写三章纯表白和空洞甜腻形容词。',
            '严禁关系升温后下一章毫无理由重置回冷冰冰初次见面状态。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '情感线高辨识开篇交集',
                'bad_ai': '第1章女主走路摔倒被霸总男主接住一见钟情；第2章发现男主是新老板；第3章男主强行壁咚。',
                'target_craft': '第1章竞标前夜核心报价单遭泄密，女主在茶水间撞见替对家审合同的男主——正是三年前不告而别的旧搭档；第2章两人在甲方面前各护其主针锋相对，私下却默契挡下同一桩栽赃；第3章项目被迫合并成立联合组，男主把当年留着缺口的旧工牌放回她桌角，留下“当年为什么撤资”的第一层真悬念。',
                'why': '用真实职场利益把两人锁死，旧情与现实立场交织，每场戏都自带拉扯。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '关系阶梯递进节奏',
                'bad_ai': '第1章发糖；第2章突然大吵分手；第3章莫名其妙和好；第4章继续发糖。',
                'target_craft': '第1章【轻】加班赶方案顺手照应，心防松动半寸；第2章【中】外部竞争方翻出旧案挑拨，双方试探彼此底线；第3章【重】危机当场不顾自身损失公开护短，把关系推上不可逆台阶；第4章【轻】事后独处卸下礼貌称呼，却触到更深一层家庭现实阻力。',
                'why': '情感位移每一步都由实打实的选择与代价托住，真挚动人。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '关系位移真钩子',
                'bad_ai': '他深情地望着她的背影，发誓一定要追回她。',
                'target_craft': '她把多备的一份胃药推过去，顺口喊出了三年前才叫过的那个小名。话出口两人都愣了半秒，他没有拆穿，只慢慢把药盒攥进掌心，抬眼问她：“那封我托人转交给你的信，你到底拆过没有？”',
                'why': '用称呼失守引爆积压已久的关键信息差，读者立刻想知道下一句答复。',
            },
        ],
    },
    {
        'id': 'PLOT_EPISODIC_ARC',
        'name': '单元闭环 + 暗藏主线暗流循环',
        'tagline': '每3–8章完成一个爽利可读的独立单元，同时悄然推动人物关系与主线暗流',
        'recommended_genres': ('GENRE_QINGXIAOSHUO', 'GENRE_DUSHI', 'GENRE_ZHIYE', 'GENRE_XIANSHI', 'GENRE_GAOXIAO', 'GENRE_ERCIYUAN', 'GENRE_TONGREN', 'GENRE_TIYU'),
        'incompatible_genres': ('GENRE_QUANMOU',),
        'default_knobs': {
            'pacing_speed': 'fast_punchy',
            'hook_style': 'payoff_anticipation',
            'payoff_ratio': 'frequent_payoff',
            'plot_bans': ['no_fake_cliffhanger', 'no_filler_streak', 'no_deus_ex_machina', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '每 3–8 章围绕一个独立委托/比赛/日常事件/行业难题完成起承转合闭环，单元解决后必留下至少 1 项带入后续的人脉、名声或主线暗线碎片。',
            'golden_three': '第 1 章用高辨识度小事件立住主角性格与特殊手段；第 2 章把小事件里的反差趣味或真实棘手处写透；第 3 章漂亮收束首单元并顺带勾出更大主线/常驻配角圈。',
            'pacing_cadence': '单元起势（中）→ 单元核心反转/破题（重）→ 日常吐槽余味与主线暗子露头（轻），节奏轻快不拖泥带水。',
            'hook_contract': '单元内章末用眼前小局的变数拉住阅读；单元尾章必须自然抛出下一单元委托或主线暗流异动。',
            'foreshadow_payoff': '前几个看似无关的小单元里藏入同一条暗线线索，中盘串联引爆时给读者“草蛇灰线”的惊喜。',
            'aftermath_carry': '前单元结识的配角、口碑或后遗症在后续单元反复客串发力，形成活生生的常驻世界感。',
        },
        'anti_drift_redlines': [
            '严禁单元之间完全零关联、写完像十篇互不相干的短篇拼盘。',
            '严禁为了追求轻松日常而让章节失去目标与冲突，写成流水账吃饭逛街。',
            '严禁单个琐碎小事硬水超过 10 章迟迟不收口。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '都市/日常/轻小说单元开局',
                'bad_ai': '第1章主角起床上班吐槽老板；第2章下班吃饭看手机；第3章还是没发生任何推进。',
                'target_craft': '第1章二手修复店刚贴出停业告示，陌生老太就拎着一只刻着诡异铭文的坏怀表砸了两万定金要求今晚修好；第2章拆机发现表芯里藏着三十年前的当票，引来两拨人上门抢买；第3章主角用修表手艺和合同条款化解刁难赚下房租，却在当票背面认出失踪祖父的字迹。',
                'why': '首个小单元三章内爽利闭环，同时把长期主线暗钩自然埋好。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '单元串联主线暗流',
                'bad_ai': '每个单元都是新委托人出场→解决→永不再出现，主线原地踏步。',
                'target_craft': '单元一【1–4章】修坏怀表结识古玩线人，得线索碎片A；单元二【5–9章】借线人牵线接手拍卖会赝品案，表面赚名声，暗里发现碎片B与碎片A指向同一家旧典当行；单元三【10–15章】两案当事人交叉登场，主线浮出水面。',
                'why': '单元各自独立好看，串起来又能把长篇格局越滚越大。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '轻快单元尾钩',
                'bad_ai': '委托完美结束，主角数着钞票开心地睡着了。',
                'target_craft': '尾款到账提示响起，主角刚把卷帘门拉下一半，门缝外却塞进来一只印着市局徽章的牛皮纸袋——上个单元刚帮过忙的老警察在便签上潦草写了六个字：“别收今晚的急单。”话音未落，门口停下一辆熄了灯的黑车。',
                'why': '前单元配角自然反哺，两句话丝滑把读者拽进下一单元。',
            },
        ],
    },
    {
        'id': 'PLOT_HYBRID_BALANCED',
        'name': '全能稳健推进循环',
        'tagline': '兼顾开篇抓力、重中轻节奏轮换与多题材融合主副分工',
        'recommended_genres': (),
        'incompatible_genres': (),
        'default_knobs': {
            'pacing_speed': 'steady_wave',
            'hook_style': 'crisis_cliff',
            'payoff_ratio': 'balanced_arc',
            'plot_bans': ['no_fake_cliffhanger', 'no_payoff_reset', 'no_filler_streak', 'no_causal_inversion'],
        },
        'dimensions': {
            'drive_loop': '主类型冲突负责核心主线推进，副类型元素负责提供独特阻力或情感/爽感调剂；每轮确保“目标受阻→代价试错→局势位移→新矛盾抬头”。',
            'golden_three': '前 3 章快速立住主角当下处境、核心矛盾与读者长期期待，兑现至少一次明确的小回报或悬念升级。',
            'pacing_cadence': '严格落实篇幅档位对应的重/中/轻章交替与卷级高潮梯度，不前松后紧也不前紧后崩。',
            'hook_contract': '先承接回应上章遗留钩子，再在章尾落在具体未了事态或刚露头的新变量上。',
            'foreshadow_payoff': '伏笔维护清晰埋设—休眠—回收周期，全书伏笔兑现率不低于 80%，所有反转可回溯。',
            'aftermath_carry': '重大事件与高潮后必须留出可见余波，让主角的赢与输都真实改写后续处境。',
        },
        'anti_drift_redlines': [
            '严禁多题材融合时主副线互相抢戏、前十章悬疑后十章莫名变成纯谈恋爱。',
            '严禁为水字数在原地打转，每章须交付具体信息、筹码、关系或局势变化。',
            '严禁硬截半句话充当章末钩子，或刚赢成果立刻清零。',
        ],
        'micro_contrasts': [
            {
                'target_function': 'golden_three',
                'label': '多题材融合主副清晰开局',
                'bad_ai': '第1章写大段世界设定；第2章写无关感情戏；第3章主角还没确定要做什么。',
                'target_craft': '第1章以主类型紧迫冲突切入现场，主角当场被逼接下烫手目标；第2章带入副类型独特阻力与核心搭档；第3章靠双方磨合破掉第一道小关，同时揭出贯穿全卷的主悬念。',
                'why': '主线领跑、副线赋能，三章内读者立刻明白这本书的独特卖点。',
            },
            {
                'target_function': 'chapter_split_rhythm',
                'label': '按篇幅节奏排布轻重章',
                'bad_ai': '每章任务描述都写成“主角继续推进调查/继续修炼，遇到一点困难后解决”。',
                'target_craft': '逐章写明本章节拍定位（重/中/轻）、核心要改变的唯一局势项、前置承接点与交接给下章的具体新问题。',
                'why': '每章都有不可替代的推进功能，彻底避免大纲同质化。',
            },
            {
                'target_function': 'hook_aftermath',
                'label': '成果落地接新局',
                'bad_ai': '事情解决了，但主角总觉得事情没那么简单，心里隐隐感到不安。',
                'target_craft': '协议签完、眼前的危局暂解，他低头核对对方归还的旧账盒，却发现最底层的封蜡是今晚刚重烫过的——有人比他们早半个时辰动过里面的东西。',
                'why': '用具体物理异常替代“隐隐感到不安”的空洞旁白。',
            },
        ],
    },
)

PLOT_BASE_MAP: dict[str, dict[str, Any]] = {b['id']: b for b in PLOT_BASES}

# Executable directives upgrading all 15 NARRATIVE_STRUCTURE_* & 23+ PLOT_MECHANISM_* legacy IDs.
STRUCTURE_EXECUTION_HINTS: dict[str, str] = {
    'NARRATIVE_STRUCTURE_LINEAR': '线性推进：严格按事件因果顺时推进，把悬念藏在“即将发生什么”而非故意打乱时间线。',
    'NARRATIVE_STRUCTURE_NONLINEAR': '非线性插叙：每次闪回/插叙必须标明原时点、触发物与回主线接点，且必须当场改变读者对当前局面的判断。',
    'NARRATIVE_STRUCTURE_MULTI_POV': '多视角交错：每个 POV 必须承担独立信息线与不可替代视角，严守各自知情边界，切换处给出明确时空定位。',
    'NARRATIVE_STRUCTURE_SINGLE_POV': '单视角深潜：全程紧贴单一主角见闻，其他势力的动向只能通过主角目击、听闻、结果残痕和对手漏嘴渗入。',
    'NARRATIVE_STRUCTURE_EPISODIC': '单元剧闭环：每单元 3–8 章爽利收口，但单元结果必须持续累积人脉、名声或主线暗线碎片。',
    'NARRATIVE_STRUCTURE_SERIAL': '连续剧紧扣：章与章首尾咬合，优先回应上章钩子，让前章代价直接成为下章阻力。',
    'NARRATIVE_STRUCTURE_ARC': '篇章分卷梯度：每卷围绕一个完整核心矛盾与舞台展开，卷末必须有不可逆的格局跃迁。',
    'NARRATIVE_STRUCTURE_LEVEL': '升级阶梯控通胀：每次等阶/地位跃升必须对应具体瓶颈、实打实代价与新阶层的新对手，严禁无脑跳级。',
    'NARRATIVE_STRUCTURE_QUEST': '任务驱动链：每个任务写清完成判据、失败惩罚与时限，完成前件才解锁后继任务（守住完成门）。',
    'NARRATIVE_STRUCTURE_EPIC': '宏阔史诗视野：大时代变动与个体具体抉择互相咬合，分阶段扩展地域与势力版图而非开篇全盘托出。',
    'NARRATIVE_STRUCTURE_GROUP': '群像交织：核心人物线各自独立推进并在关键事件交汇碰撞，防某一条线长期掉线或沦为工具人。',
    'NARRATIVE_STRUCTURE_LOOP': '时间循环差异化：每一轮循环必须有明确的新信息增量或变量改写，绝不原样重演上一轮过程。',
    'NARRATIVE_STRUCTURE_FRAME': '框架嵌套：明确外层框架与内层故事的呼应关系和返回节点，内层进展必须反过来改变外层局势。',
    'NARRATIVE_STRUCTURE_STREAM': '意识流动克制：心理联想要紧扣眼前感官触发物与具体处境推进，不脱离主线漂浮空想。',
    'NARRATIVE_STRUCTURE_CHRONICLE': '编年坐标推进：以清晰时间节点串联跨年/跨季大势变化，每次时间跳跃必须交待期间积累的可见后果。',
}

PLOT_MECHANISM_EXECUTION_HINTS: dict[str, str] = {
    'PLOT_MECHANISM_UPGRADE': '升级推进：明确当前所处阶段、突破缺口与试错代价，每次变强必须有实战或局势实证。',
    'PLOT_MECHANISM_INFINITE': '无限流副本：每轮世界规则清晰、结算透明，副本收获必须带回主空间改写长期处境。',
    'PLOT_MECHANISM_FAST_TRANSMIGRATION': '快穿高密度：单世界 10–25 章利落破局并立刻兑现高情绪爽点，同时保留贯穿所有世界的总主线。',
    'PLOT_MECHANISM_UNDERDOG': '逆袭破局：弱势起点必须真实有痛感，翻盘靠信息差、苦功、筹码或机制利用，严禁全靠对手降智。',
    'PLOT_MECHANISM_MYSTERY': '解谜递进：把真实线索混入日常细节，每解开一层小谜须引出更深一层动机追问。',
    'PLOT_MECHANISM_INVESTIGATION': '探案实证：靠物证、时间线、口供矛盾与现场反推推进，盘问攻防要有对手防线与反制。',
    'PLOT_MECHANISM_POLITICAL': '权谋博弈：写清权责、财税、把柄与多方算盘，借势与制衡皆须合乎制度逻辑。',
    'PLOT_MECHANISM_WAR': '战争谋划：落到粮草、地形、士气、情报与局部战役抉择，拒绝几句口号就全军溃败。',
    'PLOT_MECHANISM_MANAGEMENT': '经营壮大：写清资金/人力/渠道卡点与改良红利，繁荣后引来同行或外部势力博弈。',
    'PLOT_MECHANISM_FARMING': '种田积累：尊重农时、原料与工具限制，用看得见的吃穿改善与家园成长提供扎实满足感。',
    'PLOT_MECHANISM_TRADE': '商业博弈：围绕供需差、定价权、信用与资金链设计交锋，每一笔输赢落到真金白银后果。',
    'PLOT_MECHANISM_ROMANCE': '情感演进：靠具体事件中的偏爱、误解、并肩与取舍递进，称呼与距离变化不可逆。',
    'PLOT_MECHANISM_REVENGE': '复仇主线：明确仇敌格局与主角筹码差距，每一步反击带来实打实斩获也付出真实代价。',
    'PLOT_MECHANISM_GROWTH': '成长实证：用主角前后面对相似困局时截然不同的判断与出手方式证明真正的蜕变。',
    'PLOT_MECHANISM_COMPETITION': '竞技赛制：赛前备战针对弱点、赛中写清战术拆招与体能心理博弈、赛后兑现排名与格局变化。',
    'PLOT_MECHANISM_GAME': '游戏冒险：数值与机制服务于策略破题而非堆面板，探索未知地图兼顾风险与收益。',
    'PLOT_MECHANISM_CIVILIZATION': '文明演化：技术/制度突破引发社会结构连锁反应与旧势力反弹，以小人物命运映出时代巨变。',
    'PLOT_MECHANISM_APOCALYPSE': '末世求生：物资稀缺、环境恶化与人性秩序崩塌三重施压，避难所建设与外部掠夺交替推进。',
    'PLOT_MECHANISM_DYSTOPIA': '反乌托邦反抗：写透高压秩序的精密运转与个人代价，反抗靠微小裂缝层层撕开而非一呼百应。',
    'PLOT_MECHANISM_SPACE': '太空探索：尊重航程、补给、通信延迟与真空物理约束，在孤绝环境里放大未知压迫。',
    'PLOT_MECHANISM_STAR': '星际博弈：兼顾星域补给、舰队/技术代差与多文明外交利害，以关键战役撬动全局。',
    'PLOT_MECHANISM_PLANET': '星球开发：从勘探、生态适应、资源开采到殖民利益冲突层层推进，尊重异星环境反噬。',
    'PLOT_MECHANISM_MULTI_WORLD': '多世界穿梭：明确两界通行门槛、时间比例与资源价差，利用两界信息/物产互补制造核心爽点。',
}


def compute_scale_profile(
    target_words: int | None,
    *,
    pacing_speed: str = 'steady_wave',
) -> dict[str, Any]:
    """Deterministically compile length tier (from length_settings.WORD_TIERS) into executable pacing rules."""
    tw = int(target_words) if isinstance(target_words, int) and target_words > 0 else None
    if tw is None:
        base = {
            'tier_label': '待定档（默认按 50–100 万字网文节奏起盘）',
            'target_words': None,
            'estimated_chapters': '约 220–450 章（单章 2,000–2,500 字）',
            'recommended_volumes': '3–6 卷（每卷 60–80 章）',
            'small_climax_every_chapters': [5, 8],
            'major_arc_every_chapters': [55, 75],
            'chapter_weight_ratio': '重3 : 中4 : 轻2 : 过渡1',
            'golden_three_target': '第 1 章入核心冲突，第 3 章前兑现首个可见小爽点/反转并立长期主线钩',
            'stage_escalation_rule': '批准书纲定档后自动重算精准卷数与阶梯梯度；前卷严禁透支全书天花板。',
        }
    elif tw <= 35_000:
        base = {
            'tier_id': 'micro_short',
            'tier_label': '0.5–3 万字短篇快变现档（知乎盐言 / 番茄短故事）',
            'target_words': tw,
            'estimated_chapters': '约 4–10 节（单节 1,500–3,500 字，全文一次完结投稿）',
            'recommended_volumes': '1 卷短篇闭环（免多卷冗余）',
            'small_climax_every_chapters': [1, 2],
            'major_arc_every_chapters': [4, 10],
            'chapter_weight_ratio': '重6 : 中4 : 轻0 : 过渡0',
            'golden_three_target': '前 300–500 字抛强导语钩子（可用……分隔进正文），约 2,500–4,000 字处埋免转付付费卡点，每 3,000 字一次反转直至爽快闭环',
            'stage_escalation_rule': '零冗余铺垫，单主线极致情绪推进，跳过多卷世界观科普，结尾干脆收束并反杀闭环。',
        }
    elif tw <= 399_999:
        base = {
            'tier_label': '30 万字紧凑档',
            'target_words': tw,
            'estimated_chapters': '约 120–160 章（单章 2,000–2,500 字）',
            'recommended_volumes': '2–3 卷（每卷 45–65 章）',
            'small_climax_every_chapters': [4, 6],
            'major_arc_every_chapters': [40, 55],
            'chapter_weight_ratio': '重4 : 中4 : 轻2 : 过渡0',
            'golden_three_target': '第 1 章直入主线危机，第 3 章前完成首轮破局与核心悬念立锚，零冗余开场',
            'stage_escalation_rule': '单主线高密度收束，伏笔控制在 3–15 章内密集兑现，严禁横向开无关新地图支线。',
        }
    elif tw <= 749_999:
        base = {
            'tier_label': '50 万字中长篇档',
            'target_words': tw,
            'estimated_chapters': '约 200–280 章（单章 2,000–2,500 字）',
            'recommended_volumes': '3–4 卷（每卷 55–75 章）',
            'small_climax_every_chapters': [5, 8],
            'major_arc_every_chapters': [50, 70],
            'chapter_weight_ratio': '重3 : 中5 : 轻2 : 过渡0',
            'golden_three_target': '黄金三章兑现首个实打实破局并埋下本卷主悬念',
            'stage_escalation_rule': '每卷完成一次舞台/敌手升级；短伏笔 3–10 章兑现，卷伏笔本卷必结。',
        }
    elif tw <= 1_249_999:
        base = {
            'tier_label': '100 万字标准长篇档',
            'target_words': tw,
            'estimated_chapters': '约 400–500 章（单章 2,000–2,500 字）',
            'recommended_volumes': '5–7 卷（每卷 65–85 章）',
            'small_climax_every_chapters': [6, 10],
            'major_arc_every_chapters': [65, 85],
            'chapter_weight_ratio': '重3 : 中4 : 轻2 : 过渡1',
            'golden_three_target': '黄金三章强抓力起势 + 首卷前 15 章确立稳定追读循环',
            'stage_escalation_rule': '至少规划 3 级舞台/力量/格局阶梯，严禁前两卷透支战力或悬念天花板。',
        }
    else:
        tier_name = '200 万字超长篇档' if tw >= 1_750_000 else '150 万字大长篇档'
        base = {
            'tier_label': tier_name,
            'target_words': tw,
            'estimated_chapters': '约 650–900 章（单章 2,000–2,500 字）',
            'recommended_volumes': '8–12 卷（每卷 70–95 章）',
            'small_climax_every_chapters': [8, 12],
            'major_arc_every_chapters': [75, 95],
            'chapter_weight_ratio': '重3 : 中4 : 轻2 : 过渡1',
            'golden_three_target': '黄金三章即时兑现首波抓力，同时暗埋跨卷长期终极悬念',
            'stage_escalation_rule': '强制卷间推进世界时钟与配角阶梯退场/复现；伏笔按短线(3-8章)/中线(半卷)/长线(跨卷)分账管理。',
        }

    lo, hi = base['small_climax_every_chapters']
    if pacing_speed == 'fast_punchy':
        base['small_climax_every_chapters'] = [max(3, lo - 1), max(4, hi - 2)]
        base['speed_adjustment'] = '疾走加速：小高潮间隔收紧，减少纯过渡章。'
    elif pacing_speed == 'layered_build':
        base['small_climax_every_chapters'] = [lo + 1, hi + 2]
        base['speed_adjustment'] = '蓄势厚积：允许更厚的多线铺陈，但单章仍须交付有效信息或筹码推进。'
    else:
        base['speed_adjustment'] = '稳健波浪：保持标准重/中/轻章交替与蓄势爆发节奏。'
    return base


def recommend_plot_bases(types: list[str] | tuple[str, ...] | None) -> list[dict[str, Any]]:
    return rank_bases_for_genres(PLOT_BASES, types, fallback_id='PLOT_HYBRID_BALANCED')


def default_plot_base_id(types: list[str] | tuple[str, ...] | None) -> str:
    ranked = recommend_plot_bases(types)
    return ranked[0]['id'] if ranked else 'PLOT_HYBRID_BALANCED'


def compile_plot_pacing_spec(
    genre_ids: list[str] | tuple[str, ...],
    *,
    base_id: str | None = None,
    target_words: int | None = None,
    knobs: dict[str, Any] | None = None,
    structure_ids: list[str] | tuple[str, ...] = (),
    mechanism_ids: list[str] | tuple[str, ...] = (),
    fingerprints: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    custom_notes: str = '',
    enabled: bool = True,
) -> dict[str, Any]:
    """Compile a single unified, length-linked Book Plot & Pacing Spec (`plot_pacing_spec.json`)."""
    norm_genres = canonical_types(list(genre_ids)) if genre_ids else []
    bid = base_id if (base_id and base_id in PLOT_BASE_MAP) else default_plot_base_id(norm_genres)
    base = PLOT_BASE_MAP[bid]
    norm_knobs = normalize_spec_knobs(PLOT_KNOBS, knobs, base['default_knobs'])
    scale = compute_scale_profile(target_words, pacing_speed=norm_knobs['pacing_speed'])

    dims = dict(base['dimensions'])
    speed_opt = _PLOT_KNOB_MAP['pacing_speed'].get(norm_knobs['pacing_speed'])
    hook_opt = _PLOT_KNOB_MAP['hook_style'].get(norm_knobs['hook_style'])
    payoff_opt = _PLOT_KNOB_MAP['payoff_ratio'].get(norm_knobs['payoff_ratio'])
    if speed_opt:
        dims['pacing_cadence'] = (
            f"【{scale['tier_label']}｜小高潮每{scale['small_climax_every_chapters'][0]}–{scale['small_climax_every_chapters'][1]}章"
            f"｜配比{scale['chapter_weight_ratio']}】{speed_opt['directive']}"
        )
    if hook_opt:
        dims['hook_contract'] = f"【{hook_opt['label']}】{hook_opt['directive']} 并且优先回应上章遗留钩子。"
    if payoff_opt:
        dims['foreshadow_payoff'] = f"【{payoff_opt['label']}】{payoff_opt['directive']}"

    redlines: list[str] = list(base['anti_drift_redlines'])
    for ban_id in norm_knobs.get('plot_bans', ()):
        ban_opt = _PLOT_KNOB_MAP['plot_bans'].get(ban_id)
        if ban_opt and ban_opt['directive'] not in redlines:
            redlines.append(ban_opt['directive'])

    legacy_hints: list[str] = []
    for sid in structure_ids:
        if h := STRUCTURE_EXECUTION_HINTS.get(str(sid)):
            legacy_hints.append(h)
    for mid in mechanism_ids:
        if h := PLOT_MECHANISM_EXECUTION_HINTS.get(str(mid)):
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
            'title': fp.get('title', '参考剧情节奏指纹'),
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
        'domain': 'plot_pacing',
        'enabled': bool(enabled),
        'genre_ids': norm_genres,
        'base_id': bid,
        'base_name': base['name'],
        'tagline': base['tagline'],
        'scale_profile': scale,
        'knobs': norm_knobs,
        'dimensions': dims,
        'anti_drift_redlines': redlines[:10],
        'micro_contrasts': deepcopy(base['micro_contrasts']),
        'legacy_hints': legacy_hints[:8],
        'fingerprint_ids': [fp['id'] for fp in accepted_fps if fp.get('id')],
        'fingerprints': accepted_fps,
        'custom_notes': str(custom_notes or '').strip()[:800],
    }
    return finalize_spec_payload(spec)


def load_plot_pacing_spec(store: Store) -> dict[str, Any] | None:
    return load_spec_file(store, PLOT_SPEC_FILENAME)


def save_plot_pacing_spec(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    return save_spec_file(store, PLOT_SPEC_FILENAME, spec)


def build_plot_stage_packet(
    spec: dict[str, Any] | None,
    *,
    scope: str = 'book',
    max_chars: int = 1100,
) -> dict[str, Any] | None:
    """Build bounded craft guidance for 06 `plot_design` (book/volume/chapter)."""
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    scale = spec.get('scale_profile') or {}
    preferred_fn = {
        'book': ('golden_three', 'chapter_split_rhythm'),
        'volume': ('chapter_split_rhythm', 'hook_aftermath'),
        'chapter': ('hook_aftermath', 'chapter_split_rhythm'),
    }.get(scope, ('golden_three', 'hook_aftermath'))
    contrasts = sorted(
        list(spec.get('micro_contrasts') or ()),
        key=lambda r: (0 if r.get('target_function') in preferred_fn else 1),
    )[:2]

    lines = [
        f"【剧情引擎与节奏基座：{spec.get('base_name', '')}】{PRIORITY_ARBITRATION_NOTE}",
        f"篇幅节奏标尺：{scale.get('tier_label', '')}｜{scale.get('recommended_volumes', '')}｜"
        f"小高潮每{'–'.join(str(x) for x in scale.get('small_climax_every_chapters', [5, 8]))}章｜"
        f"配比{scale.get('chapter_weight_ratio', '')}。{scale.get('stage_escalation_rule', '')}",
    ]
    dim_labels = (
        ('drive_loop', '驱动循环'),
        ('golden_three', '黄金三章'),
        ('pacing_cadence', '节奏密度'),
        ('hook_contract', '钩子纪律'),
        ('foreshadow_payoff', '伏笔兑现'),
        ('aftermath_carry', '余波承接'),
    )
    for dk, zh in dim_labels:
        if val := (spec.get('dimensions') or {}).get(dk):
            lines.append(f"- {zh}：{val}")
    for hint in (spec.get('legacy_hints') or ())[:3]:
        lines.append(f"- 专项结构/机制：{hint}")
    for fp in (spec.get('fingerprints') or ())[:2]:
        for t in (fp.get('techniques') or ())[:2]:
            lines.append(f"- 参考节奏手法（{fp.get('title', '')}）：{t}")
    if spec.get('custom_notes'):
        lines.append(f"- 作者补充：{spec['custom_notes'][:160]}")
    for rl in (spec.get('anti_drift_redlines') or ())[:4]:
        lines.append(f"- 红线：{rl}")
    for mc in contrasts:
        lines.append(f"- 微对照[{mc.get('label', '')}] ❌{mc.get('bad_ai', '')[:75]} → ✅{mc.get('target_craft', '')[:95]}")

    return {
        'domain': 'plot_pacing',
        'base_id': spec.get('base_id', ''),
        'base_name': spec.get('base_name', ''),
        'sha256': spec.get('sha256', ''),
        'scale_profile': scale,
        'prompt_block': truncate_lines_to_budget(lines, max_chars),
    }


def build_event_scene_pacing_packet(
    spec: dict[str, Any] | None,
    *,
    max_chars: int = 340,
) -> dict[str, Any] | None:
    """Compact pacing & hook slice for 07 `event_design` and 09 `scene_design`."""
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    dims = spec.get('dimensions') or {}
    lines = [
        f"【剧情与钩子标尺：{spec.get('base_name', '')}】",
        f"- 推进循环：{dims.get('drive_loop', '')}",
        f"- 钩子要求：{dims.get('hook_contract', '')}",
        f"- 余波承接：{dims.get('aftermath_carry', '')}",
    ]
    if rls := (spec.get('anti_drift_redlines') or ())[:2]:
        lines.append(f"- 禁忌：{'；'.join(rls)}")
    lines.append('- 信号与剧透边界：普通场景卡只写角色当下可见的异常信号，不提前把后期大反转底牌剧透给写手。')
    return {
        'domain': 'plot_pacing',
        'base_id': spec.get('base_id', ''),
        'sha256': spec.get('sha256', ''),
        'prompt_block': truncate_lines_to_budget(lines, max_chars),
    }


def build_writer_scene_beat_hint(
    spec: dict[str, Any] | None,
    scene_body: dict[str, Any] | None,
    *,
    chapter_index: int = 1,
    scene_index: int = 1,
    is_chapter_end: bool = False,
) -> dict[str, Any] | None:
    """Ultra-compact 2-3 line scene beat & hook cue (<=150 chars) for 15 `writer`.

    Never dumps macro outlining rules into Step 15!
    """
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    knobs = spec.get('knobs') or {}
    hook_opt = _PLOT_KNOB_MAP['hook_style'].get(knobs.get('hook_style', ''))
    speed_opt = _PLOT_KNOB_MAP['pacing_speed'].get(knobs.get('pacing_speed', ''))
    body = scene_body if isinstance(scene_body, dict) else {}
    text = ' '.join(str(body.get(k) or '') for k in ('title', 'goal', 'conflict', 'summary'))
    beat_weight = (
        '重拍（冲突/破局写足过程与后果）'
        if any(w in text for w in ('冲突', '决战', '对峙', '揭晓', '反转', '杀', '破局', '交锋', '摊牌'))
        else ('轻拍（人物呼吸与暗线渗入，不拖水）' if any(w in text for w in ('日常', '休息', '整理', '商议', '谈话'))
              else '中拍（稳推处境变化，交付明确增量）')
    )
    lines = [
        f"本场节拍：{beat_weight}（{speed_opt['label'] if speed_opt else spec.get('base_name', '')}）",
    ]
    if chapter_index <= 3 and scene_index == 1:
        lines.append('黄金三章起势：直接进眼前受阻处境与异常，零背景说明书。')
    if is_chapter_end:
        from nw.expansion_advisor import recommend_chapter_opener_and_hook
        scale_id = str((spec.get('scale_profile') or {}).get('tier_id') or 'long')
        rec = recommend_chapter_opener_and_hook(chapter_index, scale=scale_id)
        hk_label = hook_opt['label'] if hook_opt else rec['hook']['name']
        lines.append(f'章尾落点：{hk_label}/{rec["hook"]["name"]}（强度{rec["wave_intensity"]}/5）——完整收束后独立短段留钩，禁半句硬断。')
    else:
        lines.append('离场承接：带着本场真实得失与未了压力顺畅转入下场。')
    return {
        'base_id': spec.get('base_id', ''),
        'sha256': spec.get('sha256', ''),
        'beat_hint': truncate_lines_to_budget(lines, 150),
        'review_redlines': list(spec.get('anti_drift_redlines') or ())[:3],
    }


def build_review_plot_guard(spec: dict[str, Any] | None) -> str:
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return ''
    rls = [str(x).strip() for x in (spec.get('anti_drift_redlines') or ()) if str(x).strip()][:3]
    if not rls:
        return ''
    return f"【剧情节奏防漂移({spec.get('base_name', '')})】{'；'.join(rls)}"
