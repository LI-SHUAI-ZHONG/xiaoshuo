"""剧情设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 主支线、情绪缓冲、势力张力及暗线揭示】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

70483｜{"id":"C00338","source":"150.1_人性博弈","target":"150.2_博弈类型","type":"转化","condition":"博弈有类型；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据作品已有的博弈双方、各自目标和实际资源，核对当前场面属于哪种博弈及其怎样推进冲突，保留选择和后果。

70913｜{"id":"C00340","source":"150.1_人性博弈","target":"86.1_合作","type":"嵌套链","condition":"博弈是合作","priority":1,"effect":"人性博弈是合作的一部分","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目采用合作处理既有博弈时，安排双方可接受的分工、交换条件、仍有分歧的利益与合作能维持的范围。

71112｜{"id":"C00341","source":"150.1_人性博弈","target":"86.1_合作","type":"嵌套","condition":"博弈=合作；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用博弈与合作的关系时，用具体共同目标、人物选择和随后的改变核对合作是在哪个事件里成立的。

71542｜{"id":"C00343","source":"150.3_博弈回合","target":"43.1_资源争夺","type":"嵌套","condition":"博弈=争夺；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】某一回合确实围绕同一资源时，把双方需求、该回合的关键选择和资源可能如何转移落实到实际事件。

72601｜{"id":"C00348","source":"151.2_三层身份","target":"45.1_伏笔","type":"嵌套","condition":"隐藏身份=伏笔；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「151.2_三层身份」经「嵌套」影响「45.1_伏笔」（条件：隐藏身份=伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

72816｜{"id":"C00349","source":"151.2_三层身份","target":"130_核心悬念","type":"绑定","condition":"身份=悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已把某一层身份纳入核心悬念时，用实际身份线索、各方知情和既定揭示时点明确它解决哪个问题。

74520｜{"id":"C00357","source":"153.1_对立定义","target":"43.1_资源争夺","type":"转化","condition":"对立=争夺；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已有对立且双方需要同一资源时，将争夺对象、进入冲突的行动及对后续选择的影响落实到事件。

74735｜{"id":"C00358","source":"153.1_对立定义","target":"43.4_道德困境","type":"转化","condition":"对立=困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已用现有对立产生道德困境时，给实际角色安排有价值差异的选项及其成本，用前情支撑两难。

75165｜{"id":"C00360","source":"153.2_对立类型","target":"43.4_道德困境","type":"转化","condition":"价值观对立=困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有价值观对立并选择转为困境时，以人物已有价值和所处事件说明为什么两种做法各有依据及实际损失。

75380｜{"id":"C00361","source":"153.3_对立强度","target":"43.1_资源争夺","type":"转化","condition":"强度影响争夺；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已经确定争夺双方和资源时，按当前对立强度核对升级选择、双方所冒风险和具体后果。

75810｜{"id":"C00363","source":"153_对立关系","target":"43.1_资源争夺","type":"嵌套链","condition":"对立是资源争夺","priority":1,"effect":"对立关系是资源争夺的一种","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】只在项目已确认对立围绕资源时使用这条关系，明确对立双方、争夺标的及已经安排的事件后果。

76009｜{"id":"C00364","source":"154.1_主线","target":"130_核心悬念","type":"绑定","condition":"主线绑定核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】主线和核心悬念已确立时，把主线实际行动与悬念线索、阶段性回应及计划兑现对应起来。

76224｜{"id":"C00365","source":"154.1_主线","target":"41.1_三幕","type":"嵌套","condition":"主线=三幕核心；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用三幕且主线已有实际事件时，将目标、关键转折和主线收束分配给已定各幕，保留事件因果。

76439｜{"id":"C00366","source":"154.1_主线","target":"42.1_引力中心","type":"绑定","condition":"主线=引力中心；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知主线目标和故事引力中心时，核对当前事件为什么仍牵引该目标或待回答问题，并安排下一处可见联系。

76654｜{"id":"C00367","source":"154.2_支线","target":"121.9_配角独立行动","type":"嵌套","condition":"支线=配角行动；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定支线确由配角发起时，用其独立目标、实际行动和结果建立事件顺序，注明支线何时影响主线。

76869｜{"id":"C00368","source":"154.2_支线","target":"154.1_主线","type":"嵌套","condition":"支线依附主线；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】主支线已有项目事实时，用两者实际共享的事件、信息或结果找出连接点，保留支线的具体目标及收束。

77084｜{"id":"C00369","source":"154.2_支线","target":"45.1_伏笔","type":"嵌套","condition":"支线埋设伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「154.2_支线」经「嵌套」影响「45.1_伏笔」（条件：支线埋设伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

77299｜{"id":"C00370","source":"154.3_任务目标","target":"122.1_推进","type":"转化","condition":"任务→推进；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用现有章节任务、行动结果及后续事件核对任务怎样产生推进，标出会改变局势、人物选择或信息的证据。

77944｜{"id":"C00373","source":"154.4_目标层级","target":"154.1_主线","type":"嵌套","condition":"高层目标=主线；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依主线实际方向和分层目标，在章任务明确当前任务承接哪项上层目标，以及事件结束后应留下什么。

78159｜{"id":"C00374","source":"154_主线","target":"130_核心悬念","type":"触发链","condition":"主线绑定悬念","priority":1,"effect":"主线绑定核心悬念","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已认定主线绑定核心悬念时，用实际主线行动确定哪次取得线索、哪次改变预期以及最终回应位置。

78358｜{"id":"C00375","source":"155.1_情绪缓冲","target":"61.3_轻章","type":"嵌套链","condition":"缓冲是轻章","priority":1,"effect":"情绪缓冲是轻章","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】确实选用轻章做情绪缓冲时，用已发生的高压事件和读者已知后果确定缓冲位置、章内任务与下一次升压条件。

78557｜{"id":"C00376","source":"155.1_情绪缓冲","target":"61.3_轻章","type":"绑定","condition":"轻章是缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作安排高压后的轻章时，核对已定章序、可见的消化与关系反应，以及它怎样承接后续事件。

78772｜{"id":"C00377","source":"155.1_情绪缓冲","target":"61.4_空章","type":"绑定","condition":"空章是缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选空章承担缓冲时，保留实际可写的人物反应或情节余波，按本作章序核对它与前后强度的关系。

78987｜{"id":"C00378","source":"155.1_情绪缓冲","target":"62.1_节奏轮换","type":"约束","condition":"缓冲影响轮换；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按项目已用节奏轮换核对高潮之后的缓冲位置、真实章场事件和下一轮强度变化，并在章任务保留原因。

79202｜{"id":"C00379","source":"155.2_共情铺垫","target":"45.1_伏笔","type":"嵌套","condition":"铺垫=伏笔；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「155.2_共情铺垫」经「嵌套」影响「45.1_伏笔」（条件：铺垫=伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

79417｜{"id":"C00380","source":"155.2_共情铺垫","target":"45.1_伏笔埋设","type":"嵌套链","condition":"铺垫是伏笔","priority":2,"effect":"共情铺垫是伏笔的一种","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已明确共情铺垫也承担伏笔埋设时，在 promise_plan 标出具体处境、实际放下的线索及后文可以回查的回应。

80826｜{"id":"C00387","source":"158.1_认知阶梯","target":"4.1_弧光五阶段","type":"嵌套链","condition":"认知是弧光","priority":1,"effect":"认知阶梯是弧光的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用认知阶梯承接人物弧光时，用角色实际获得的新证据、由此触发的选择和后果定位这一阶段的变化。

83296｜{"id":"C00399","source":"16.3_透支","target":"155.1_缓冲","type":"约束","condition":"透支需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「16.3_透支」经「约束」影响「155.1_缓冲」（条件：透支需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

84104｜{"id":"C00403","source":"16.4_后遗症","target":"4.5_成长中断","type":"触发","condition":"后遗症导致中断；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已经确认后遗症会中断人物成长时，在实际章场安排哪些能力或目标受阻、持续条件和重新推进的依据。

90272｜{"id":"C00433","source":"18.3_能量源衰竭","target":"130_核心悬念","type":"绑定","condition":"衰竭关联核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】能量源的变化与已选核心悬念相关时，用实际地点、衰竭进展和已有证据安排探索或揭示具体问题的线索。

92559｜{"id":"C00444","source":"19.3_例外代价","target":"44.3_爽点-代价","type":"共振","condition":"代价与爽点同步；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已用同一事件安排例外代价与读者回报时，用人物选择、付出的具体代价和立即或后续发生的回报组织事件因果。

92963｜{"id":"C00446","source":"19.4_例外的验证","target":"45.1_伏笔埋设","type":"触发链","condition":"验证是伏笔展开","priority":2,"effect":"例外验证是伏笔的展开方式","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已设检验例外的叙事任务时，安排能提前看到的异常线索与后续实际验证事件，在 promise_plan 留清两处的证据和结论条件。

93152｜{"id":"C00447","source":"19.4_例外验证","target":"45.1_伏笔","type":"嵌套","condition":"验证是伏笔展开；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「19.4_例外验证」经「嵌套」影响「45.1_伏笔」（条件：验证是伏笔展开）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

93367｜{"id":"C00448","source":"19.4_例外验证","target":"130_核心悬念","type":"绑定","condition":"验证关联核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】待验证的例外确实关乎核心悬念时，用所知问题、实际验证动作和可观察结果核对这次揭示能回答到哪一层。

98280｜{"id":"C00471","source":"20.1_生态系统层级","target":"83.1_探索","type":"转化","condition":"生态决定探索方向；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】探索任务已经形成时，用已知生态层级、线索和进入限制说明相应人物为何选择这个目标与路线。

99124｜{"id":"C00475","source":"20.2_自动运转事件","target":"23.1_隐蔽流","type":"嵌套链","condition":"自动运转包含隐蔽流","priority":2,"effect":"自动运转事件包含隐蔽流","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】某项自动运转确实是本作暗线时，用具体幕后事件、前段可见痕迹和后段可核揭示形成信息顺序。

99323｜{"id":"C00476","source":"20.2_自动运转事件","target":"35.2_张力设计","type":"嵌套","condition":"自动事件制造张力；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已设自动事件持续产生压力时，按真实的参与方、事件结果及已给线索安排角色或读者何时察觉张力。

102683｜{"id":"C00492","source":"21.2_扰动与失衡","target":"35.2_张力设计","type":"嵌套","condition":"失衡制造张力；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件中的失衡可形成持续张力时，用具体不稳定征象和各方选择标明升级的依据及角色何时能得知。

103312｜{"id":"C00495","source":"21.3_寻找新均衡","target":"32.6_裂变期","type":"转化","condition":"新均衡对应裂变期；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用裂变期并已安排寻找新均衡的事件时，以实际势力分化、旧秩序失效和新关系形成核对该事件的历史位置。

104759｜{"id":"C00502","source":"22.1_势力自动互动","target":"23.1_隐蔽流","type":"嵌套","condition":"隐蔽势力互动；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已设某项势力互动需要隐蔽展开时，用已知双方、幕后的实际事件和前段可见痕迹安排后续揭示。

105603｜{"id":"C00506","source":"22.2_势力间张力","target":"130_核心悬念","type":"绑定","condition":"张力是悬念来源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已把势力张力用作核心悬念来源时，用具体争议、可见迹象及后续事件对应要回答的实际问题。

106033｜{"id":"C00508","source":"22.3_势力的自动变化","target":"32.5_暗流期","type":"转化","condition":"势力变化在暗流期；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】历史安排已经采用暗流期时，把具体势力的生长、收缩或分化安放在实际区间，标明当事人能够察觉的事件。

106248｜{"id":"C00509","source":"22.3_势力的自动变化","target":"121.9_配角独立行动","type":"转化","condition":"势力变化关联配角；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确立的势力变化与配角行动有因果关系时，以配角独立目标、所做之事及实际后果安排其在剧情中承担的部分。

106463｜{"id":"C00510","source":"22.3_势力的自动变化","target":"32.5_暗流期","type":"触发链","condition":"势力变化是暗流的一部分","priority":2,"effect":"势力的自动变化是暗流期的表现","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品使用暗流期表现势力内部变化时，用实有事件和前后势力痕迹定位角色能够发现什么及其后续意义。

106662｜{"id":"C00511","source":"23.1_隐蔽流","target":"130_核心悬念","type":"绑定","condition":"隐蔽流连接核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已定隐蔽流关联核心悬念时，在 promise_plan 把实际幕后事件、可见证据和最终揭示位置对应到本书要回答的问题。

106877｜{"id":"C00512","source":"23.1_隐蔽流","target":"130_核心悬念","type":"触发链","condition":"隐蔽流是核心悬念","priority":1,"effect":"隐蔽流是核心悬念的来源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】核心悬念确有幕后事件来源时，用既有行动与留下的可感痕迹核对它如何引出读者的问题及后续实际解释。

107076｜{"id":"C00513","source":"23.1_隐蔽流","target":"45.1_伏笔","type":"嵌套","condition":"隐蔽流通过伏笔揭示；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「23.1_隐蔽流」经「嵌套」影响「45.1_伏笔」（条件：隐蔽流通过伏笔揭示）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

107291｜{"id":"C00514","source":"23.1_隐蔽流","target":"45.1_伏笔埋设","type":"嵌套链","condition":"隐蔽流是伏笔来源","priority":1,"effect":"隐蔽流是伏笔的来源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已明确用隐蔽流提供伏笔时，在现有章场放入可回查的真实痕迹，核对当前视角可以察觉的程度及后续揭示位置。

107490｜{"id":"C00515","source":"23.1_隐蔽流","target":"23.3_揭示时机","type":"演化","condition":"隐蔽流逐步揭示；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已安排的隐蔽流，按现有事件、角色知情和前段线索安排何时局部揭示及何时确认其真实作用。

107705｜{"id":"C00516","source":"23.2_暗线循环","target":"45.1_伏笔","type":"嵌套","condition":"暗线是伏笔来源；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「23.2_暗线循环」经「嵌套」影响「45.1_伏笔」（条件：暗线是伏笔来源）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

107920｜{"id":"C00517","source":"23.2_暗线循环","target":"130_核心悬念","type":"绑定","condition":"暗线关联核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】暗线循环已确定关联核心悬念时，以可具体对照的重复事件、不同表现及先后顺序安排证据和待解问题。

108135｜{"id":"C00518","source":"23.2_暗线循环","target":"23.3_揭示时机","type":"演化","condition":"暗线周期性揭示；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有事件按周期重复时，依据前后痕迹核对角色在什么节点辨认出规律，并给计划中真正揭示的位置保留依据。

108350｜{"id":"C00519","source":"23.2_暗线循环","target":"80.1_抗争","type":"触发链","condition":"暗线循环驱动抗争","priority":2,"effect":"暗线循环驱动角色抗争","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「23.2_暗线循环」经「触发链」影响「80.1_抗争」（条件：暗线循环驱动抗争）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

108549｜{"id":"C00520","source":"23.3_隐蔽流揭示时机","target":"45.3_伏笔揭示","type":"触发链","condition":"揭示时机决定伏笔揭示","priority":1,"effect":"隐蔽流揭示时机决定伏笔揭示时机","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】现有隐蔽流揭示同时承担项目已埋伏笔的回收时，用已放线索、实际事件和人物知情安排揭示的时间及证据。

108748｜{"id":"C00521","source":"23.3_隐蔽流揭示时机","target":"45.3_伏笔揭示","type":"转化","condition":"揭示即伏笔揭示；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以已采用的揭示时机对照前文伏笔与当前可见结果，写明既有 promise_plan 在哪一事件怎样兑现。

108963｜{"id":"C00522","source":"23.3_隐蔽流揭示时机","target":"65.2_不确定性","type":"转化","condition":"揭示减少不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前揭示已确认能缩小读者疑问时，在 reader_plan 写清哪项真实证据消除了哪个解释、还留哪些问题给后续事件。"""
