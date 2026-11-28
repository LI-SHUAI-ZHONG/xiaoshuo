"""Verified 2025-2026 Chinese Web-Novel Monetization & Chart Rulebooks (Single Source of Truth).

Covers the 6 highest-traffic, clearest-monetization web-novel platforms for authors:
  1. `fanqie`       — 番茄小说（含番茄短故事）: #1 free ad/audio-share + short-drama ecosystem
  2. `qidian`       — 起点中文网（阅文男频）: #1 paid subscription + IP ceiling
  3. `qimao`        — 七猫免费小说: steady buyout/minimum-guarantee + over-guarantee revenue share
  4. `jjwxc`        — 晋江文学城: #1 female paid subscription + 8:2 copyright adaptation leader
  5. `zhihu_yanyan` — 知乎盐言故事: #1 short-fiction high-conversion paywall + short-drama incubator
  6. `ciweimao`     — 刺猬猫阅读: top ACG / light-novel vertical paid subscription community

Provides:
  - Structured signing thresholds, revenue split, full-attendance rules, 2025-2026 policy updates
  - Progression ladders (entry -> recommendation testing -> chart climb -> monetization)
  - Per-chart ranking rules (driver metrics, eligibility windows, climb strategy)
  - `recommend_monetization_platforms(...)`: deterministic platform matcher by scale, experience & genre
"""
from __future__ import annotations

from typing import Any

PLAYBOOK_UPDATED_PERIOD = '2025-2026（以各平台作家后台当期公告与合同细则为准）'

