"""场景审稿步骤所用的《资料库》原文。"""

from nw.materials.steps.review_meaning import MATERIAL as MEANING_MATERIAL
from nw.materials.steps.review_deliberation import MATERIAL as DELIBERATION_MATERIAL
from nw.materials.steps.review_object_actions import MATERIAL as OBJECT_ACTION_MATERIAL
from nw.materials.steps.review_memory import MATERIAL as MEMORY_MATERIAL
from nw.materials.steps.review_social_material import MATERIAL as SOCIAL_MATERIAL
from nw.materials.steps.review_scene_space import MATERIAL as SCENE_SPACE_MATERIAL
from nw.materials.steps.review_character_checks import MATERIAL as CHARACTER_MATERIAL
from nw.materials.steps.review_dynamic_network import MATERIAL as DYNAMIC_NETWORK_MATERIAL
from nw.materials.steps.review_expression import MATERIAL as EXPRESSION_MATERIAL
from nw.materials.steps.review_language_checks import MATERIAL as LANGUAGE_MATERIAL
from nw.materials.steps.review_scene_checks import MATERIAL as SCENE_MATERIAL
from nw.materials.steps.review_static_network import MATERIAL as STATIC_NETWORK_MATERIAL
from nw.materials.steps.review_type_originality import MATERIAL as TYPE_ORIGINALITY_MATERIAL
from nw.materials.steps.review_workflow import MATERIAL as WORKFLOW_MATERIAL
from nw.materials.steps.review_material_anchors import MATERIAL as MATERIAL_ANCHOR_MATERIAL
from nw.materials.steps.review_perception_anchors import MATERIAL as PERCEPTION_ANCHOR_MATERIAL
from nw.materials.steps.review_body_state_anchors import MATERIAL as BODY_STATE_ANCHOR_MATERIAL
from nw.materials.steps.review_action_space_anchors import MATERIAL as ACTION_SPACE_ANCHOR_MATERIAL
from nw.materials.steps.review_cognition_decision_anchors import MATERIAL as COGNITION_DECISION_ANCHOR_MATERIAL


MATERIAL = r"""【正文审稿的资料】
按本场成稿及已采用规则定位问题与原文区间，跨章或全书判断以实际覆盖范围为准：
1. 快节奏或高强度对抗段核对短句、精确动词与动作结果；
2. 受限视角严查越界获知（他人内心、未见事件、无据确信），标明当前POV知情边界，区分叙述者向读者披露的事实与人物实际所知；
3. 对照冻结输入核验人物行为、道具边界、世界规则与时间标记；
4. 身份锚点按同号原表核对触发、行动与可见结果，绑定稿件版本、哈希与原文区间取证。

### 板块45 伏笔与反转#伏笔密度
【定义】每章伏笔的埋设和揭示数量。
【判定标准】规则\*\*：
\- 埋设密度：每章1-2条伏笔被埋设
\- 揭示密度：每章0.5-1.5条伏笔被揭示
\- 总量平衡
【本步用法】
只有本次审稿覆盖完整所需章节时才核对章级数量；小数揭示口径未确定时指出具体可核的事实。

### 板块45 伏笔与反转#伏笔回收率
【定义】伏笔被揭示的比例。
【判定标准】规则\*\*：
\- 不低于80%：绝大部分伏笔都必须被回收
\- 剩余20%可以是开放式（保留悬念）或噪音（不解释的细
【本步用法】
有完整范围和伏笔记录时核对实际埋设、回收和证据；原文剩余项的末行残缺。

### 板块45 伏笔与反转#反转合理性
【定义】反转必须有伏笔支撑且符合逻辑。
【判定标准】规则内是合理的
\- 可被回溯验证：读者在知道反转后回看前文，能发现“确实有暗示”
\*\*合理性写作规则\*\*：
【本步用法】
引用反转前的线索和反转当场的证据，说明旧判断怎样成立、新解释怎样与既有事实相接。缺实际前文时，只核本场因果，前文伏笔标为待核。

### 板块46 场景结构#场景内部因果链
【定义】每个动作有前因。
【判定标准】规则\*\*：
\- 场景中的每个动作都必须有其前因（做了什么导致了这个动作）
\- 前因可以是同一个场景内的上一件事，
【本步用法】
对照已选事件与本稿所见，定位主要动作及其直接前因。原因来自前场时回查实际交接材料。看到动作结果但找不到触发时，引用该句段及现有证据缺口。

### 板块48 章节结构#章节连续性
【定义】本章必须回应上一章结尾的钩子。
【判定标准】规则\*\*：
\- 本章的开篇（第1场景的前1/3）必须回应上一章结尾提出的问题
\- 回应方式：直接解决、部分解决、
【本步用法】
如工作包已有前章钩子，引用本章首场前1/3的实际答案或进展。回想旧问题只能用于唤回记忆。缺实际前章信息或当前首场时，在审稿提出待核的具体证据。

### 板块48 章节结构#章节长度控制
【定义】本章的字数范围。
【判定标准】规则\*\*：单章最多少于目标字数±30%，超过则需要拆分或精简，不足则需要扩充或合并
【本步用法】
有目标字数与整章稿件时核对已采用的篇幅范围。

### 板块49 句子控制#句长比例
【定义】全篇句子长度的比例。
【判定标准】检查方式\*\*：随机抽取一页，统计句长分布
【本步用法】
作者已指定页面和句长口径时按原文检查分布。当前场稿只报告当前段落的表现。

### 板块50 词汇控制#通用动词限制使用
【判定标准】规则\*\*：
\- 每段对话中，“说”最多使用1次（其余用精确动词替代或省略）
\- 描述动作时，优先使用精确动词而非
【同版补用原文｜156.5 第198893、198909行】
- 每100字至少有1个精确动词（刺/劈/切/掠/攥/碾 > 打/砍/弄/拿/放）
精确动词不足→替换通用动词
【本步用法】
引用同一实际对白段的说话人提示，区别台词中的词和标记说话人的“说”。本场动作被泛动词遮住时，指出实际动作的对象和方式，建议只替换影响辨认的措辞。

### 板块51 禁止词汇#禁止词汇检查规则
【定义】每章完成后检查禁止词汇是否出现。
【禁止清单】
- 禁止词汇检查规则相关禁用表达
【替代方式】用动作或直接叙述替代
【本步用法】
完整章稿与项目已确认禁词清单具备时才作章级检查。单场可报告已确认规则在当前稿件的具体命中位置。原件禁词清单为占位。
""" + '\n'.join((
    '', EXPRESSION_MATERIAL, WORKFLOW_MATERIAL, SCENE_MATERIAL, LANGUAGE_MATERIAL,
    CHARACTER_MATERIAL, DYNAMIC_NETWORK_MATERIAL, STATIC_NETWORK_MATERIAL,
    SCENE_SPACE_MATERIAL, SOCIAL_MATERIAL, MEMORY_MATERIAL, OBJECT_ACTION_MATERIAL, DELIBERATION_MATERIAL, MEANING_MATERIAL,
    TYPE_ORIGINALITY_MATERIAL,
    MATERIAL_ANCHOR_MATERIAL, PERCEPTION_ANCHOR_MATERIAL, BODY_STATE_ANCHOR_MATERIAL,
    ACTION_SPACE_ANCHOR_MATERIAL, COGNITION_DECISION_ANCHOR_MATERIAL,
))
