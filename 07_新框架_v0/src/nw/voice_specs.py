"""Executable Voice Specification Library, Multi-Genre Voice Fingerprint Registry, and Book Voice Spec Compiler.

Replaces vague adjective labels ("冷峻/轻快/诗意") with concrete, boundary-enforced
6-dimension linguistic rules, anti-drift redlines, and plot-free 50-char micro-contrasts
(❌ stiff AI prose vs ✅ target human register), plus automatic multi-genre voice
fingerprint collection from targeted novel decomposition.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

from nw.store import Store, now
from nw.studio.catalog import canonical_types
from nw.task_models import canonical, content_sha256

VOICE_SPEC_FILENAME = 'voice_spec.json'

VOICE_FINGERPRINT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS voice_fingerprints (
 id TEXT PRIMARY KEY,
 book_id TEXT NOT NULL REFERENCES staging_books(id),
 structure_version INTEGER NOT NULL,
 title TEXT NOT NULL,
 base_voice_id TEXT NOT NULL,
 type_tags_json TEXT NOT NULL DEFAULT '[]',
 excluded_types_json TEXT NOT NULL DEFAULT '[]',
 scene_functions_json TEXT NOT NULL DEFAULT '[]',
 body_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'approved',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS voice_fp_book ON voice_fingerprints(book_id, status);
'''

SCENE_FUNCTION_LABELS: dict[str, str] = {
    'opening_hook': '开场立人与抛钩',
    'confrontation': '对峙交锋与试探',
    'action_reveal': '动作爆发与能力亮相',
    'emotional_shock': '情绪冲击与内心转折',
    'dialogue_daily': '日常对白与信息渗入',
}

VOICE_KNOBS: dict[str, dict[str, Any]] = {
    'register': {
        'label': '语体寄存器（文白与用词体系）',
        'multi': False,
        'options': [
            {'id': 'modern_plain', 'label': '现代大白话', 'directive': '用干净利落的现代白话叙述，绝不夹杂半吊子古文或翻译腔，专业词只在必要处自然带出。'},
            {'id': 'colloquial_street', 'label': '市井烟火口语', 'directive': '贴近真实生活口语与行业行话，带点烟火气与粗粝感，人物说话有各自阶层的顺口用词。'},
            {'id': 'semi_classical', 'label': '半文半白雅致', 'directive': '半文半白但不晦涩，自然运用“便/却/倒也/只见/沉吟”等网文古风连接词，禁用现代网络热梗。'},
            {'id': 'hard_documentary', 'label': '冷峻行业实录', 'directive': '用精确、克制、重物证与实操细节的写实语体，像亲历者贴近现场观察，拒绝浮夸修辞。'},
            {'id': 'atmospheric_poetic', 'label': '意象氛围渲染', 'directive': '以精选环境光影、气候与异域质感营造沉浸氛围，每段只抓 1–2 个高辨识意象，绝不空泛抒情。'},
        ],
    },
    'cadence': {
        'label': '句式呼吸与节奏切换',
        'multi': False,
        'options': [
            {'id': 'smooth_flow', 'label': '顺畅连贯（一路说完）', 'directive': '普通场景按意思一路把句子说完整，长短句自然交替，不刻意切碎成电报体；高潮处再骤收短句。'},
            {'id': 'kinetic_sharp', 'label': '凌厉快切（短句动词）', 'directive': '冲突、交手与反杀段落优先短句与精准动词推进，动作起手—碰撞—结果干脆利落，少静态长定语。'},
            {'id': 'measured_layered', 'label': '绵密缓拍（细节蓄势）', 'directive': '允许在关键试探与压迫戏中放慢节奏，用停顿、物件与环境余波层层蓄压，再给决定性落点。'},
        ],
    },
    'dialogue_mind': {
        'label': '内心贴近度与对白质地',
        'multi': False,
        'options': [
            {'id': 'vivid_thought_sharp_talk', 'label': '直白心里话 + 带脾气短交锋', 'directive': '直接贴身写出主角的算计、顾虑、贪心或暗骂；对白带各人脾气与立场，敢打断、回避、呛声。'},
            {'id': 'restrained_subtext', 'label': '克制外显 + 潜台词机锋', 'directive': '减少直白自我剖白，多借客套、转话题、半截话与动作停顿藏住言外之意，让读者自己品出锋芒。'},
            {'id': 'witty_banter', 'label': '轻快吐槽 + 活人感语气词', 'directive': '保留自然口语语气词（呢/啊/都…了/倒也）与处境反差带来的鲜活趣味，吐槽从人物性格长出不跳戏。'},
        ],
    },
    'anti_drift_bans': {
        'label': '防 AI 漂移禁忌（可多选叠加）',
        'multi': True,
        'options': [
            {'id': 'no_modern_slang', 'label': '禁现代网梗', 'directive': '严禁在古风/正剧语境出现现代网络流行语、段子梗或出戏流行词。'},
            {'id': 'no_idiom_stacking', 'label': '禁四字成语堆砌', 'directive': '严禁连续堆砌四字成语或排比形容词，动作与神态一律用具体动词和可见细节写出。'},
            {'id': 'no_translationese', 'label': '禁翻译腔', 'directive': '严禁“他发出一声冷笑”“一股寒意顺着脊背爬上”“令人窒息的沉默”等译制腔套句。'},
            {'id': 'no_narrator_preaching', 'label': '禁旁白说教', 'directive': '严禁叙述者跳出来总结人生道理、替读者点破悬念，或用旁白把刚演完的情绪再解释一遍。'},
            {'id': 'no_inventory_ledger', 'label': '禁正文清点账目', 'directive': '用完的物品去向、钱数进出、能力限制由后台状态机记账，读者不关心时绝不在正文逐项清点防挑刺。'},
            {'id': 'no_telegraph_chop', 'label': '禁电报体碎短句', 'directive': '严禁连续用无主语的三五字碎短句摆排造势（如“灯暗了。人走了。心冷了。”），保持自然人话语流。'},
        ],
    },
}

_KNOB_OPTION_MAP: dict[str, dict[str, dict[str, str]]] = {
    k: {opt['id']: opt for opt in meta['options']}
    for k, meta in VOICE_KNOBS.items()
}


VOICE_BASES: tuple[dict[str, Any], ...] = (
    {
        'id': 'VOICE_NET_VERNACULAR',
        'name': '成熟网文烟火白描流',
        'tagline': '一路说完整的人话语流，贴身鲜活心里话 + 带脾气对白 + 扎眼实景白描',
        'recommended_genres': (
            'GENRE_DUSHI', 'GENRE_XIANSHI', 'GENRE_ZHIYE', 'GENRE_SHANGZHAN',
            'GENRE_ZHUTIAN', 'GENRE_TONGREN', 'GENRE_TIYU',
        ),
        'incompatible_genres': (),
        'aligned_tones': ('TONE_LIGHT', 'TONE_WARM', 'TONE_SERIOUS'),
        'aligned_styles': ('STYLE_REALISTIC', 'STYLE_GROWTH', 'STYLE_FAST'),
        'default_knobs': {
            'register': 'colloquial_street',
            'cadence': 'smooth_flow',
            'dialogue_mind': 'vivid_thought_sharp_talk',
            'anti_drift_bans': ['no_translationese', 'no_narrator_preaching', 'no_inventory_ledger', 'no_telegraph_chop'],
        },
        'dimensions': {
            'register': '自然成熟的现代网文白话，带市井与行业烟火气；不端架子、不用伪文学腔，也不用尬梗讨好读者。',
            'cadence': '普通叙述按意思一路说完，句长随事态自然起伏；不刻意切碎短句，冲突抬头时收紧动词节奏。',
            'psychic_distance': '紧贴视角人物，直接写出他当下的盘算、心疼、犹豫或暗喜；允许人物猜错，但绝不把猜测当已证实事实。',
            'dialogue_texture': '对白接住眼前的话和现场变化，保留“都…了/呢/啊”等自然语气词与各人脾气，绝不写成一问一答资料汇报。',
            'imagery_budget': '每场只挑 1–2 个视角人物真会注意的扎眼实景细节（掉漆门框、冷茶、手上的茧），不空堆五感模板。',
            'pacing_payoff': '小事快过、有冲突和得失的场面当场写足；章尾落在具体未了局面或刚掀开的麻烦上，不写抽象总结句。',
        },
        'drift_redlines': [
            '严禁写成“摸了摸兜里手机和钱一样没少”的防挑刺报账流水账。',
            '严禁遭遇大事时人物还像开会一样先理性分析利弊再补一句“他心里一紧”。',
            '严禁旁白站在外头用“好嘛/行吧”替读者概括处境抖机灵。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'confrontation',
                'label': '利益对峙与试探',
                'bad_ai': '他微微眯起眼睛，心中暗想对方绝非善类，声音平静地问道：“你今天来这里，究竟有什么目的？”对方嘴角勾起一抹冷笑：“我只是来拿回属于我的东西。”',
                'target_voice': '他把账本合上，压在手肘底下：“三千块尾款拖了两个月，今天拎两箱奶过来，你是打算拿奶抵账？”来人赔着笑往椅背一靠：“话别说这么冲嘛，我这不是带新单子来了。”',
                'why': '用具体物件与利益直接顶撞，对白带脾气和生活感，删掉“眯眼/暗想/冷笑”套式。',
            },
            {
                'scene_function': 'emotional_shock',
                'label': '突发变故第一反应',
                'bad_ai': '听完这个消息，他瞬间如遭雷击，脸色变得苍白，手指不由自主地颤抖起来，心中涌起一股难以言喻的恐惧与愤怒。',
                'target_voice': '电话那头挂断了，忙音嘟嘟响了五六声，他才发现自己还攥着锅铲。锅里的油已经冒起青烟，他连火都忘了关，抓起椅背上的外套就往门外冲。',
                'why': '先写触动当下的失神与本能举动，不靠“如遭雷击/难以言喻的恐惧”贴情绪标签。',
            },
            {
                'scene_function': 'opening_hook',
                'label': '开场立人与抛钩',
                'bad_ai': '这是一个繁华而又残酷的城市。林凡是一个普通的年轻人，已经在这里打拼了三年，却依然一无所有。这一天，命运的齿轮开始转动。',
                'target_voice': '房东把退租通知贴在防盗门上的时候，陈野正蹲在卫生间里拿铁丝捅下水道。水还没通开，兜里手机先响了，催款短信后面跟着一条陌生的入账通知——两万整。',
                'why': '直接落进窘迫现场与具体异常，零抽象背景介绍与“命运齿轮”套话。',
            },
        ],
    },
    {
        'id': 'VOICE_CLASSICAL_EDGE',
        'name': '古典清雅机锋流',
        'tagline': '半文半白凝练骨力，重礼数背后的潜台词机锋与克制留白',
        'recommended_genres': ('GENRE_XIANXIA', 'GENRE_WUXIA', 'GENRE_LISHI'),
        'incompatible_genres': ('GENRE_SAIBO', 'GENRE_KEHUAN', 'GENRE_DIANJING'),
        'aligned_tones': ('TONE_SERIOUS', 'TONE_COLD', 'TONE_DISTANT', 'TONE_EPIC'),
        'aligned_styles': ('STYLE_POETIC', 'STYLE_FANTASY', 'STYLE_STRATEGIC', 'STYLE_SERIOUS'),
        'default_knobs': {
            'register': 'semi_classical',
            'cadence': 'smooth_flow',
            'dialogue_mind': 'restrained_subtext',
            'anti_drift_bans': ['no_modern_slang', 'no_idiom_stacking', 'no_translationese', 'no_narrator_preaching'],
        },
        'dimensions': {
            'register': '半文半白、清雅利落而不晦涩；自然使用“便/却/只见/沉吟/倒也/冷笑道”，严禁现代网络梗与生造文言。',
            'cadence': '静处舒缓有古意，动处骤收显骨力；长句铺陈环境与心境，关键出手或点破机锋用干脆短句立住。',
            'psychic_distance': '贴近人物却保持几分克制，心念写成符合古人/修士常识的算计与忌惮（如寿元、因果、辈分、门规）。',
            'dialogue_texture': '话分辈分与身份，表面讲礼数体面、内里藏利害杀机；少把潜台词替读者说破，让对方接话露怯。',
            'imagery_budget': '善用灯火、茶烟、剑锈、山雾、钟声等古典实景物象承载氛围，一笔点出即可，不堆砌四字骈句。',
            'pacing_payoff': '斗法写清虚实算计、真气/异象与代价落点，静修与转场留足余韵；不用“申时/卯时”等需换算冷词，改用傍晚/天明。',
        },
        'drift_redlines': [
            '严禁堆砌“风起云涌、气吞山河、剑气纵横、宛若神魔”等空洞四字成语排比。',
            '严禁在仙侠/历史对话中混入现代网梗或“逻辑/概率/底层机制”等现代术语。',
            '严禁把修仙斗法写成毫无灵气异象的普通武侠比划，或用现代凡人常识算修士寿元。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'confrontation',
                'label': '礼数机锋与潜台词',
                'bad_ai': '他目光如炬，气势如虹，心中暗道此人必定居心叵测，冷冷道：“阁下休要巧言令色，你莫非以为我看不穿你的阴谋诡计？”',
                'target_voice': '他垂眼拨了拨浮在碗面的茶梗，半晌才笑道：“师兄这笔灵石账算得极细，只不知外堂的几位长老，肯不肯认这个数。”',
                'why': '表面笑语客套，实则直戳对方要害，不喊口号也不替读者解释“居心叵测”。',
            },
            {
                'scene_function': 'action_reveal',
                'label': '招式与异象亮相',
                'bad_ai': '他瞬间爆发出恐怖的气息，只见一道璀璨夺目的剑光划破苍穹，带着毁天灭地之威，狠狠斩向对手，周围众人无不震惊失色。',
                'target_voice': '竹竿点在胸口前，他本能运起那丝真气往外一顶，不料竿头骤然生出一股看不见的水流，把他的力气整股卷进去转了半圈，原封不动拍回他自己胸膛，连檐下晾着的粗布衣裳无风齐齐飘了一下。',
                'why': '写清真气异象、受力路径与环境连锁实证，比“毁天灭地/震惊失色”有力量十倍。',
            },
            {
                'scene_function': 'emotional_shock',
                'label': '克制情绪冲击',
                'bad_ai': '得知师门噩耗，他内心掀起了惊涛骇浪，悲痛欲绝，双拳紧握得发白，发誓一定要查明真相。',
                'target_voice': '灯芯啪地爆了一朵火星。他端着药碗的手没抖，碗沿却晃出半口褐汁，泼在虎口上也没觉出烫——三百里加急的青羽符，怎么会是从后山飞进来的？',
                'why': '用动作失常与一个直抵核心的念头写出震惊，比“内心掀起惊涛骇浪”更克制更有力。',
            },
        ],
    },
    {
        'id': 'VOICE_HARD_REALISM',
        'name': '冷峻实录悬疑流',
        'tagline': '近景实证白描 + 信息差压迫感 + 真实压力下的克制反应',
        'recommended_genres': ('GENRE_XUANYI', 'GENRE_TUILI', 'GENRE_JUNSHI', 'GENRE_MOSHI', 'GENRE_JINGSONG'),
        'incompatible_genres': ('GENRE_ERCIYUAN', 'GENRE_QINGXIAOSHUO', 'GENRE_QINGCHUN'),
        'aligned_tones': ('TONE_COLD', 'TONE_DARK', 'TONE_SERIOUS', 'TONE_DISTANT'),
        'aligned_styles': ('STYLE_SUSPENSE', 'STYLE_GRITTY', 'STYLE_COLD', 'STYLE_REALISTIC'),
        'default_knobs': {
            'register': 'hard_documentary',
            'cadence': 'measured_layered',
            'dialogue_mind': 'restrained_subtext',
            'anti_drift_bans': ['no_translationese', 'no_narrator_preaching', 'no_inventory_ledger', 'no_idiom_stacking'],
        },
        'dimensions': {
            'register': '精准、冷峻、重现场证据与物理常识的写实语体；名词具体到材质/方位/时间痕迹，少用空洞形容词。',
            'cadence': '勘查与盘问时稳住呼吸、层层逼近，发现关键破绽或危机骤临处短句收口，不滥用感叹号和破折号。',
            'psychic_distance': '严格区分“亲眼所见事实”与“人物当下怀疑”，绝不把未证实推测写成旁白定论，也不提前替读者把推论说完。',
            'dialogue_texture': '盘问、撒谎、试探皆有各自防线：人物会避重就轻、答非所问、借小事试探对方底细，绝不主动坦白推进剧情。',
            'imagery_budget': '把异常线索平平常常放进现场其余细节里，绝不写“他当时并没有多想”这类指路做记号的句子。',
            'pacing_payoff': '压迫感来自时间逼近、退路收窄与信息不对等；揭示真相靠物证与对方自露马脚，不靠旁白总结。',
        },
        'drift_redlines': [
            '严禁“碑背面有一行小字，他抄的时候并没有多想”这类提前给读者做记号的指路句。',
            '严禁把冷峻写成所有人遇险都不怕、不急、毫无情绪波动的机器人通报。',
            '严禁在章末替读者把显而易见的推论说破（如“莫非凶手就是刚才那个人？”）。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'opening_hook',
                'label': '现场异常与线索埋设',
                'bad_ai': '房间里弥漫着一股诡异的气氛。他扫视了一圈，注意到桌角有一道奇怪的划痕，但他当时并没有多想，殊不知这将成为破案的关键。',
                'target_voice': '屋里暖气开得很足，茶几上那半杯水却已经凉透。烟灰缸洗得发亮，边沿还沾着半截没擦净的湿纸巾，垃圾桶套着崭新的黑袋子，里头只躺着一张揉皱的停车票。',
                'why': '把线索自然混在现场物理细节里，读者自己看出不对劲，绝不做记号。',
            },
            {
                'scene_function': 'confrontation',
                'label': '审讯/试探攻防',
                'bad_ai': '警官冷冷地盯着他：“昨晚十点你在哪里？”嫌疑人眼神闪烁了一下，紧张地说：“我在家里睡觉。”警官敏锐地察觉到了他的谎言。',
                'target_voice': '“昨晚十点你在哪儿？”对面把袖口往下扯了扯，盖住腕表：“在家加班，物业监控能查。”“我没问你进小区的时间。”他把照片推过去半寸，“我问你十点整。”',
                'why': '攻防全在问句错位与防卫微动作里，不写“眼神闪烁/察觉谎言”的懒标签。',
            },
            {
                'scene_function': 'emotional_shock',
                'label': '危险逼近真实压迫',
                'bad_ai': '他突然意识到门外站着的人就是杀手，一股寒意瞬间席卷全身，心脏剧烈跳动起来。',
                'target_voice': '走廊声控灯灭了，门缝底下的光暗下去，却没有下楼的脚步声。三秒后，门把手极轻地往下压了半格，停住，又慢慢松了回去。他往后退了一步，脚跟碰到鞋柜，喉咙发干。',
                'why': '用声音、光线和门把手的精确物理变化把危险演在眼前，禁用“一股寒意席卷全身”。',
            },
        ],
    },
    {
        'id': 'VOICE_HIGH_KINETIC',
        'name': '高燃爽文快节拍流',
        'tagline': '蓄力→破局→当场爽感反馈三拍到位，交手短句凌厉有劲',
        'recommended_genres': ('GENRE_XUANHUAN', 'GENRE_YOUXI', 'GENRE_DIANJING', 'GENRE_GAOWU', 'GENRE_TIYU'),
        'incompatible_genres': ('GENRE_XIANSHI', 'GENRE_YANQING'),
        'aligned_tones': ('TONE_EPIC', 'TONE_SERIOUS', 'TONE_LIGHT', 'TONE_COLD'),
        'aligned_styles': ('STYLE_ACTION', 'STYLE_FAST', 'STYLE_FANTASY', 'STYLE_GROWTH'),
        'default_knobs': {
            'register': 'modern_plain',
            'cadence': 'kinetic_sharp',
            'dialogue_mind': 'vivid_thought_sharp_talk',
            'anti_drift_bans': ['no_idiom_stacking', 'no_translationese', 'no_inventory_ledger', 'no_narrator_preaching'],
        },
        'dimensions': {
            'register': '直接、有冲劲的商业网文白话；关键出手与反转敢用有力度的动词、贴切比喻和爽朗措辞，不端着写温吞水。',
            'cadence': '铺垫与日常句式顺畅紧凑，进入对抗、破境、反杀瞬间骤切短句+精确动词（劈/碾/掠/攥/贯），拳拳到肉。',
            'psychic_distance': '主角目标明确、行动力强，面对压迫的憋闷与破局后的痛快都要写足，让读者实实在在跟着出一口气。',
            'dialogue_texture': '对手嚣张有其利害底气而非纯傻瓜，主角反击靠实打实手段和干净台词压场，不靠长篇嘴炮讲道理。',
            'imagery_budget': '重点场面给足「蓄力前兆 → 爆发撞击 → 物理结果与旁人实感反馈」三拍，绝不三行草草带过。',
            'pacing_payoff': '金手指/新能力首次亮相必须给足一整场戏；赢下来的成果实实在在改变后续处境，不被下一段坏消息立刻清零。',
        },
        'drift_redlines': [
            '严禁全靠旁观者反复喊“不可能！他怎么会这么强！”的廉价换皮震惊体充当爽感。',
            '严禁跳过阻力回合直接一招秒杀，或用“爆发恐怖力量”等抽象空话代替真实招式因果。',
            '严禁把全场最值得看的突破/亮相挤在两三行里一句“没工夫细想”带过。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'action_reveal',
                'label': '高燃出手与破局三拍',
                'bad_ai': '面对强敌的攻击，他毫不畏惧，体内灵力疯狂运转，一拳轰出，爆发出惊天动地的巨响，直接将对方震飞了出去，全场一片死寂。',
                'target_voice': '铁棍砸到头顶三寸，风声已经压得额发贴脸。他没退，左脚往青砖缝里狠狠一拧，肩背塌下半尺，整条右臂绷出弓弦般的脆响，迎着棍影斜递上去——咔嚓！拇指粗的精铁棍硬生生折成两截，半截飞出去钉进了三丈外的梁柱，嗡嗡直颤。',
                'why': '压迫距离→发力支点→精铁折断钉柱的物理结果，无需喊“惊天动地”读者已感到力度。',
            },
            {
                'scene_function': 'confrontation',
                'label': '强弱反差压场',
                'bad_ai': '长老冷笑道：“凭你也配参加大比？”主角眼神坚定地回答：“三十年河东，三十年河西，今天我就要证明给你看！”',
                'target_voice': '执事翻着名册头也不抬：“外门垫底的，交十块灵石押金，打输了不退。”他反手把那块带着血痂的妖兽骨牌拍在案上，木桌咯吱一沉：“押金免了，把乙字三号擂台的名字划掉，写我的。”',
                'why': '用实打实的筹码和干脆动作压场，删掉陈旧口号和无营养嘴炮。',
            },
            {
                'scene_function': 'opening_hook',
                'label': '开篇压迫与能力初显',
                'bad_ai': '他穿越到了玄幻世界，获得了神秘系统，从此踏上了逆袭之路。此时，反派正带着人来找他麻烦。',
                'target_voice': '验脉石亮到第三息就暗了下去，台下哄笑声刚起，他掌心那道发烫的旧疤突然往里一缩——石碑底座裂开一条细缝，把台上执事刚测出的七品灵气硬生生抽走了半成。',
                'why': '当场抛出窘境+奇异异象+可追问后果，一步到位建立期待。',
            },
        ],
    },
    {
        'id': 'VOICE_LIGHT_WIT',
        'name': '轻快吐槽日常流',
        'tagline': '活人感鲜活吐槽 + 处境反差喜剧 + 轻松不失主线抓力',
        'recommended_genres': ('GENRE_QINGXIAOSHUO', 'GENRE_ERCIYUAN', 'GENRE_GAOXIAO', 'GENRE_ZHONGDIAN'),
        'incompatible_genres': ('GENRE_KONGBU', 'GENRE_LISHI', 'GENRE_JUNSHI'),
        'aligned_tones': ('TONE_LIGHT', 'TONE_HUMOROUS', 'TONE_WARM', 'TONE_SATIRICAL'),
        'aligned_styles': ('STYLE_LIGHT', 'STYLE_HUMOROUS', 'STYLE_WARM', 'STYLE_FAST'),
        'default_knobs': {
            'register': 'colloquial_street',
            'cadence': 'smooth_flow',
            'dialogue_mind': 'witty_banter',
            'anti_drift_bans': ['no_translationese', 'no_idiom_stacking', 'no_narrator_preaching', 'no_inventory_ledger'],
        },
        'dimensions': {
            'register': '轻快活泼的现代口语或生活化白话，保留自然语气词、停顿和人物自己的小算盘，读着像真人面对面聊天。',
            'cadence': '节奏轻盈有弹性，日常拌嘴与小反转一气呵成；遇到正经危机立刻收起嬉皮笑脸，张弛分明。',
            'psychic_distance': '极贴近主角内心吐槽，幽默必须从“主角真在意的利益、误会或窘境”里长出来，绝不靠旁白站外面抖机灵。',
            'dialogue_texture': '配角各有各的固执、抠门、傲娇或脑回路，接话自然跑偏或互相拆台，绝不为搞笑让角色变成无脑捧哏。',
            'imagery_budget': '抓生活感小动作与反差细节（比如拿三千斤铜钟当掩体却只围了块抹布），少冗长风景描写。',
            'pacing_payoff': '保持高频率小趣味与生活实感，同时主线盼头不能断；搞笑过后仍要推进真实处境或关系变化。',
        },
        'drift_redlines': [
            '严禁危险关头主角为了一句俏皮话忘记眼前性命威胁或核心目标。',
            '严禁叙述者跳出视角用“好嘛/行吧/真不愧是”硬逗乐（事情本身不好笑，别靠句子强逗）。',
            '严禁把所有配角写成同一个贫嘴腔调，遮住名字必须能分出谁在说话。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'dialogue_daily',
                'label': '处境反差喜剧对白',
                'bad_ai': '姑娘怒道：“你这个淫贼！”他心里暗暗吐槽：好嘛，刚穿越就被当成淫贼，这开局真是绝了，于是幽默地回答：“姑娘你误会了。”',
                'target_voice': '“不是淫贼，你光着膀子躲在我家钟室做什么？偷钟？”他扭头看了一眼那口一人多高的铜钟，又低头看看自己两条细胳膊，小心翼翼道：“姑娘，这钟少说三千斤，我搬不动……”“所以你是淫贼。”剑尖又往前送了半分。',
                'why': '笑点完全长在荒诞处境与双方各自的死理里，零出戏旁白吐槽。',
            },
            {
                'scene_function': 'confrontation',
                'label': '轻快交锋不失紧迫',
                'bad_ai': '反派得意地大笑，主角却毫不在意地吹了声口哨，调侃了一句网络热梗，把反派气得跳脚。',
                'target_voice': '债主拍着桌子算利滚利，他全程点头称是，顺手把桌上那盘瓜子磕了一半，等对方喘气才把手机转过去：“哥，你刚才算的那套复利我录下来了，按今年新规，这利率咱们去所里聊还是在这儿重新按计算器？”',
                'why': '用机灵但站得住脚的实操反制制造痛快感，不靠降智反派和尬梗。',
            },
            {
                'scene_function': 'emotional_shock',
                'label': '轻松底色下的真心触动',
                'bad_ai': '平时爱开玩笑的他此刻突然变得深沉起来，内心感慨万千，意识到友情的可贵。',
                'target_voice': '他张嘴本想顺口损两句，话到舌尖看见对方袖口磨得起毛的旧棉线，忽然卡住了，干咳一声把多买的那份热豆浆往人手里一塞：“买一送一的，别瞎想，喝不完倒了怪可惜。”',
                'why': '人物还是原来那个嘴硬性子，情绪藏在别扭动作里，绝不突然端起鸡汤腔。',
            },
        ],
    },
    {
        'id': 'VOICE_EPIC_ATMOSPHERE',
        'name': '厚重史诗与诡秘氛围流',
        'tagline': '异域感官渗透 + 远近镜头交替 + 未知压迫与宏阔质感',
        'recommended_genres': ('GENRE_QIHUAN', 'GENRE_KEHUAN', 'GENRE_LINGYI', 'GENRE_KONGBU', 'GENRE_SAIBO', 'GENRE_WEILAI'),
        'incompatible_genres': ('GENRE_GAOXIAO', 'GENRE_QINGCHUN'),
        'aligned_tones': ('TONE_EPIC', 'TONE_DARK', 'TONE_SERIOUS', 'TONE_DISTANT'),
        'aligned_styles': ('STYLE_EPIC', 'STYLE_FANTASY', 'STYLE_HORROR', 'STYLE_DARK', 'STYLE_POETIC'),
        'default_knobs': {
            'register': 'atmospheric_poetic',
            'cadence': 'measured_layered',
            'dialogue_mind': 'restrained_subtext',
            'anti_drift_bans': ['no_modern_slang', 'no_idiom_stacking', 'no_narrator_preaching', 'no_telegraph_chop'],
        },
        'dimensions': {
            'register': '沉稳有质感、带世界观独特物质肌理的叙述语言；用齿轮、潮雾、铁锈、星尘、仪轨等实存物象立起异域真实感。',
            'cadence': '远景压城与近景呼吸交替推进；信息量大的世界背景掰碎藏进人物日常与行动，绝不开篇整段丢设定说明书。',
            'psychic_distance': '在宏大尺度和个体微末感之间制造落差：世界越庞大诡谲，人物手头具体的一点痛、冷、犹豫越要写实。',
            'dialogue_texture': '不同阵营、阶层、学派或种族有各自称谓与行话惯性，保持克制与未知感，不主动给主角做免费设定导游。',
            'imagery_budget': '重触觉、听觉、嗅觉与光影温度变化（如湿冷煤烟、失真回声、金属味），每处异象有清晰物理后果。',
            'pacing_payoff': '恐怖/诡秘靠克制留白与规则边界逼近制造后劲；史诗靠个体抉择撬动庞大格局，不靠空洞宏大形容词轰炸。',
        },
        'drift_redlines': [
            '严禁在开篇连写五百字世界起源、纪元编年或阵营说明书。',
            '严禁堆砌“不可名状的恐惧、难以言喻的宏伟、令人窒息的压迫感”等虚空大词。',
            '严禁把所有外星/异界/古老存在写成同一个现代高中生说话腔调。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'opening_hook',
                'label': '世界观半透明渗入',
                'bad_ai': '这是一个由蒸汽与神秘力量统治的时代，七大教会掌控着世界秩序，夜晚的雾气中潜伏着不可名状的怪物。',
                'target_voice': '钟楼敲过十一下，街灯里的鲸油火苗齐齐矮了一寸。巡夜人把铜哨含进嘴里，先抬头确认屋檐上那排石像今天还是七座，才推开锈死的铁门。',
                'why': '用巡夜人“数石像”的日常习惯瞬间立起诡秘世界规则，零设定说明文。',
            },
            {
                'scene_function': 'action_reveal',
                'label': '异象与规则冲击',
                'bad_ai': '封印突然破碎，一股不可名状的恐怖气息瞬间笼罩了整个大厅，众人都感到灵魂在颤栗。',
                'target_voice': '青铜匣开了一条指宽的缝，屋里没有风，墙上所有挂钟的秒针却同时往回跳了三格。离匣子最近的提灯灭了，玻璃罩内壁瞬间凝出一层白霜，映出他身后多出来的一道矮影子。',
                'why': '用时钟倒跳、灯灭结霜与多出的影子写诡异压迫，比“不可名状”真实十倍。',
            },
            {
                'scene_function': 'confrontation',
                'label': '阵营声线与宏大格局',
                'bad_ai': '大主教威严地说：“你们这些异端必将受到惩罚。”反抗军首领不甘示弱：“我们是为了自由而战！”',
                'target_voice': '“冬港今年少了三成粮税，圣座只问一句：是海雾吃掉了船，还是领主大人替海雾收了税？”高阶教士翻过羊皮卷，“至于城外那些冻死的矿工，不在本季账册之内。”',
                'why': '冷酷的制度语言和账册措辞自然透出阶层压迫与世界格局，无需空喊口号。',
            },
        ],
    },
    {
        'id': 'VOICE_EMOTION_TENSION',
        'name': '细腻情感拉扯流',
        'tagline': '精准捕捉关系微差、克制回避与情绪递进，写出让人心动或揪心的真实感',
        'recommended_genres': ('GENRE_YANQING', 'GENRE_QINGCHUN', 'GENRE_CHENGZHANG'),
        'incompatible_genres': ('GENRE_KONGBU', 'GENRE_MOSHI', 'GENRE_JUNSHI'),
        'aligned_tones': ('TONE_WARM', 'TONE_INTIMATE', 'TONE_LIGHT', 'TONE_SERIOUS'),
        'aligned_styles': ('STYLE_ROMANTIC', 'STYLE_WARM', 'STYLE_SLOW', 'STYLE_POETIC', 'STYLE_GROWTH'),
        'default_knobs': {
            'register': 'modern_plain',
            'cadence': 'smooth_flow',
            'dialogue_mind': 'vivid_thought_sharp_talk',
            'anti_drift_bans': ['no_translationese', 'no_idiom_stacking', 'no_narrator_preaching', 'no_telegraph_chop'],
        },
        'dimensions': {
            'register': '干净、细腻、有温度的叙述语言；准确写出亲近、试探、委屈、嘴硬或心动时的细微落差，不矫情做作。',
            'cadence': '对手戏舍得留呼吸与停顿，把一次对视、半句迟疑、收回的手写透；普通过渡干净简写不拖水。',
            'psychic_distance': '重要情绪来时，先写人物此刻最在意、最怕失去或最不敢认的那一层真实念头，让感受驱动接下来的说话与选择。',
            'dialogue_texture': '重视答非所问、改口、沉默与称呼变化；人物说的话既符合性格又带着关系里的小心思和防备。',
            'imagery_budget': '细节聚焦在对方身上会被视角人物盯住的细节（袖口、停顿半拍的动作、语尾变轻），而非泛泛描写长相多美。',
            'pacing_payoff': '情感推进靠一次次具体事件里的偏爱、误解、并肩与取舍累加，绝不无铺垫突然深情告白或强行煽情。',
        },
        'drift_redlines': [
            '严禁空泛形容“她美得惊心动魄/他深邃的眼眸里藏着无尽温柔”等工业言情套话。',
            '严禁先写人物心里平平淡淡，再强行补一句“他的心漏跳了一拍/眼眶湿润了”。',
            '严禁凭空编造惨痛往事硬煽情，情绪必须从眼前这段关系里的实事长出来。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'dialogue_daily',
                'label': '关系拉扯与口是心非',
                'bad_ai': '他深情地看着她，温柔地说：“你别太累了，我会心疼的。”她的脸一下子红了，心跳加速，害羞地低下了头。',
                'target_voice': '他把多出来的那把伞塞进她包侧袋，拉链拉到一半卡住了，干脆低头帮她扯平：“顺路买的，办公室放不下。”她盯着他手背还没消下去的红痕，没拆穿，只小声道：“那明天我还你。”“不急，下周还有雨。”',
                'why': '偏爱藏在顺手动作和留后路的话里，零“深情/脸红/心跳加速”套词。',
            },
            {
                'scene_function': 'emotional_shock',
                'label': '委屈与失落真实过程',
                'bad_ai': '看到他维护别人，她感到心如刀割，一股委屈涌上心头，泪水在眼眶里打转。',
                'target_voice': '他说完那句“她只是不懂事”，客厅里安静了两秒。她把原本要递过去的胃药放回茶几，指尖在药盒边停了一下，还是收回手笑了笑：“行，那你们先聊，我回屋把明天的方案改完。”',
                'why': '把“原本想给的关怀收回”这个具体选择演出来，比“心如刀割”扎心十倍。',
            },
            {
                'scene_function': 'confrontation',
                'label': '摊牌与情绪爆发',
                'bad_ai': '她愤怒地大喊：“你根本就不懂我！我们之间已经没有信任了！”说完便哭着跑开了。',
                'target_voice': '“你每次都这样。”她没有提高声音，只把钥匙轻轻搁在玄关柜上，“出事的时候把我挡在门外，事后拿一句‘为你好’盖章。你不是怕我吃亏，你是压根不信我能跟你一块儿扛。”',
                'why': '字字落在具体相处模式与核心痛点上，人物有尊严有脑子，不靠嚎叫和跑开制造冲突。',
            },
        ],
    },
    {
        'id': 'VOICE_STRATEGIC_GROUP',
        'name': '权谋博弈与群像层次流',
        'tagline': '各方皆有利害算盘 + 话中有话交锋 + 群像声线各异不撞脸',
        'recommended_genres': ('GENRE_QUANMOU', 'GENRE_LISHI', 'GENRE_SHANGZHAN'),
        'incompatible_genres': ('GENRE_GAOXIAO', 'GENRE_QINGCHUN'),
        'aligned_tones': ('TONE_SERIOUS', 'TONE_COLD', 'TONE_SATIRICAL', 'TONE_EPIC'),
        'aligned_styles': ('STYLE_STRATEGIC', 'STYLE_GROUP', 'STYLE_SERIOUS', 'STYLE_GRITTY'),
        'default_knobs': {
            'register': 'semi_classical',
            'cadence': 'measured_layered',
            'dialogue_mind': 'restrained_subtext',
            'anti_drift_bans': ['no_modern_slang', 'no_idiom_stacking', 'no_narrator_preaching', 'no_translationese'],
        },
        'dimensions': {
            'register': '沉着老练、重制度与利害分寸的叙述语言；用权责、筹码、人情、把柄等现实杠杆驱动每一段戏。',
            'cadence': '议事与博弈铺陈有章法，信息一层层换手；真正掀桌或反转处干脆利落，不啰嗦复盘计谋。',
            'psychic_distance': '主角聪明靠信息拼图与人性推演，但他人同样各怀鬼胎、不会配合降智；切忌用上帝视角替读者解释“其实主角早算到了”。',
            'dialogue_texture': '群像场面每人说话各带立场、年龄与阶层口吻：有人打太极、有人递刀子、有人装糊涂，遮住名字就能分清是谁。',
            'imagery_budget': '聚焦座次、眼神递交、茶水添减、文书落印等权力场域微细节，少无关风景。',
            'pacing_payoff': '一局落定必须留下新的权力格局变动与未了账目，让各方在下一回继续反制，绝不一劳永逸。',
        },
        'drift_redlines': [
            '严禁全员配合主角走流程或反派突然看不见明摆着的陷阱（降智衬托智斗）。',
            '严禁事后安排一段冗长的“主角向跟班复盘自己刚才怎么一步步算计的”说明文。',
            '严禁群像里五个人说话全是同一套腔调、连停顿和称呼都一模一样。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'confrontation',
                'label': '多方权力场交锋',
                'bad_ai': '宰相和将军在朝堂上针锋相对，各自发表了长篇大论，气氛十分紧张，皇帝则高深莫测地看着他们。',
                'target_voice': '户部尚书刚念完西北欠饷的折子，兵部侍郎就咳嗽了一声：“去年冬衣也是户部批的，怎么送到凉州少了四成？”主位上没说话，只把茶盖轻轻一磕。原本低头数靴尖的御史立刻出列：“臣倒听说，那批布匹在陕州换过两回船。”',
                'why': '三方各打各的算盘、一句话把火引向新靶子，主位一磕茶盖胜过百字旁白。',
            },
            {
                'scene_function': 'dialogue_daily',
                'label': '递筹码不挑明',
                'bad_ai': '他聪明地分析道：“如果我们联手，就能扳倒对方，这对我们双方都有好处，你觉得呢？”',
                'target_voice': '“下月初三盐引换照，南边那两位怕是凑不齐现银。”他把名帖压在砚台底下，“我手里多两张旧契，搁着也是生虫，就看周大人那日得不得空喝这杯茶了。”',
                'why': '只摆条件和时限，不替对方做结论，把博弈空间留给对手反应。',
            },
            {
                'scene_function': 'emotional_shock',
                'label': '算漏与反制受挫',
                'bad_ai': '他没想到对方竟然留了一手，顿时脸色大变，懊恼地发现自己中计了。',
                'target_voice': '快马报进门的时候，棋盘上那枚白子还捏在他指间。他盯着信纸末尾那个陌生官印看了足足十息，才把白子放回盒里——不是对方动作快，是半个月前递出来的那份假账，压根就是冲着他案头来的。',
                'why': '冷静复盘错在哪里（信息差与对手藏得深），既显受挫分量又不降智。',
            },
        ],
    },
    {
        'id': 'VOICE_GENRE_HYBRID_BALANCED',
        'name': '全能平衡叙事流',
        'tagline': '稳健百搭，兼顾画面实感、人物活气与多题材融合边界',
        'recommended_genres': (),
        'incompatible_genres': (),
        'aligned_tones': ('TONE_SERIOUS', 'TONE_WARM', 'TONE_LIGHT', 'TONE_COLD'),
        'aligned_styles': ('STYLE_REALISTIC', 'STYLE_GROWTH', 'STYLE_SUSPENSE', 'STYLE_FAST'),
        'default_knobs': {
            'register': 'modern_plain',
            'cadence': 'smooth_flow',
            'dialogue_mind': 'vivid_thought_sharp_talk',
            'anti_drift_bans': ['no_translationese', 'no_narrator_preaching', 'no_inventory_ledger', 'no_telegraph_chop'],
        },
        'dimensions': {
            'register': '平实自然、贴合当前主副题材语境的通用成熟网文语体，不偏科、不造作，遇多题材融合时以主类型语体压阵。',
            'cadence': '叙述流畅完整，平缓戏留出人物相处空间，冲突戏自动收短句长、突出动作因果与后果。',
            'psychic_distance': '贴着视角人物写感受、判断与选择，保留有效心理与自然反应，严格守住知情边界。',
            'dialogue_texture': '对白紧接眼前事态与人物利害，允许犹豫、打断和各人脾气，不轮流播报设定。',
            'imagery_budget': '围绕推动情节或映照情绪的具象细节落笔，每场至少一处让读者记住的画面或物件动作。',
            'pacing_payoff': '一章至少推进一件主角做成或改变局面的实事，章尾停在具体未了事态上。',
        },
        'drift_redlines': [
            '严禁在多题材融合时前后语体割裂（前段古风、后段突然冒出廉价现代吐槽）。',
            '严禁把设定解释、物品去向与规则限制堆进正文充数。',
            '严禁全章情绪一条直线，毫无起伏或强行每段套微动作模板。',
        ],
        'micro_contrasts': [
            {
                'scene_function': 'confrontation',
                'label': '有阻力的现场推进',
                'bad_ai': '他决定说服对方帮忙，于是耐心解释了事情的重要性，对方听完后觉得很有道理，立刻答应了下来。',
                'target_voice': '“这趟活我不接。”对方把工具箱扣上，“上回替你们修旧闸，差点把右手搭进去。”他没急着加钱，只把那张缺了一角的旧名单放在箱盖上：“这次死的不是外人，是老周。”对方按在锁扣上的手停住了。',
                'why': '用真实顾虑和直戳要害的筹码推动让步，拒绝全员讲道理顺推。',
            },
            {
                'scene_function': 'emotional_shock',
                'label': '先写最强感受再写动作',
                'bad_ai': '屋里很冷，被子很薄，墙角长着青苔。他躺在床上，忽然想起白天见过的那块墓碑，心里有些难过。',
                'target_voice': '白天刚对着她笑过，夜里却先记起那块刻着她名字的旧碑。这念头一冒出来，屋里那点柴火暖气像一下子散光了，他翻身坐起，摸黑去扯搭在床尾的棉袄。',
                'why': '最重要那层情绪开头直给，环境细节顺着情绪带出，不绕远路。',
            },
            {
                'scene_function': 'opening_hook',
                'label': '具体局面开局',
                'bad_ai': '故事发生在一个不寻常的夜晚，主角正面临人生中最大的危机，一切都将从这里改变。',
                'target_voice': '距离封港只剩两刻钟，通行牌还在掌柜手里扣着。他把最后三两碎银推过柜台，掌柜却连眼皮都没抬，慢吞吞拿镇纸压住了那张写着他名字的旧纸。',
                'why': '时间紧迫、筹码受阻、对手施压三要素两句话立住开局。',
            },
        ],
    },
)

VOICE_BASE_MAP: dict[str, dict[str, Any]] = {v['id']: v for v in VOICE_BASES}

# Executable micro-directives upgrading legacy TONE_* / STYLE_* IDs from vague adjectives to concrete craft.
TONE_EXECUTION_HINTS: dict[str, str] = {
    'TONE_SERIOUS': '正剧分量：重要利害和抉择不轻佻化，人物面对真实代价时的反应写足分量。',
    'TONE_LIGHT': '轻快透气：日常与推进段保持明快呼吸，不无故沉重苦大仇深，允许处境带出的自然轻松感。',
    'TONE_HUMOROUS': '处境幽默：笑点从人物性格反差、误会与小算盘长出来，不靠旁白硬吐槽或危险时刻忘本职。',
    'TONE_DARK': '压迫暗调：通过规则冷酷、退路收窄与艰难取舍体现压抑，不靠血腥形容词硬堆。',
    'TONE_WARM': '温情底色：人与人之间的照应藏在递东西、留余地、默默兜底等具体小动作里，不喊温暖口号。',
    'TONE_COLD': '冷峻克制：情绪不外泄泛滥，用短停顿、偏离视线、克制措辞呈现暗涌，但冷峻≠无情绪面瘫。',
    'TONE_SATIRICAL': '锋利反讽：把表面冠冕堂皇的说辞与背后赤裸利害并排摆出，让读者自己笑出凉意，旁白不点破。',
    'TONE_EPIC': '宏阔格局：让个人处境与大时代/大世界变动互相咬合，用具体人群命运映出规模而非空喊宏大。',
    'TONE_INTIMATE': '贴身亲近：贴紧 POV 呼吸与私密念头，放大两人独处时的细微语调与沉默张力。',
    'TONE_DISTANT': '客观留白：拉远半步叙述距离，多呈现行为与客观结果，减少替角色辩护或抒情。',
}

STYLE_EXECUTION_HINTS: dict[str, str] = {
    'STYLE_REALISTIC': '写实肌理：衣食住行、金钱时间与社会规矩合乎常识，细节落地不悬浮。',
    'STYLE_FANTASY': '奇异可感：超凡现象写出具体感官异象、触发条件与使用代价，让读者一眼信服。',
    'STYLE_EPIC': '史诗层次：大场面先立空间坐标与多方动向，再落回核心人物的关键抉择。',
    'STYLE_DARK': '暗黑张力：困境真实有代价，胜出也留疤痕或道德两难，不廉价大团圆。',
    'STYLE_LIGHT': '轻爽节奏：小挫折快解、日常有趣味，读者持续拿到轻松愉快的阅读回报。',
    'STYLE_HUMOROUS': '诙谐活气：对白有来有往带调侃机锋，保持角色各自鲜明怪癖与脾气。',
    'STYLE_SERIOUS': '沉稳厚重：叙述克制扎实，人物动机经得起追问，不靠巧合和降智推进。',
    'STYLE_GRITTY': '粗粝生猛：动作、环境与人性带泥土与铁锈味，不把世界磨皮成精致布景。',
    'STYLE_POETIC': '意象留白：关键节点用 1–2 句凝练实景意象定格余韵，克制不堆砌华丽辞藻。',
    'STYLE_ACTION': '动作利落：交手写清站位、蓄力、碰撞与物理后果，短句精准动词推进。',
    'STYLE_SUSPENSE': '悬念递进：线索与猜测分开写，保留未揭晓信息差，章尾停在具体悬而未决处。',
    'STYLE_HORROR': '克制惊悚：靠日常秩序里的微小异常、空间封闭与规则违背制造寒意，少直白嘶吼。',
    'STYLE_ROMANTIC': '情感拉扯：捕捉称呼、眼神、犹豫与偏爱的细微变化，给足关系发酵空间。',
    'STYLE_GROWTH': '成长实证：面对相似困局时，用主角前后不同的判断与出手方式证明真的变强了。',
    'STYLE_GROUP': '群像辨识：出场配角各有独立目的与独特说话节奏，不沦为主角附庸。',
    'STYLE_STRATEGIC': '谋略交锋：算计建立在有限信息与对手真实利害之上，绝不靠反派降智衬托。',
    'STYLE_WARM': '烟火治愈：细腻写清日常相处里的体谅与互助，让人物真正享受做成事后的好日子。',
    'STYLE_COLD': '冷冽留锋：措辞精炼克制、少多余修饰，情绪压在台词与克制动作底下。',
    'STYLE_FAST': '紧凑快拍：省去无效寒暄与重复铺垫，每场直奔矛盾核心并产出明确局势变化。',
    'STYLE_SLOW': '缓拍蓄势：重要对手戏与情绪转折舍得展开过程与停顿，把氛围与关系做厚。',
}

# Coarse register families used to auto-compute excluded_types for decomposed voice fingerprints
# so classical/xuanhuan prose never pollutes modern urban/suspense books (and vice versa).
_REGISTER_FAMILIES: dict[str, frozenset[str]] = {
    'classical_fantastic': frozenset({'GENRE_XIANXIA', 'GENRE_WUXIA', 'GENRE_XUANHUAN', 'GENRE_LISHI', 'GENRE_QUANMOU'}),
    'modern_realistic': frozenset({'GENRE_DUSHI', 'GENRE_XIANSHI', 'GENRE_ZHIYE', 'GENRE_SHANGZHAN', 'GENRE_XUANYI', 'GENRE_TUILI', 'GENRE_QINGCHUN', 'GENRE_TIYU'}),
    'speculative_dark': frozenset({'GENRE_QIHUAN', 'GENRE_KEHUAN', 'GENRE_SAIBO', 'GENRE_WEILAI', 'GENRE_MOSHI', 'GENRE_LINGYI', 'GENRE_KONGBU'}),
    'light_playful': frozenset({'GENRE_QINGXIAOSHUO', 'GENRE_ERCIYUAN', 'GENRE_YOUXI', 'GENRE_DIANJING', 'GENRE_TONGREN'}),
}


def excluded_types_for_genres(type_ids: list[str] | tuple[str, ...]) -> list[str]:
    """Compute clearly incompatible main genres so decomposed voice fingerprints never cross-contaminate."""
    normalized = set(canonical_types(list(type_ids))) if type_ids else set()
    if not normalized:
        return []
    in_classical = bool(normalized & _REGISTER_FAMILIES['classical_fantastic'])
    in_modern = bool(normalized & _REGISTER_FAMILIES['modern_realistic'])
    in_spec = bool(normalized & _REGISTER_FAMILIES['speculative_dark'])
    excluded: set[str] = set()
    if in_classical and not in_modern:
        excluded |= (_REGISTER_FAMILIES['modern_realistic'] - {'GENRE_SHANGZHAN'})
    elif in_modern and not in_classical:
        excluded |= {'GENRE_XIANXIA', 'GENRE_WUXIA', 'GENRE_XUANHUAN'}
    if in_spec and not in_classical:
        excluded |= {'GENRE_XIANXIA', 'GENRE_WUXIA'}
    return sorted(excluded - normalized)


def recommend_voice_bases(types: list[str] | tuple[str, ...] | None) -> list[dict[str, Any]]:
    """Return all 9 built-in voice bases ranked for the chosen genres."""
    normalized = canonical_types(list(types)) if types else []
    primary = normalized[0] if normalized else ''
    type_set = set(normalized)

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for idx, base in enumerate(VOICE_BASES):
        rec = set(base['recommended_genres'])
        incompat = set(base['incompatible_genres'])
        if primary and primary in rec:
            tier, label = 0, '本类型首选'
        elif type_set & rec:
            tier, label = 1, '契合副类型'
        elif base['id'] == 'VOICE_GENRE_HYBRID_BALANCED':
            tier, label = 1 if not normalized else 2, '通用稳健'
        elif primary and primary in incompat:
            tier, label = 3, '跨题材慎用'
        else:
            tier, label = 2, '按需可选'
        item = deepcopy(base)
        item['relevance'] = ('primary' if tier == 0 else ('optional' if tier <= 2 else 'out_of_scope'))
        item['relevance_label'] = label
        ranked.append((tier, idx, item))
    ranked.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in ranked]


def default_voice_base_id(types: list[str] | tuple[str, ...] | None) -> str:
    ranked = recommend_voice_bases(types)
    return ranked[0]['id'] if ranked else 'VOICE_GENRE_HYBRID_BALANCED'


def normalize_knobs(raw_knobs: dict[str, Any] | None, *, base_id: str) -> dict[str, Any]:
    base = VOICE_BASE_MAP.get(base_id) or VOICE_BASE_MAP['VOICE_GENRE_HYBRID_BALANCED']
    defaults = deepcopy(base['default_knobs'])
    if not isinstance(raw_knobs, dict):
        return defaults
    out = dict(defaults)
    for key in ('register', 'cadence', 'dialogue_mind'):
        val = str(raw_knobs.get(key) or '').strip()
        if val and val in _KNOB_OPTION_MAP[key]:
            out[key] = val
    if 'anti_drift_bans' in raw_knobs and isinstance(raw_knobs['anti_drift_bans'], list):
        valid_bans = [str(x).strip() for x in raw_knobs['anti_drift_bans'] if str(x).strip() in _KNOB_OPTION_MAP['anti_drift_bans']]
        out['anti_drift_bans'] = list(dict.fromkeys(valid_bans))
    return out


def compile_book_voice_spec(
    genre_ids: list[str] | tuple[str, ...] | None,
    *,
    base_voice_id: str | None = None,
    knobs: dict[str, Any] | None = None,
    tone_ids: list[str] | tuple[str, ...] = (),
    style_ids: list[str] | tuple[str, ...] = (),
    fingerprints: list[dict[str, Any]] = (),
    custom_notes: str = '',
    enabled: bool = True,
) -> dict[str, Any]:
    """Compile built-in base voice + 4 orthogonal knobs + legacy tone/style hints +
    decomposed same-genre voice fingerprints into ONE executable Book Voice Spec.
    """
    normalized_genres = canonical_types(list(genre_ids)) if genre_ids else []
    chosen_base_id = base_voice_id if (base_voice_id in VOICE_BASE_MAP) else default_voice_base_id(normalized_genres)
    base = VOICE_BASE_MAP[chosen_base_id]
    eff_knobs = normalize_knobs(knobs, base_id=chosen_base_id)

    # Start with base 6 dimensions, then apply orthogonal knob refinements when customized.
    dimensions = dict(base['dimensions'])
    reg_opt = _KNOB_OPTION_MAP['register'].get(eff_knobs['register'])
    if reg_opt and eff_knobs['register'] != base['default_knobs']['register']:
        dimensions['register'] = f"{reg_opt['directive']}（叠加基座：{base['dimensions']['register']}）"
    cad_opt = _KNOB_OPTION_MAP['cadence'].get(eff_knobs['cadence'])
    if cad_opt and eff_knobs['cadence'] != base['default_knobs']['cadence']:
        dimensions['cadence'] = f"{cad_opt['directive']}（叠加基座：{base['dimensions']['cadence']}）"
    dm_opt = _KNOB_OPTION_MAP['dialogue_mind'].get(eff_knobs['dialogue_mind'])
    if dm_opt and eff_knobs['dialogue_mind'] != base['default_knobs']['dialogue_mind']:
        dimensions['dialogue_texture'] = f"{dm_opt['directive']}（叠加基座：{base['dimensions']['dialogue_texture']}）"

    # Collect drift redlines from base + selected anti-drift ban knobs.
    drift_redlines: list[str] = list(base['drift_redlines'])
    for ban_id in eff_knobs.get('anti_drift_bans', ()):
        opt = _KNOB_OPTION_MAP['anti_drift_bans'].get(ban_id)
        if opt and opt['directive'] not in drift_redlines:
            drift_redlines.append(opt['directive'])

    # Upgrade chosen legacy TONE_* / STYLE_* into concrete execution notes.
    legacy_hints: list[str] = []
    for tid in tone_ids or ():
        if hint := TONE_EXECUTION_HINTS.get(str(tid)):
            legacy_hints.append(hint)
    for sid in style_ids or ():
        if hint := STYLE_EXECUTION_HINTS.get(str(sid)):
            legacy_hints.append(hint)

    # Filter and attach compatible decomposed voice fingerprints (strictly rejecting excluded-genre collisions).
    genre_set = set(normalized_genres)
    attached_fps: list[dict[str, Any]] = []
    for fp in fingerprints or ():
        if not isinstance(fp, dict):
            continue
        fp_excluded = set(fp.get('excluded_types') or ())
        if genre_set and (genre_set & fp_excluded):
            continue
        body = fp.get('body') if isinstance(fp.get('body'), dict) else fp
        attached_fps.append({
            'id': str(fp.get('id') or ''),
            'title': str(fp.get('title') or body.get('title') or '参考语感指纹'),
            'book_id': str(fp.get('book_id') or ''),
            'base_voice_id': str(fp.get('base_voice_id') or chosen_base_id),
            'type_tags': list(fp.get('type_tags') or ()),
            'scene_functions': list(fp.get('scene_functions') or body.get('scene_functions') or ()),
            'dimensions': dict(body.get('dimensions') or {}),
            'techniques': list(body.get('techniques') or ())[:4],
            'drift_guards': list(body.get('drift_guards') or ())[:3],
            'scene_function_notes': dict(body.get('scene_function_notes') or {}),
        })
        for dg in (body.get('drift_guards') or ())[:2]:
            dg_text = str(dg).strip()
            if dg_text and dg_text not in drift_redlines:
                drift_redlines.append(dg_text)

    notes_clean = str(custom_notes or '').strip()[:800]
    spec: dict[str, Any] = {
        'version': 1,
        'enabled': bool(enabled),
        'genre_ids': normalized_genres,
        'base_voice_id': chosen_base_id,
        'base_voice_name': base['name'],
        'tagline': base['tagline'],
        'knobs': eff_knobs,
        'dimensions': dimensions,
        'drift_redlines': drift_redlines[:8],
        'micro_contrasts': deepcopy(base['micro_contrasts']),
        'legacy_tone_style_hints': legacy_hints[:4],
        'fingerprints': attached_fps[:3],
        'fingerprint_ids': [fp['id'] for fp in attached_fps[:3] if fp.get('id')],
        'custom_notes': notes_clean,
        'style_whitelist': [],
        'updated_at': now(),
    }
    spec['sha256'] = content_sha256({k: v for k, v in spec.items() if k not in ('updated_at', 'sha256')})
    return spec


# ---------- Scene-function inference & Step 15/16 packets ----------

def infer_scene_function(scene_body: dict[str, Any] | None, *, chapter_index: int | None = None, scene_index: int | None = None) -> str:
    """Deterministically infer the dominant dramatic function of a scene for micro-contrast matching."""
    body = scene_body or {}
    if chapter_index == 1 and (scene_index in (None, 1)):
        return 'opening_hook'
    blob = ' '.join(str(body.get(k) or '') for k in ('title', 'goal', 'conflict', 'function', 'entering_state', 'planned_result'))
    if any(w in blob for w in ('战斗', '交手', '搏杀', '打斗', '出招', '截杀', '突围', '破境', '突破', '亮相', '觉醒', '绝招', '斗法')):
        return 'action_reveal'
    if any(w in blob for w in ('噩耗', '崩溃', '背叛', '离别', '失落', '痛', '震惊', '悔', '动摇', '心碎', '告白', '泪')):
        return 'emotional_shock'
    if any(w in blob for w in ('对峙', '试探', '审讯', '交锋', '逼问', '谈判', '质问', '威胁', '压迫', '反制', '博弈', '拒认')):
        return 'confrontation'
    if any(w in blob for w in ('日常', '闲聊', '吃饭', '买', '相处', '拌嘴', '休整', '商量')):
        return 'dialogue_daily'
    return 'confrontation'


def build_writer_voice_packet(spec: dict[str, Any] | None, *, scene_function: str = 'confrontation') -> dict[str, Any] | None:
    """Compile a compact, executable Step 15 writer voice packet with scene-matched micro-contrasts."""
    if not isinstance(spec, dict) or not spec.get('enabled', True):
        return None
    learned = [c for c in (spec.get('learned_contrasts') or ()) if isinstance(c, dict)]
    learned_matched = [c for c in learned if c.get('scene_function') == scene_function]
    contrasts = list(spec.get('micro_contrasts') or ())
    matched = [c for c in contrasts if c.get('scene_function') == scene_function]
    others = [c for c in contrasts if c.get('scene_function') != scene_function]
    # Author's own confirmed edit contrasts take top priority over generic template contrasts!
    picked_contrasts = (learned_matched + matched + learned + others)[:2]

    fp_techniques: list[dict[str, Any]] = []
    for fp in (spec.get('fingerprints') or ())[:2]:
        entry: dict[str, Any] = {'source': fp.get('title') or '同题材语感指纹'}
        fn_note = (fp.get('scene_function_notes') or {}).get(scene_function)
        if fn_note:
            entry['for_this_scene'] = str(fn_note)[:220]
        if fp.get('techniques'):
            entry['techniques'] = [str(t)[:160] for t in fp['techniques'][:3]]
        fp_techniques.append(entry)

    packet: dict[str, Any] = {
        'voice_name': spec.get('base_voice_name') or spec.get('base_voice_id', ''),
        'scene_function': SCENE_FUNCTION_LABELS.get(scene_function, scene_function),
        'six_dimensions': spec.get('dimensions') or {},
        'drift_redlines': list(spec.get('drift_redlines') or ())[:8],
        'micro_contrasts': [
            {
                'label': c.get('label', ''),
                'avoid_ai': c.get('bad_ai', ''),
                'target_voice': c.get('target_voice', ''),
                'why': c.get('why', ''),
                **({'source': c['source']} if c.get('source') else {}),
            }
            for c in picked_contrasts
        ],
        'usage_rule': '按上述 6 维语言规范与防漂移红线落笔，参照正反微对照校准句式呼吸与用词质感；微对照仅校准语感，严禁照搬其中句式或元素。',
    }
    if spec.get('legacy_tone_style_hints'):
        packet['tone_style_focus'] = list(spec['legacy_tone_style_hints'])[:3]
    if fp_techniques:
        packet['decomposed_voice_fingerprints'] = fp_techniques
    if spec.get('custom_notes'):
        packet['author_voice_notes'] = str(spec['custom_notes'])[:500]
    return packet


def build_review_voice_guard_from_package(package: dict[str, Any] | None) -> str:
    """Extract the frozen Book Voice Spec drift redlines directly from the writing package for Step 16 review."""
    if not isinstance(package, dict):
        return ''
    for item in package.get('items', ()):
        if not isinstance(item, dict) or item.get('source') != 'voice-spec':
            continue
        try:
            body = json.loads(item.get('text') or '{}')
        except ValueError:
            return ''
        if not isinstance(body, dict):
            return ''
        vname = str(body.get('voice_name') or '').strip()
        redlines = [str(r).strip() for r in (body.get('drift_redlines') or ()) if str(r).strip()][:5]
        if not vname and not redlines:
            return ''
        joined = '；'.join(redlines)
        return f'【本书语感防漂移验收：{vname or "已定语感规范"}】核查正文是否守住本书选定语体，重点拦截：{joined}'
    return ''


# ---------- Per-project Voice Spec persistence ----------

def _voice_spec_path(store: Store) -> Path:
    return store.data_file(VOICE_SPEC_FILENAME)


def load_book_voice_spec(store: Store) -> dict[str, Any] | None:
    path = _voice_spec_path(store)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def save_book_voice_spec(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or not spec.get('base_voice_id'):
        raise ValueError('无效的本书语感规范卡')
    # Preserve existing book-local style_whitelist / learned_contrasts / learned_redlines when caller omits them
    existing = load_book_voice_spec(store)
    if isinstance(existing, dict):
        if 'style_whitelist' not in spec and isinstance(existing.get('style_whitelist'), list):
            spec = {**spec, 'style_whitelist': list(existing['style_whitelist'])}
        if 'learned_contrasts' not in spec and isinstance(existing.get('learned_contrasts'), list):
            spec = {**spec, 'learned_contrasts': list(existing['learned_contrasts'])}
        if 'learned_redlines' not in spec and isinstance(existing.get('learned_redlines'), list):
            spec = {**spec, 'learned_redlines': list(existing['learned_redlines'])}
    path = _voice_spec_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = NamedTemporaryFile('w', encoding='utf-8', newline='', dir=path.parent,
                                prefix='.voice-spec-', suffix='.tmp', delete=False)
    tmp = Path(staged.name)
    try:
        with staged:
            staged.write(json.dumps(spec, ensure_ascii=False, indent=2))
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return spec


def load_book_style_whitelist(store: Store | None) -> list[str]:
    """Load book-local literal exemptions (catchphrases, in-world idioms, deliberate stylistic phrases).

    Strictly book-local: NEVER shared across books!
    """
    if store is None:
        return []
    spec = load_book_voice_spec(store)
    if not isinstance(spec, dict):
        return []
    raw = spec.get('style_whitelist')
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in raw:
        s = str(item or '').strip()
        if 2 <= len(s) <= 80 and s not in seen:
            seen.add(s)
            cleaned.append(s)
    return cleaned[:60]


def save_book_style_whitelist(store: Store, items: list[str] | tuple[str, ...]) -> list[str]:
    """Persist book-local style whitelist literals inside `voice_spec.json`."""
    spec = load_book_voice_spec(store)
    if spec is None:
        spec = compile_book_voice_spec((), enabled=True)
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in (items or ()):
        s = str(item or '').strip()
        if 2 <= len(s) <= 80 and s not in seen:
            seen.add(s)
            cleaned.append(s)
    spec['style_whitelist'] = cleaned[:60]
    spec['updated_at'] = now()
    save_book_voice_spec(store, spec)
    return spec['style_whitelist']


# ---------- Library.db Multi-Genre Voice Fingerprint Registry ----------

def ensure_voice_fingerprint_table(conn: Any) -> None:
    conn.executescript(VOICE_FINGERPRINT_SCHEMA)


def save_voice_fingerprint(
    conn: Any,
    *,
    book_id: str,
    structure_version: int,
    title: str,
    base_voice_id: str,
    type_tags: list[str],
    body: dict[str, Any],
    status: str = 'approved',
    excluded_types: list[str] | None = None,
    scene_functions: list[str] | None = None,
    ts: str | None = None,
) -> dict[str, Any]:
    """Upsert a decomposed book's structured voice fingerprint in library.db."""
    ensure_voice_fingerprint_table(conn)
    norm_types = canonical_types(list(type_tags)) if type_tags else []
    eff_base = base_voice_id if base_voice_id in VOICE_BASE_MAP else default_voice_base_id(norm_types)
    eff_excluded = (
        canonical_types(list(excluded_types))
        if excluded_types is not None
        else excluded_types_for_genres(norm_types)
    )
    eff_funcs = [f for f in (scene_functions or body.get('scene_functions') or []) if f in SCENE_FUNCTION_LABELS]
    if not eff_funcs:
        eff_funcs = ['opening_hook', 'confrontation']
    timestamp_val = ts or now()
    existing = conn.execute(
        'SELECT id FROM voice_fingerprints WHERE book_id=? ORDER BY updated_at DESC LIMIT 1', (book_id,)
    ).fetchone()
    fp_id = existing['id'] if existing else f'vfp-{uuid4().hex[:12]}'
    clean_body = {
        'title': str(title)[:120],
        'base_voice_id': eff_base,
        'dimensions': dict(body.get('dimensions') or {}),
        'techniques': [str(x).strip()[:220] for x in (body.get('techniques') or ()) if str(x).strip()][:5],
        'drift_guards': [str(x).strip()[:180] for x in (body.get('drift_guards') or ()) if str(x).strip()][:4],
        'scene_functions': eff_funcs,
        'scene_function_notes': {
            k: str(v).strip()[:240]
            for k, v in (body.get('scene_function_notes') or {}).items()
            if k in SCENE_FUNCTION_LABELS and str(v).strip()
        },
        'evidence_spans': [
            {k: span[k] for k in ('unit_id', 'chapter_index', 'start', 'end', 'quote') if k in span}
            for span in (body.get('evidence_spans') or ())[:4]
            if isinstance(span, dict)
        ],
    }
    conn.execute(
        '''INSERT OR REPLACE INTO voice_fingerprints
           (id, book_id, structure_version, title, base_voice_id, type_tags_json, excluded_types_json,
            scene_functions_json, body_json, status, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
        (
            fp_id, book_id, int(structure_version), str(title)[:120], eff_base,
            canonical(norm_types), canonical(eff_excluded), canonical(eff_funcs),
            canonical(clean_body), status, timestamp_val, timestamp_val,
        ),
    )
    return {
        'id': fp_id,
        'book_id': book_id,
        'structure_version': int(structure_version),
        'title': str(title)[:120],
        'base_voice_id': eff_base,
        'base_voice_name': VOICE_BASE_MAP[eff_base]['name'],
        'type_tags': norm_types,
        'excluded_types': eff_excluded,
        'scene_functions': eff_funcs,
        'body': clean_body,
        'status': status,
        'updated_at': timestamp_val,
    }


def _row_to_fingerprint(row: Any) -> dict[str, Any]:
    base_id = row['base_voice_id']
    base_meta = VOICE_BASE_MAP.get(base_id) or VOICE_BASE_MAP['VOICE_GENRE_HYBRID_BALANCED']
    return {
        'id': row['id'],
        'book_id': row['book_id'],
        'book_title': row['book_title'] if 'book_title' in row.keys() else '',
        'structure_version': row['structure_version'],
        'title': row['title'],
        'base_voice_id': base_id,
        'base_voice_name': base_meta['name'],
        'type_tags': json.loads(row['type_tags_json'] or '[]'),
        'excluded_types': json.loads(row['excluded_types_json'] or '[]'),
        'scene_functions': json.loads(row['scene_functions_json'] or '[]'),
        'body': json.loads(row['body_json'] or '{}'),
        'status': row['status'],
        'updated_at': row['updated_at'],
    }


def list_voice_fingerprints(
    conn: Any,
    *,
    types: list[str] | tuple[str, ...] | None = None,
    status: str = 'approved',
    include_incompatible: bool = False,
) -> list[dict[str, Any]]:
    """Query decomposed voice fingerprints ranked by genre match, blocking cross-genre pollution."""
    ensure_voice_fingerprint_table(conn)
    rows = conn.execute(
        '''SELECT f.*, COALESCE(b.title, '') AS book_title
           FROM voice_fingerprints f
           LEFT JOIN staging_books b ON b.id=f.book_id
           WHERE (?='' OR f.status=?) AND (b.status IS NULL OR b.status!='rejected')
           ORDER BY f.updated_at DESC''',
        (status, status),
    ).fetchall()
    norm_types = canonical_types(list(types)) if types else []
    type_set = set(norm_types)
    primary = norm_types[0] if norm_types else ''

    results: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        item = _row_to_fingerprint(row)
        fp_types = set(item['type_tags'])
        fp_excluded = set(item['excluded_types'])
        if type_set:
            if type_set & fp_excluded:
                if not include_incompatible:
                    continue
                item['type_match'] = 'incompatible'
                results.append((3, item))
                continue
            if primary and primary in fp_types:
                item['type_match'] = 'primary'
                results.append((0, item))
            elif type_set & fp_types:
                item['type_match'] = 'secondary'
                results.append((1, item))
            else:
                if not include_incompatible:
                    continue
                item['type_match'] = 'general'
                results.append((2, item))
        else:
            item['type_match'] = 'all'
            results.append((0, item))
    results.sort(key=lambda r: (r[0], r[1].get('updated_at') or ''))
    return [r[1] for r in results]


def get_voice_fingerprints_by_ids(conn: Any, ids: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
    if not ids:
        return []
    ensure_voice_fingerprint_table(conn)
    clean = [str(i).strip() for i in ids if str(i).strip()]
    if not clean:
        return []
    placeholders = ','.join('?' for _ in clean)
    rows = conn.execute(
        f'''SELECT f.*, COALESCE(b.title, '') AS book_title
            FROM voice_fingerprints f LEFT JOIN staging_books b ON b.id=f.book_id
            WHERE f.id IN ({placeholders}) AND f.status='approved' ''',
        tuple(clean),
    ).fetchall()
    by_id = {row['id']: _row_to_fingerprint(row) for row in rows}
    return [by_id[i] for i in clean if i in by_id]