PLATFORM_PLAYBOOKS: dict[str, dict[str, Any]] = {
    'fanqie': {
        'id': 'fanqie',
        'name': '番茄小说',
        'full_name': '番茄小说（含番茄短故事 / 番茄畅听）',
        'tier': 'T0 · 全网第一免费流量池',
        'audience_focus': '男女频大众向、脑洞爽文、都市年代、玄幻修仙、女频短故事',
        'scale_fit': 'both',
        'beginner_friendly': 'medium',
        'verified_period': PLAYBOOK_UPDATED_PERIOD,
        'monetization': {
            'model': '免费阅读广告分成 + 番茄畅听（TTS听书）分成 + 微短剧/IP版权激励',
            'revenue_split': '独家签约享广告与听读基础分成；短故事另有抖音/穿山甲渠道活动加成或千字 100–3000 元保底',
            'full_attendance': '数据挂钩全勤：满 10 万字且当月站内听读/广告分成达底线门槛 + 日更 ≥4000/6000 字，方可领对应档位全勤（纯单机无收益拿不到全勤）',
            'bonus_channels': ['番茄畅听有声分成', '今日头条信息流/抖音推文联动', '微短剧改编版权分红', '星火/星燃专项激励'],
            'settlement': '按月结算',
        },
        'signing': {
            'mode': '按作者等级分层（完本签约 / 连载签约） + 短故事完本投稿',
            'threshold': 'Lv.0/Lv.1 新人长篇需完本签约（15万或30万字，视主分类）；Lv.2+ 老作者保留 2万/5万/8万字三次连载签约机会；番茄短故事 5000–3万字完本即可投稿',
            'contract_binding': '单本作品独家签约（锁定作品不可删书，可修章）',
            'recent_2026_alert': '⚠️ 2026年10月12日起重要新规：Lv.0/Lv.1 新作者长篇须走「完本签约」（写完 15万–30万字整书过审），裸奔试错成本显著上升；纯新人建议先用「番茄短故事（5000–3万字）」低成本试水或同步评估七猫保底通道！',
        },
        'progression_ladder': [
            {'stage': '开篇与签约过审', 'words_or_time': '短篇 0.5–3万字完本；老作者长篇 2/5/8万字；新人长篇 15–30万字完本', 'core_metrics': '黄金三章留存、清晰主线、严禁AI套话与注水', 'action_tip': '前3章必须落地核心卖点与首次小回报，竖屏短段（中位20–35字）'},
            {'stage': '推荐验证期', 'words_or_time': '连载模式约 8 万字开启小流量测水', 'core_metrics': '开篇完读率、加书架率', 'action_tip': '保持稳定日更 ≥4000 字，盯紧前5章跳失点并及时修文'},
            {'stage': '正式首秀（核心生死关）', 'words_or_time': '约 10 万字系统自动触发', 'core_metrics': '头 3 天完读率、次日/三日追读率、催更互动', 'action_tip': '首秀前储备至少 1–2 万字存稿；若转化差第 4 天易腰斩，首秀期务必高密度兑现爽点'},
            {'stage': '书名验证与多端破圈', 'words_or_time': '20万–50万字阶段', 'core_metrics': '多书名/封面点击转化、听书完播率、在读峰值', 'action_tip': '配合平台做多书名测试，同时联动番茄畅听与今日头条推流放大长尾收益'},
        ],
        'rank_lists': [
            {'name': '热门榜 / 畅销榜', 'category': '主流量大榜', 'driver_metrics': '实时在读人数、综合广告/听读变现价值、完读率与追读率', 'window': '纯算法动态实时刷新', 'strategy': '靠高追读率 + 长线不断更稳住高阶算法流量池，避免中后期崩节奏'},
            {'name': '黑马新书榜 / 飙升榜', 'category': '新书爆发榜', 'driver_metrics': '首秀期在读增速、高开篇完读率、加书架转化率', 'window': '首秀及上升期实时触发', 'strategy': '用强反差开局 + 10万字首秀密集爆发冲刺，直接撬动公域大池'},
            {'name': '完本榜 / 热搜榜', 'category': '长尾与破圈榜', 'driver_metrics': '全本完读率、站内外搜索热度、短剧/推文带动', 'window': '完本后持续享受算法长尾', 'strategy': '收尾稳妥不烂尾，完本后仍能通过听书与信息流持续赚取广告分成'},
        ],
        'craft_requirements': {
            'daily_words': '日更 ≥4000 字（冲量建议 6000 字）',
            'chapter_words': '单章 1800–3500 字（竖屏手机端友好）',
            'golden_three_focus': '第1章前300字必出核心矛盾/金手指或身份反差；短故事强推第一人称「我」沉浸切入',
            'hot_genres': ['GENRE_DUSHI', 'GENRE_XUANYI', 'GENRE_XUANHUAN', 'GENRE_YANQING', 'GENRE_ZHONGDIAN', 'GENRE_KEHUAN', 'GENRE_MOSHI'],
            'redlines': [
                '书名严控 15 字以内（半角算 0.5 字），禁空格、Emoji、促销括号',
                '严打低质水文与明显 AI 机械套话，违者限流或拒签',
                '正文严禁插入作者题外话、外链引流及违规拼音代写',
            ],
        },
    },
    'qidian': {
        'id': 'qidian',
        'name': '起点中文网',
        'full_name': '起点中文网（阅文男频旗舰付费平台）',
        'tier': 'T0 · 付费订阅与大IP天花板',
        'audience_focus': '男频精品长篇：玄幻、仙侠、历史、都市、科幻、悬疑、轻小说、诸天',
        'scale_fit': 'long',
        'beginner_friendly': 'low',
        'verified_period': PLAYBOOK_UPDATED_PERIOD,
        'monetization': {
            'model': 'VIP 付费订阅分成 + 月票/打赏 + 全勤奖 + 影视/动漫/游戏大版权',
            'revenue_split': '正版订阅标准分成（以阅文当期合同为准）+ 月票打赏 + 均订 3000 精品徽章与版权开发',
            'full_attendance': '稳定日更 4000/6000+ 字且全月不断更（按1000字整数倍计）；上架后频繁请假或缩减字数不仅扣全勤，还会直接导致智能推流量池掉档',
            'bonus_channels': ['月票/新书月票榜奖金', '精品/荣誉殿堂激励', '有声/漫画/动画/影视全版权开发'],
            'settlement': '按月结算（上架后次月起按订阅日销结算）',
        },
        'signing': {
            'mode': '强烈推荐「编辑内投」（直发原创极易单机）',
            'threshold': '内投通常准备完整大纲 + 前 6000 字左右正文给对应频道编辑；收到站短签约后须在约 5 天内更新满 2 万字入库',
            'contract_binding': '单本作品独家签约（阅文合约）',
            'recent_2026_alert': '⚠️ 2025–2026 起点免费期全面进入「强追读PK + 智能推日更档位」双轨赛马：大频道（玄幻/都市/轻小说）二进三淘汰率极高，新书期平均拉长至约 40 天 / 20 万字再上架吃满推荐！',
        },
        'progression_ladder': [
            {'stage': '编辑内投签约', 'words_or_time': '6000 字样稿 + 大纲', 'core_metrics': '核心创意辨识度、人设钩子、文笔稳定性', 'action_tip': '先查清各频道编辑收稿偏好再投，被拒可复盘修改换组重投，避免直接后台裸奔直发'},
            {'stage': '新书入库', 'words_or_time': '签约后 5 天内满 2 万字，持续约 14 天', 'core_metrics': '初期收藏与真实追读率', 'action_tip': '稳妥起见每日双更或单大章过 4000 字，期间严禁断更'},
            {'stage': '分类试水推（1–3轮PK）', 'words_or_time': '约 6 万字起进入同批 PK 晋级', 'core_metrics': '真实追读人数、章节完读率、收藏增速', 'action_tip': '周二等关键追读统计日务必把最强钩子/高潮排在最新章，严防“一轮游”断推'},
            {'stage': '智能推 + 三江推荐 + 强推', 'words_or_time': '12万字智能推节点 → 拔尖者晋级三江/强推', 'core_metrics': '跨频道拔尖追读、日更字数档位（5000/6000+）', 'action_tip': '三江是免费期含金量最高跳板，登上后通常无缝衔接强推与上架'},
            {'stage': 'VIP 上架首订与长尾', 'words_or_time': '约 20 万字 / 连载 40 天左右上架', 'core_metrics': '24小时首订、均订、上架前3个月新书扶持期日销', 'action_tip': '上架当天准备爆更存稿，前 3 个月维持稳定高日更稳住高阶智能推池'},
        ],
        'rank_lists': [
            {'name': '畅销榜 / 月票榜', 'category': '上架商业核心榜', 'driver_metrics': '24小时订阅、月票数、打赏与商业化综合日销', 'window': '实时/月度滚动', 'strategy': '靠上架高均订 + 月初/月底双倍月票期加更拉票冲击前列'},
            {'name': '签约新书榜 / 新人作者新书榜', 'category': '免费期曝光榜', 'driver_metrics': '新书期收藏增长、追读人数、推荐票与活跃度', 'window': '签约免费新书期', 'strategy': '卡准入库与试水推节奏集中爆发，借榜单流量反哺追读晋级'},
            {'name': '三江推荐', 'category': '编辑+数据S级跳板', 'driver_metrics': '全站各频道当周试水推最拔尖的真实追读与留存', 'window': '每周遴选', 'strategy': '前 15 万字死磕主线推进、世界观新鲜感与章尾强追读钩子'},
            {'name': '阅读指数榜 / 原创推荐榜', 'category': '读者活跃与口碑榜', 'driver_metrics': '真实有效阅读人数、章节讨论度与推荐票', 'window': '日/周动态更新', 'strategy': '提高角色记忆点与段评互动设计，提升真实追读粘性'},
        ],
        'craft_requirements': {
            'daily_words': '免费期稳定 ≥4000 字；上架保智能推建议 5000–6000+ 字',
            'chapter_words': '单章 2000–4000 字（稳妥按千字整数倍以上，避免卡边少算字数）',
            'golden_three_focus': '开篇兼顾设定新鲜度、硬核质感与真实冲突，老读者反感无脑降智反派与千篇一律系统模板',
            'hot_genres': ['GENRE_XUANHUAN', 'GENRE_XIANXIA', 'GENRE_LISHI', 'GENRE_DUSHI', 'GENRE_KEHUAN', 'GENRE_XUANYI', 'GENRE_QINGXIAOSHUO', 'GENRE_ZHUTIAN'],
            'redlines': [
                '书名不超过 15 字，禁止特殊符号与广告词',
                '免费期与上架前 3 个月切忌断更或大幅缩水，否则智能推直接降档',
                '严禁涉政历史虚无、低俗擦边与抄袭洗稿',
            ],
        },
    },
    'qimao': {
        'id': 'qimao',
        'name': '七猫免费小说',
        'full_name': '七猫免费小说（七猫中文网 / 奇妙小说网）',
        'tier': 'T0 · 免费保底最稳健平台',
        'audience_focus': '男女频强情绪爽文：女频虐恋/追妻/年代/豪门；男频快节奏都市/爽文/历史/脑洞',
        'scale_fit': 'long',
        'beginner_friendly': 'high',
        'verified_period': PLAYBOOK_UPDATED_PERIOD,
        'monetization': {
            'model': '保底 + 超保底五五分成（双保险） OR 纯分成 / 超级纯分成',
            'revenue_split': '保底常见千字 20–80 元（大咖最高可达千字 1000 元），实际广告收益超保底后通常 5:5 分成；纯分成按站内广告与阅读收益阶梯分成',
            'full_attendance': '规则清晰友好：日更 ≥4000 字即可享全勤（常见约千字 6 元，月封顶 20 万字，每月允许请假 1 天）；注意纯分成作品完结须 ≥20 万字且不可烂尾，否则完结月无全勤',
            'bonus_channels': ['新人训练营阶段奖学金', '年度垂类题材激励', '有声/短剧/海外衍生分成'],
            'settlement': '按月结算（保底稿费抗波动能力强）',
        },
        'signing': {
            'mode': '编辑内投保底 / 作家后台直发签约 / 新人训练营',
            'threshold': '常规内投大纲 + 前 1–2 万字；新人训练营约 3 万字即可低门槛切入，数据达标后转正式保底或分成合同',
            'contract_binding': '单本作品独家签约',
            'recent_2026_alert': '💡 2026 新人友好亮点：在番茄收紧新人完本签约的背景下，七猫的「3万字训练营 + 千字保底 + 允许月请假1天的明确全勤」是目前长篇新人稳健拿稿费的首选保底路线之一！',
        },
        'progression_ladder': [
            {'stage': '大纲过审 / 3万字签约', 'words_or_time': '内投 1–2万字 或 训练营 3万字', 'core_metrics': '题材对口度、黄金三章强情绪与直白高辨识书名', 'action_tip': '直接亮出核心冲突与人物关系拉扯，避免大段慢热世界观说明书'},
            {'stage': '冷启动测水', 'words_or_time': '签约后编辑排期 + 算法初始流量', 'core_metrics': '点击率、前几章留存率、单日阅读 UV', 'action_tip': '保持手机端紧凑短段、强对话推进，前 10 万字死磕留存曲线'},
            {'stage': '重磅/分类强推爬坡', 'words_or_time': '10万–30万字放量期', 'core_metrics': '读完率、必读票增量、书架添加率与阅读时长', 'action_tip': '发动章末互动引导读者投「必读票」，保持日更 4000–6000 字吃满全勤与流量'},
            {'stage': '超保底分成与长尾完结', 'words_or_time': '20万字以上稳健完本', 'core_metrics': '总广告分成超保底线、高完本率不烂尾', 'action_tip': '纯分成切记满 20 万字且体面收尾，保住完结月全勤与后续长尾分成'},
        ],
        'rank_lists': [
            {'name': '全站书库点击新书 / 新书榜', 'category': '新书风向榜', 'driver_metrics': '新书期点击转化、前章留存与单日阅读 UV', 'window': '实时更新（已自动过滤非网文出版物）', 'strategy': '靠高点击直白书名 + 强冲突简介抢占首屏点击'},
            {'name': '畅销榜 / 飙升榜', 'category': '核心变现榜', 'driver_metrics': '单日 UV、留存率、必读票数、广告有效阅读时长', 'window': '日/周动态刷新', 'strategy': '情绪起伏密集 + 必读票互动拉动，形成 UV 与广告分成正循环'},
            {'name': '读完榜', 'category': '高粘性长尾榜', 'driver_metrics': '读者持续追读至最新章/全本的读完比例', 'window': '长期权重极高', 'strategy': '少水字数、不偏题、每隔 3–5 章必须有一次小高潮兑现'},
        ],
        'craft_requirements': {
            'daily_words': '日更 ≥4000 字（月封顶 20 万字全勤，每月可请假 1 天）',
            'chapter_words': '单章 1800–3500 字',
            'golden_three_focus': '直给情绪钩子与明确人设目标，简介严控 400 字内直击看点',
            'hot_genres': ['GENRE_YANQING', 'GENRE_DUSHI', 'GENRE_ZHONGDIAN', 'GENRE_LISHI', 'GENRE_XUANHUAN', 'GENRE_XUANYI'],
            'redlines': [
                '书名不超过 15 字，简介不超过 400 字，禁止促销引流词与外链',
                '纯分成完结不足 20 万字或被判烂尾将取消完结月全勤',
                '严禁低俗擦边与 AI 生硬模板文',
            ],
        },
    },
    'jjwxc': {
        'id': 'jjwxc',
        'name': '晋江文学城',
        'full_name': '晋江文学城（女频订阅与影视出版旗舰）',
        'tier': 'T0 · 女频订阅 + 8:2 版权王者',
        'audience_focus': '女频原创言情、古言宅斗、现言职场、无限流/悬疑、纯爱/无CP/百合',
        'scale_fit': 'long',
        'beginner_friendly': 'medium',
        'verified_period': PLAYBOOK_UPDATED_PERIOD,
        'monetization': {
            'model': 'VIP 订阅分成 + 霸王票/营养液 + 红花/全勤加成 + 影视出版大版权',
            'revenue_split': '订阅（网页/APP 约 5:5 左右，视合同细则）+ 霸王票 5:5 + 版权收益（影视/出版/广播剧/动漫）常见 8:2（作者占大头！）',
            'full_attendance': '日更 3000 / 6000 / 9000 字档位对应当月订阅收益比例加成与小红花奖励',
            'bonus_channels': ['影视剧/网剧高价版权（作者占大头）', '广播剧与繁简体实体出版', '完结金榜/全订榜长尾'],
            'settlement': '按月结算',
        },
        'signing': {
            'mode': '「签人制」（非单本签）：后台发文满 1 万字自荐申签',
            'threshold': '注册笔名并公开发表满 1 万字提交审签模板；未过约冷却 1 周可重申；入V需达频道收藏线（言情/无CP/百合常见 ~300 收藏，纯爱 ~300–500 收藏）',
            'contract_binding': '⚠️ 签人合约（通常 5 年起步），合约期内作者全部同类网文代理权归晋江，签约前务必想清长期规划',
            'recent_2026_alert': '⚠️ 核心机制提醒：晋江「新晋作者榜」按同一实名证件/客户号严格限制总上榜次数（约 2–3 次机会），千万不要拿半成品练手白白耗掉新晋榜机会！',
        },
        'progression_ladder': [
            {'stage': '1万字自荐签约', 'words_or_time': '发文满 1 万字', 'core_metrics': '核心梗辨识度、文案吸引力、人设与文笔', 'action_tip': '先打磨好文案（含核心卖点+立意+排雷）与前三章，再攒够 1 万字提交审签'},
            {'stage': '新晋作者榜（新人黄金梯）', 'words_or_time': '1万–10万字，停留约 30 天（同实名限次！）', 'core_metrics': '文章积分（点击/收藏/评论/字数/更新）', 'action_tip': '确保全文有完整存稿与稳定日更再开文，把有限的新晋机会吃满'},
            {'stage': '顺V / 倒V 入V', 'words_or_time': '收藏达频道V线（通常 300–500 收藏）', 'core_metrics': '预收/免费期收藏与有效追读', 'action_tip': '选好入V万字更新日，入V当天三合一万字更以冲刺夹子千字收益'},
            {'stage': '夹子 / VIP 金榜（生死大考）', 'words_or_time': '入V后第 3–4 天自动上夹子', 'core_metrics': '入V后千字订阅与实时收益（修罗场排名）', 'action_tip': '入V前2章务必埋下强情感/剧情钩子，保证夹子当天高转化率'},
            {'stage': '自然榜长线晋级', 'words_or_time': '月榜(11–40天) → 季榜(41–130天) → 半年榜(131–310天) → 长生殿(1年以上)', 'core_metrics': '持续日更与综合文章积分', 'action_tip': '保持不断更与稳定完结率，完结后继续角逐完结金榜与版权改编'},
        ],
        'rank_lists': [
            {'name': '新晋作者榜', 'category': '新人专属大榜', 'driver_metrics': '发文积分（点击/收藏/评论/字数综合）', 'window': '1万–10万字，停留30天，同实名限次', 'strategy': '开文前做好预收与存稿，开文后日更不断档冲前排'},
            {'name': '夹子（VIP 金榜）', 'category': '入V定生死榜', 'driver_metrics': '入V后千字收益 / 订阅转化', 'window': '入V后第 3–4 天上榜', 'strategy': '入V当天万字爆发 + 关键高潮卡点，决定后续整个连载期流量级'},
            {'name': '月榜 / 季榜 / 半年榜 / 长生殿', 'category': '自然积分晋级榜', 'driver_metrics': '点击、收藏、评论、打分、字数与日更持续性', 'window': '11–40天 / 41–130天 / 131–310天 / >1年且周更≥5000字', 'strategy': '靠高口碑稳定日更顺次爬榜，严防断更掉积分'},
            {'name': '收入金榜 / 完结金榜', 'category': '头部收益榜', 'driver_metrics': '真实订阅与霸王票收益总额', 'window': '周/月/完结后持续曝光', 'strategy': '高完成度人设感情线 + 优质完本率，直接吸引影视出版方采购版权'},
        ],
        'craft_requirements': {
            'daily_words': '建议日更 ≥3000 字（冲榜/小红花常见 6000 字档）',
            'chapter_words': '单章 2500–5000 字（入V当天常需万字大肥章）',
            'golden_three_focus': '极度看重「人设反差、感情张力、文案与正文一致性」，开篇忌平淡流水账',
            'hot_genres': ['GENRE_YANQING', 'GENRE_QINGCHUN', 'GENRE_XUANYI', 'GENRE_ZHUTIAN', 'GENRE_ZHONGDIAN', 'GENRE_QUANMOU'],
            'redlines': [
                '书名不超过 14 字（不折半角），禁用装饰符号与表情',
                '严禁未成年早恋/越界描写、颈部以下违规描写与违规外链引流',
                '签人合约通常 5 年起步，切勿一稿多投或私自在外站发布',
            ],
        },
    },
    'zhihu_yanyan': {
        'id': 'zhihu_yanyan',
        'name': '知乎盐言故事',
        'full_name': '知乎盐言故事（盐选短篇 / 中篇变现旗舰）',
        'tier': 'T0 · 短篇快回款与微短剧孵化器',
        'audience_focus': '强反转高情绪短篇：现言/古言、婚姻家庭、现实社会、职场、悬疑推理、脑洞',
        'scale_fit': 'short',
        'beginner_friendly': 'high',
        'verified_period': PLAYBOOK_UPDATED_PERIOD,
        'monetization': {
            'model': '盐选会员付费解锁 5:5 分成 + 微短剧/AI漫剧/出版高转化版权分成',
            'revenue_split': '单本签约后上架盐选专栏，盐选会员转化订单收益常见作者与平台 5:5（50%）分成；版权售出另有高额分成',
            'full_attendance': '无日更全勤捆绑！写完 1万–3万字即一次性投稿变现，极其适合兼职/新人快速跑通第一笔稿费',
            'bonus_channels': ['微短剧爆款改编分成（孵化率全行业前列）', '有声书/AI漫剧/出版版权', '征文话题奖金'],
            'settlement': '月结或季结（按合同约定）',
        },
        'signing': {
            'mode': '「单本独家签」（不绑人！只签单部作品版权）',
            'threshold': '短篇 1万–3万字完结在线投稿（盐选作者平台或知乎故事话题）；中长篇 6万–25万字需大纲 + 3万字正文；官方审稿约 20 个工作日',
            'contract_binding': '仅绑定单部签约作品，不限制作者在其他平台写别的书',
            'recent_2026_alert': '💡 新人零包袱快变现首选：无需熬几十万字连载、不绑人身合约，1.5万字完本即可验证市场；同时务必警惕第三方“100%包过保底”机构骗局，走官方盐选作者平台直投最稳！',
        },
        'progression_ladder': [
            {'stage': '导语黄金 500 字设计', 'words_or_time': '开篇前 300–500 字（通常以分隔符衔接正文）', 'core_metrics': '信息流点击率与下拉续读率', 'action_tip': '开篇直接抛「关系撕裂 / 异常处境 / 信息差悬念」，用一句话让读者忍不住点开全文'},
            {'stage': '免费段与付费卡点设计', 'words_or_time': '约第 2000–4000 字处设核心反转/掀桌前夜卡点', 'core_metrics': '免转付（免费试读转开盐选会员）转化率', 'action_tip': '卡点前必须把憋屈/悬念拉满，反转揭晓留在付费锁章后第一屏'},
            {'stage': '完整投稿过审', 'words_or_time': '1万–3万字全文完结投稿，审稿约 20 工作日', 'core_metrics': '编辑评估反转密度、情绪烈度、完读闭环', 'action_tip': '每 3000–4000 字一次反转升级，绝不拖泥带水，结尾干脆爽快闭环'},
            {'stage': '盐选专栏放量与短剧孵化', 'words_or_time': '上线后通过知乎问答信息流与搜索长尾持续拉新', 'core_metrics': '盐选订单转化数、赞同收藏率、短剧版权选中率', 'action_tip': '搭配强共鸣的知乎提问场景包装标题，放大信息流自然曝光'},
        ],
        'rank_lists': [
            {'name': '盐言故事热榜 / 飙升榜', 'category': '核心短篇变现榜', 'driver_metrics': '盐选会员付费转化数（免转付核心）、完读率、赞同互动', 'window': '算法动态刷新', 'strategy': '前 500 字强导语 + 3000 字强付费卡点是冲榜绝对生命线'},
            {'name': '知乎故事话题高赞榜', 'category': '自然引流入口', 'driver_metrics': '回答赞同数、评论热度、点击转付费率', 'window': '长尾搜索+信息流推荐', 'strategy': '精选高热情感/脑洞/现实痛点话题切入，用第一人称极速代入'},
        ],
        'craft_requirements': {
            'daily_words': '无日更压力（短篇推荐 3–7 天一次性打磨完 1万–2.5万字完稿）',
            'chapter_words': '全文 10000–30000 字（可分 4–10 节，每节 2000–3500 字）',
            'golden_three_focus': '「前 300–500 字导语钩子 + 每 3000 字强反转 + 极致情绪宣泄」三位一体',
            'hot_genres': ['GENRE_YANQING', 'GENRE_XIANSHI', 'GENRE_XUANYI', 'GENRE_SHANGZHAN', 'GENRE_QINGCHUN', 'GENRE_GAOXIAO'],
            'redlines': [
                '⛔ 硬红线：严禁耽美/纯爱（BL）题材！',
                '⛔ 硬红线：严禁未成年恋爱及任何低俗擦边内容（恋爱角色须设定 ≥18 岁）',
                '必须独家首发，严禁一稿多投或抄袭洗稿',
            ],
        },
    },
    'ciweimao': {
        'id': 'ciweimao',
        'name': '刺猬猫阅读',
        'full_name': '刺猬猫阅读（二次元 / 轻小说垂直付费社区）',
        'tier': 'T1 · 二次元轻小说垂直领头羊',
        'audience_focus': '二次元轻小说、动漫同人衍生、无限流、宅文化脑洞、变百/反套路搞笑',
        'scale_fit': 'long',
        'beginner_friendly': 'medium',
        'verified_period': PLAYBOOK_UPDATED_PERIOD,
        'monetization': {
            'model': 'VIP 付费订阅 6:4 分成（作者拿 60%）+ 刀片/打赏 + 月票榜现金奖 + 订阅挂钩新版全勤',
            'revenue_split': '正版订阅与催更刀片/打赏常见作者 60% / 平台 40%（以合同细则为准）',
            'full_attendance': '⚠️ 2026年12月起全勤大改：月更 ≥12万字且日更 ≥4000字，固定千字全勤逐步转为当月订阅稿费的 15%（日更4千）–25%（日更6千）提成（设3个月新旧就高过渡期）',
            'bonus_channels': ['月度总榜/新书榜现金奖金（第1名可达5000元）', '读者催更刀片与打赏'],
            'settlement': '按月结算',
        },
        'signing': {
            'mode': '编辑内投为主（评 A/B/C/D 签）',
            'threshold': '约 3 万字提交签约申请，更看重脑洞新鲜感、二次元梗契合度与前三章人设；约 12 万字安排上架 VIP',
            'contract_binding': '单本作品独家签约',
            'recent_2026_alert': '⚠️ 2026年12月全勤改版后，纯靠低订阅拿固定千字全勤的“保底工资”退出，全勤彻底偏向有订阅的中腰部与头部作者——选刺猬猫务必瞄准二次元核心圈层拉高订阅！',
        },
        'progression_ladder': [
            {'stage': '3万字内投申签', 'words_or_time': '约 3 万字（评 A/B/C/D 档）', 'core_metrics': '脑洞切入点、二次元人设萌点/反差、黄金三章趣味性', 'action_tip': '精准对齐二次元读者语境与槽点设计，提高间贴/吐槽互动率'},
            {'stage': '免费期漏斗推荐', 'words_or_time': '3万–12万字免费蓄水期', 'core_metrics': '收藏、追读、吐槽数与间贴活跃度', 'action_tip': '善用章节槽点与人物反差激发间贴讨论，活跃社区氛围有助编辑推流'},
            {'stage': '12万字 VIP 上架', 'words_or_time': '约 12 万字上架爆更', 'core_metrics': '首订、均订、月票与刀片转化', 'action_tip': '上架当月冲刺「月度新书榜」拿现金奖金与新书曝光'},
            {'stage': '订阅放量与月票冲榜', 'words_or_time': '上架后保持月更 ≥12万字 / 日更 ≥4000–6000字', 'core_metrics': '当月订阅稿费（决定新版全勤 15%–25% 加成）与月票排名', 'action_tip': '以订阅为核心导向，维持稳定日更吃满订阅提成型全勤'},
        ],
        'rank_lists': [
            {'name': '月票总榜 / 月度新书榜', 'category': '现金奖核心榜', 'driver_metrics': '自然月月票数（新书榜限入库约 3 个自然月内原创）', 'window': '自然月结算', 'strategy': '上架爆更 + 悬赏加更（月票/刀片换更）冲刺前十奖金'},
            {'name': '畅销榜 / 点击榜 / 收藏榜', 'category': '流量分发榜', 'driver_metrics': '订阅收益、实时点击与收藏增长', 'window': '周/月刷新', 'strategy': '保持精准宅向标签与稳定更新节奏'},
            {'name': '刀片榜 / 吐槽榜', 'category': '社区特色互动榜', 'driver_metrics': '读者催更刀片数、间贴吐槽密度', 'window': '高频互动驱动', 'strategy': '章末留搞笑或震撼断章，激发读者发间贴与寄刀片催更'},
        ],
        'craft_requirements': {
            'daily_words': '日更 ≥4000 字（月更 ≥12 万字达新版全勤线）',
            'chapter_words': '单章 2000–4000 字',
            'golden_three_focus': '开篇迅速立住核心二次元脑洞与鲜明主角/互动人设，语言轻快有梗不沉闷',
            'hot_genres': ['GENRE_QINGXIAOSHUO', 'GENRE_ZHUTIAN', 'GENRE_GAOXIAO', 'GENRE_QIHUAN', 'GENRE_XUANHUAN', 'GENRE_YOUXI'],
            'redlines': [
                '书名不超过 15 字，禁违规符号与敏感词',
                '严禁违背公序良俗及超尺度低俗描写',
                '同人衍生注意遵守平台当期版权合规清单',
            ],
        },
    },
}

