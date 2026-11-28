"""剧情设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 命运与主题、时间安排及状态预览】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

324695｜{"id":"C01546","source":"72.5_冒险决策","target":"44.3_爽点-代价","type":"共振","condition":"冒险伴随高代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已把冒险的回报与代价放入剧情时，按真实前置压力、行动、所失和结果安排同一因果。

327044｜{"id":"C01557","source":"73.4_决策不可逆","target":"122.7_不可逆","type":"转化","condition":"不可逆是推进；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选决定带来不可逆结果时，使用实际丧失的机会、前后状态和相邻事件核对剧情推进。

327259｜{"id":"C01558","source":"73.4_决策不可逆","target":"4.1_弧光","type":"演化","condition":"不可逆推动弧光；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】若不可逆决定确推动弧光，用具体选择、不可回撤的结果和后来可观察行为确认节点。

329178｜{"id":"C01567","source":"74.2_善恶","target":"76.7_灰度","type":"转化","condition":"善恶间有灰度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选道德灰度时，以真实行为、动机及互相抵触的后果说明何种情节使判断仍有不同依据。

333645｜{"id":"C01588","source":"76.1_道德困境","target":"76.7_灰度","type":"转化","condition":"困境无法解决→灰度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有不能兼顾的两难选择时，用实际角色行为、保住或失去的价值及后续结果表现其灰度。

333860｜{"id":"C01589","source":"76.1_道德困境","target":"4.1_弧光","type":"演化","condition":"困境推动角色成长；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目以道德困境推动人物弧光时，用真实触发、所选行动及后来的行为差异核对改变节点。

334075｜{"id":"C01590","source":"76.1_道德困境","target":"44.3_爽点-代价","type":"共振","condition":"困境解决与爽点；且当前故事明确采用该静态关系","priority":3,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作安排两难解决与回报相连时，以实际选择、需要承担的代价和可见回报核对兑现因果。

334290｜{"id":"C01591","source":"76.2_困境前奏","target":"45.12_反转前奏","type":"嵌套","condition":"困境前奏类似反转前奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】确有需要铺垫的困境时，用已知前置压力、可查线索和以后真正出现选择的位置安排前奏。

334505｜{"id":"C01592","source":"76.2_困境前奏","target":"155.1_缓冲","type":"约束","condition":"前奏需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「76.2_困境前奏」经「约束」影响「155.1_缓冲」（条件：前奏需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

334720｜{"id":"C01593","source":"76.3_困境不可逆","target":"122.7_不可逆","type":"转化","condition":"困境后果不可逆；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已设两难的不可逆结果时，用实际阶段、丧失的选择和后效说明后续怎样承接。

335365｜{"id":"C01596","source":"76.6_代价追踪","target":"44.3_爽点-代价","type":"共振","condition":"代价与爽点同步；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用代价与回报同步的章序时，对照当前实际支付、人物的选择及与后面行动相接的结果。

335779｜{"id":"C01598","source":"76.7_道德灰度","target":"76.1_道德困境","type":"转化","condition":"困境是灰度来源；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已用既有困境表现灰度时，依事实、不同角色价值与所付代价核对当前仍成立的冲突。

335994｜{"id":"C01599","source":"76.7_道德灰度","target":"64.1_读者情绪","type":"转化","condition":"灰度引发读者复杂情绪；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「76.7_道德灰度」经「转化」影响「64.1_读者情绪」（条件：灰度引发读者复杂情绪）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

336424｜{"id":"C01601","source":"76.8_道德悖论","target":"63.1_主题","type":"绑定","condition":"悖论连接主题；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已将道德悖论联系主题时，把具体人物选择及其难以兼顾的后果落实到章场的主题依据。

336639｜{"id":"C01602","source":"76.9_道德与主题","target":"63.1_主题","type":"绑定","condition":"道德困境是主题肉身化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用实际道德困境表现主题时，用项目实有角色、所牺牲的价值和可观察的后果核对其作用。

337929｜{"id":"C01608","source":"77.1_时间紧迫","target":"44.1_爽点压抑","type":"共振","condition":"紧迫加剧压抑；且当前故事明确采用该静态关系","priority":3,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品用真实时限加深已定压力时，把剩余机会、所见限制与人物实际应对对应到相关章场。

338343｜{"id":"C01610","source":"77.2_时间从容","target":"155.1_缓冲","type":"转化","condition":"从容=缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「77.2_时间从容」经「转化」影响「155.1_缓冲」（条件：从容=缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

340477｜{"id":"C01620","source":"78.1_时间标记","target":"133.1_章节预览","type":"转化","condition":"标记是预览部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用项目真实时点、既定事件和可披露信息核对进入章节预览的时间标记。

340907｜{"id":"C01622","source":"78.2_时间跳跃","target":"42.1_引力中心","type":"转化","condition":"跳跃影响引力中心；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已采用时间跳跃影响引力中心时，依据作者设定的故事时间及前后事件确认哪个疑问或选择受影响。

341122｜{"id":"C01623","source":"78.3_叙事顺序","target":"113.1_叙事顺序","type":"转化","condition":"叙事顺序决定时间规则；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已明确故事发生顺序和呈现顺序时，沿实有时间线在章序注明如何排列已选事件和各次揭示。

341337｜{"id":"C01624","source":"78.3_叙事顺序","target":"45.1_伏笔","type":"嵌套","condition":"倒叙是伏笔一种；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「78.3_叙事顺序」经「嵌套」影响「45.1_伏笔」（条件：倒叙是伏笔一种）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

342396｜{"id":"C01629","source":"79.2_时间密度","target":"62.1_节奏轮换","type":"转化","condition":"密度影响节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用不同章段时间密度时，在实有章序标明实际事件、跨越的时长及应保留的快慢变化。

346584｜{"id":"C01649","source":"8.1_身体状态_饥饿","target":"130_核心悬念","type":"共振链","condition":"饥饿与核心悬念同源","priority":2,"effect":"饥饿与核心悬念绑定，生理状态成为谜题的一部分","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「共振链」影响「130_核心悬念」（条件：饥饿与核心悬念同源）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

346982｜{"id":"C01651","source":"8.1_身体状态_饥饿","target":"4.1_弧光五阶段","type":"演化链","condition":"饥饿反复发生且与核心执念相关","priority":2,"effect":"饥饿从生理状态演变为心理状态，成为角色成长的关键驱动力","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「演化链」影响「4.1_弧光五阶段」（条件：饥饿反复发生且与核心执念相关）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

348622｜{"id":"C01659","source":"8.1_饥饿","target":"4.1_弧光触发","type":"演化","condition":"反复≥3次；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「演化」影响「4.1_弧光触发」（条件：反复≥3次）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

359785｜{"id":"C01712","source":"80.1_抗争","target":"130_核心悬念","type":"绑定","condition":"抗争绑定核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「80.1_抗争」经「绑定」影响「130_核心悬念」（条件：抗争绑定核心悬念）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

360430｜{"id":"C01715","source":"80.2_接受","target":"4.1_弧光终点","type":"转化","condition":"接受是弧光终点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「80.2_接受」经「转化」影响「4.1_弧光终点」（条件：接受是弧光终点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

361290｜{"id":"C01719","source":"80.5_超越","target":"4.1_弧光顶点","type":"绑定","condition":"超越=弧光顶点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「80.5_超越」经「绑定」影响「4.1_弧光顶点」（条件：超越=弧光顶点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

361505｜{"id":"C01720","source":"81.1_必然性错觉","target":"42.4_必然性错觉","type":"转化","condition":"命运必然性错觉；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用必然性错觉时，用此前可见的选择和后来的结果核对哪些事件让人物或读者觉得事情本该如此。

361720｜{"id":"C01721","source":"81.1_必然性错觉","target":"45.1_伏笔埋设","type":"嵌套链","condition":"必然性是伏笔","priority":1,"effect":"必然性错觉是伏笔的一种","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品用伏笔形成必然性错觉时，在实有章场设定可回查线索、当下可成立的解释及日后验证位置。

361919｜{"id":"C01722","source":"81.1_必然性错觉","target":"45.1_伏笔","type":"嵌套","condition":"必然性通过伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「81.1_必然性错觉」经「嵌套」影响「45.1_伏笔」（条件：必然性通过伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

362134｜{"id":"C01723","source":"81.2_巧合必然化","target":"45.1_伏笔","type":"嵌套","condition":"巧合需伏笔支撑；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「81.2_巧合必然化」经「嵌套」影响「45.1_伏笔」（条件：巧合需伏笔支撑）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

362564｜{"id":"C01725","source":"81.6_命运揭示时机","target":"130_核心悬念","type":"解决","condition":"命运揭示解决悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并完成作用时，推动终点的问题状态收敛。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已设命运揭示回答本作核心悬念时，用既有线索、真实触发和所选时点核对能解释哪些问题。

363209｜{"id":"C01728","source":"82.3_岔路与回撤","target":"42.6_岔路设计","type":"嵌套链","condition":"岔路是设计","priority":1,"effect":"岔路是剧情设计的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已有岔路改变剧情时，以实际发生的选择、保留的退路和后续事件核对分支的作用。

363623｜{"id":"C01730","source":"82.7_命运反转","target":"130_核心悬念","type":"解决","condition":"命运反转解决悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并完成作用时，推动终点的问题状态收敛。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已用命运反转回应核心悬念时，对照实际旧解释、前置线索、触发事件和新结果确定答复范围。

363838｜{"id":"C01731","source":"82.7_命运反转","target":"45.11_反转类型","type":"转化","condition":"命运反转是反转一种；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用命运反转时，按既有事件与读者可得证据核对先成立的解释、改变原因及反转后的后效。

366800｜{"id":"C01745","source":"83.4_适应","target":"4.1_弧光","type":"演化","condition":"适应是弧光一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色已通过某项适应决定发生变化时，用真实情节和之后可见行为对应选定弧光节点。

380320｜{"id":"C01809","source":"9.2_状态化解","target":"155.1_缓冲","type":"约束","condition":"化解需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「9.2_状态化解」经「约束」影响「155.1_缓冲」（条件：化解需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

380734｜{"id":"C01811","source":"9.2_状态化解规则","target":"155.1_情绪缓冲","type":"触发链","condition":"化解需要缓冲","priority":2,"effect":"化解需要缓冲过程","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已安排状态化解之后的读者缓冲时，用具体动作、可观察余波和相邻场景确定适用位置。

383202｜{"id":"C01823","source":"9.5_状态追踪","target":"133.1_章节预览","type":"转化","condition":"状态追踪是预览的一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本条用于把已接受的章末状态作为下一章预览的依据。原附通用状态转化仅作追溯，预览中的本章末状态按实际时点和拟定事件留为设计候选。"""
