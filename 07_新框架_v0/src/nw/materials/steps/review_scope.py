"""整章与跨章审稿步骤所用的《资料库》原文。"""

from nw.materials.steps.review_scope_application import MATERIAL as APPLICATION_MATERIAL
from nw.materials.steps.review_scope_book_quality import MATERIAL as BOOK_QUALITY_MATERIAL
from nw.materials.steps.review_scope_continuity_checks import MATERIAL as CONTINUITY_MATERIAL
from nw.materials.steps.review_scope_costs import MATERIAL as COSTS_MATERIAL
from nw.materials.steps.review_scope_dynamic_network import MATERIAL as DYNAMIC_NETWORK_MATERIAL
from nw.materials.steps.review_scope_narrative import MATERIAL as NARRATIVE_MATERIAL
from nw.materials.steps.review_scope_progression import MATERIAL as PROGRESSION_MATERIAL
from nw.materials.steps.review_scope_reader import MATERIAL as READER_MATERIAL
from nw.materials.steps.review_scope_reader_engagement import MATERIAL as READER_ENGAGEMENT_MATERIAL
from nw.materials.steps.review_scope_resources import MATERIAL as RESOURCES_MATERIAL
from nw.materials.steps.review_scope_rules import MATERIAL as RULES_MATERIAL
from nw.materials.steps.review_scope_static_network import MATERIAL as STATIC_NETWORK_MATERIAL
from nw.materials.steps.review_scope_structure import MATERIAL as STRUCTURE_MATERIAL
from nw.materials.steps.review_scope_viewpoint import MATERIAL as VIEWPOINT_MATERIAL
from nw.materials.steps.review_type_originality import MATERIAL as TYPE_ORIGINALITY_MATERIAL
from nw.materials.steps.type_adaptation_work_case_rules import SCOPE_REVIEW_MATERIAL as WORK_CASE_REVIEW_MATERIAL


MATERIAL = r"""【整章及跨章审稿的资料】
按本次已经采用的资料合同和冻结稿件范围审查下列要求。使用原有 source_checks 与正文证据核对；未采用的规则和未覆盖的范围各按已有审稿规则处理。
有完整章稿及相应冻结记录时，核对新设定与既有设定、人物变化与状态证据、实际发生的世界规则例外及其原因。按所采用的项目规则引用具体稿段。

### 板块45 伏笔与反转#伏笔埋设
【定义】伏笔的三种核心特征。
【判定标准】规则\*\*：首次引入的伏笔在后续2-10章中被揭示其真正含义
【本步用法】
采用此规则且有埋设、揭示及已确认章序时，比较实际章距与回收窗口。

### 板块45 伏笔与反转#伏笔密度
【判定标准】规则\*\*：
\- 埋设密度：每章1-2条伏笔被埋设
\- 揭示密度：每章0.5-1.5条伏笔被揭示
\- 总量平衡
【本步用法】
逐章列真实埋设、局部解释、完整揭示的事实与段落。全章或项目已确认的统计窗口出现后，才核对采用的原文区间和口径。

### 板块45 伏笔与反转#伏笔回收率
【判定标准】规则\*\*：
\- 不低于80%：绝大部分伏笔都必须被回收
\- 剩余20%可以是开放式（保留悬念）或噪音（不解释的细
【本步用法】
以已定范围中实际埋设的伏笔及已归档的回收记录核对比例。保留原文80%要求、稿件缺口和项目有依据的留白项。

### 板块46 场景结构#场景数量
【判定标准】规则\*\*：每章恰好4个场景，不能多也不能少
【本步用法】
只核对项目已采用且本次完整覆盖的四场景章节。

### 板块47 场景冲突#冲突类型轮换
【定义】连续两章不得使用同一种主导冲突。
【判定标准】规则\*\*：冲突类型轮换让故事张力在不同的“轴”上摆动，避免读者对单一冲突类型疲劳
【本步用法】
有相邻完整章稿且采用本条时，分别说明各章的实际主导冲突。

### 板块48 章节结构#章节连续性
【判定标准】规则\*\*：
\- 本章的开篇（第1场景的前1/3）必须回应上一章结尾提出的问题
\- 回应方式：直接解决、部分解决、
【本步用法】
用齐备相邻章稿对照上章末的问题和本章首场前1/3交付的证据、答复或后果。回想旧问题只能用于唤回记忆。部分回应时明确本次兑现的内容及以后仍待兑现的内容。

### 板块48 章节结构#章节长度控制
【判定标准】规则\*\*：单章最多少于目标字数±30%，超过则需要拆分或精简，不足则需要扩充或合并
【本步用法】
用项目已确认的章目标字数和实际章稿范围核对篇幅。

### 板块48 章节结构#章节变奏规则
【分级标准】轻章之间至少隔2章
\- 中章可连续但不超过2章
\- 空章必须出现在重要场景之后（作为消化）
【判定标准】规则\*\*：
\- 重章之间至少隔1章
\- 轻章之间至少隔2章
\- 中章可连续但不超过2章
\- 空章必须出现
【本步用法】
按项目已采用的章节顺序与类型记录核对间隔，指出与一般不连用规则的未决边界。

### 板块51 禁止词汇#禁止词汇检查规则
【定义】每章完成后检查禁止词汇是否出现。
【禁止清单】
- 禁止词汇检查规则相关禁用表达
【替代方式】用动作或直接叙述替代
【本步用法】
已确认禁词清单与全章稿件齐备时，按实际段落核对命中。原文禁用项为占位，采用项目已确认的禁词。
""" + '\n'.join((
    '', READER_MATERIAL, STRUCTURE_MATERIAL, CONTINUITY_MATERIAL, BOOK_QUALITY_MATERIAL, RULES_MATERIAL,
    NARRATIVE_MATERIAL, COSTS_MATERIAL, VIEWPOINT_MATERIAL, PROGRESSION_MATERIAL, READER_ENGAGEMENT_MATERIAL,
    RESOURCES_MATERIAL, APPLICATION_MATERIAL, DYNAMIC_NETWORK_MATERIAL, STATIC_NETWORK_MATERIAL,
    TYPE_ORIGINALITY_MATERIAL,
    WORK_CASE_REVIEW_MATERIAL,
))