_ALIAS_TO_PLAYBOOK: dict[str, str] = {
    'fanqie': 'fanqie', '番茄': 'fanqie', '番茄小说': 'fanqie', '番茄短故事': 'fanqie',
    'qidian': 'qidian', '起点': 'qidian', '起点中文网': 'qidian', '起点读书': 'qidian',
    'qimao': 'qimao', '七猫': 'qimao', '七猫免费小说': 'qimao', '七猫中文网': 'qimao',
    'jjwxc': 'jjwxc', '晋江': 'jjwxc', '晋江文学城': 'jjwxc',
    'zhihu_yanyan': 'zhihu_yanyan', 'zhihu': 'zhihu_yanyan', 'yanyan': 'zhihu_yanyan',
    '知乎': 'zhihu_yanyan', '盐言': 'zhihu_yanyan', '知乎盐言': 'zhihu_yanyan', '知乎盐言故事': 'zhihu_yanyan', 'short': 'zhihu_yanyan',
    'ciweimao': 'ciweimao', '刺猬猫': 'ciweimao', '刺猬猫阅读': 'ciweimao',
}


def get_platform_playbook(platform: str) -> dict[str, Any] | None:
    key = str(platform or '').strip().lower()
    pid = _ALIAS_TO_PLAYBOOK.get(key)
    if not pid:
        for alias, target in _ALIAS_TO_PLAYBOOK.items():
            if alias and alias in key:
                pid = target
                break
    return PLATFORM_PLAYBOOKS.get(pid) if pid else None


def list_platform_playbooks() -> list[dict[str, Any]]:
    order = ('fanqie', 'qidian', 'qimao', 'jjwxc', 'zhihu_yanyan', 'ciweimao')
    return [PLATFORM_PLAYBOOKS[k] for k in order if k in PLATFORM_PLAYBOOKS]


def platform_monetization_brief(platform: str) -> str:
    pb = get_platform_playbook(platform)
    if not pb:
        return ''
    return (
        f'【{pb["name"]}变现指引】{pb["monetization"]["model"]}；'
        f'签约门槛：{pb["signing"]["threshold"]}；'
        f'核心红线/提示：{pb["signing"]["recent_2026_alert"]}'
    )


def recommend_monetization_platforms(
    *,
    scale: str = 'long',
    experience: str = 'beginner',
    genre_ids: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Rank top monetizable platforms by book scale (`long`/`short`), author experience (`beginner`/`experienced`), and genres."""
    sc = str(scale or 'long').strip().lower()
    exp = str(experience or 'beginner').strip().lower()
    gset = {str(g).strip() for g in (genre_ids or ()) if str(g).strip()}

    ranked: list[dict[str, Any]] = []
    for pb in list_platform_playbooks():
        score = 50
        reasons: list[str] = []
        cautions: list[str] = []

        # Scale fit
        if sc == 'short':
            if pb['scale_fit'] == 'short':
                score += 35
                reasons.append('专为 1万–3万字短篇设计，完结即投、单本签约不绑人，回款最快')
            elif pb['scale_fit'] == 'both':
                score += 25
                reasons.append('支持番茄短故事（0.5–3万字完本投稿），可享广告分成/千字保底与抖音推文流量')
            else:
                score -= 25
                cautions.append('主营长篇连载，不适合短篇快速变现')
        else:
            if pb['scale_fit'] in ('long', 'both'):
                score += 20
            else:
                score -= 10
                reasons.append('中长篇支持 6万–25万字盐选连载，但主阵地仍为强反转短篇')

        # Experience & 2026 policy fit
        if exp == 'beginner':
            if pb['beginner_friendly'] == 'high':
                score += 25
                reasons.append('对新人最友好：门槛清晰、前期试错成本低')
            elif pb['beginner_friendly'] == 'medium':
                score += 5
            else:
                score -= 15
                cautions.append('头部频道内卷严苛，新手裸奔直发极易单机，需先打磨大纲走编辑内投')

            if pb['id'] == 'fanqie' and sc == 'long':
                score -= 10
                cautions.append('2026年10月起 Lv.0/Lv.1 新人长篇需完本签约（15–30万字），建议新人先做番茄短故事或优先看七猫保底')
            elif pb['id'] == 'qimao' and sc == 'long':
                score += 10
                reasons.append('3万字训练营切入 + 千字保底/允许月请假1天全勤，适合新人稳妥拿第一桶金')
            elif pb['id'] == 'jjwxc':
                cautions.append('签人合约 5 年起且新晋作者榜同实名限次，务必攒足存稿再开文')
        else:
            # Experienced author with proven completion / Lv.2+ / stable daily output
            if pb['id'] in ('qidian', 'fanqie', 'jjwxc'):
                score += 20
                reasons.append('成熟作者上限最高：流量天花板、订阅均订与影视/短剧版权爆发力最强')
            if pb['id'] == 'ciweimao':
                score += 10
                reasons.append('2026年底新版全勤与订阅挂钩（15%–25%提成），利好有订阅基本盘的二次元成熟作者')

        # Genre alignment
        hot = set(pb['craft_requirements']['hot_genres'])
        overlap = sorted(gset & hot)
        if overlap:
            score += min(25, 15 + 5 * len(overlap))
            reasons.append(f'题材高度契合该平台强势变现品类（命中 {len(overlap)} 项）')

        ranked.append({
            'platform_id': pb['id'],
            'platform_name': pb['name'],
            'full_name': pb['full_name'],
            'tier': pb['tier'],
            'fit_score': max(0, min(100, score)),
            'fit_reasons': reasons,
            'cautions': cautions or [pb['signing']['recent_2026_alert']],
            'monetization_model': pb['monetization']['model'],
            'signing_threshold': pb['signing']['threshold'],
            'full_attendance': pb['monetization']['full_attendance'],
            'daily_words': pb['craft_requirements']['daily_words'],
        })

    ranked.sort(key=lambda r: (-r['fit_score'], r['platform_id']))
    return ranked
