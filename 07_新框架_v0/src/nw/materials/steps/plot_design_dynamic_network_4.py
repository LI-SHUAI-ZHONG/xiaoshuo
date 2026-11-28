"""剧情设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 世界信息、人物弧光、剧情结构和冲突安排】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

157694｜{"id":"C00755","source":"34.2_不可知部分","target":"130_核心悬念","type":"绑定","condition":"不可知是悬念边界；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有核心悬念与不可知边界时，在 promise_plan 写清当前事实能支撑哪一问、哪部分信息可作回应及哪些仍保留。

157909｜{"id":"C00756","source":"34.2_不可知部分","target":"143.1_不确定性","type":"转化","condition":"不可知是不确定性来源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已知某项不可知造成故事疑问时，把实际迹象、目前尚可成立的解释和能验证的后续事件排入 reader_plan。

158952｜{"id":"C00761","source":"34.3_自动运转事件","target":"35.2_张力设计","type":"嵌套","condition":"自动运转产生张力；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有自动运转实际积累张力时，安排章场能看到的变化、相关人物何时得知以及冲突可能升级的条件。

159167｜{"id":"C00762","source":"35.1_隐性传递","target":"45.1_伏笔","type":"转化","condition":"隐性传递是伏笔形式；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「35.1_隐性传递」经「转化」影响「45.1_伏笔」（条件：隐性传递是伏笔形式）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

159382｜{"id":"C00763","source":"35.1_隐性传递","target":"45.1_伏笔埋设","type":"嵌套链","condition":"隐性传递是伏笔","priority":1,"effect":"隐性传递是伏笔的形式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已选隐性传递作为伏笔埋设时，将读者可见的实际细节、出现章场和后续证实的位置对应到现有承诺。

159581｜{"id":"C00764","source":"35.1_隐性传递","target":"65.2_读者不确定性管理","type":"触发链","condition":"隐性传递制造不确定性","priority":1,"effect":"隐性传递制造读者不确定性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】采用隐性传递保留不确定性时，在 reader_plan 记录哪些真实迹象已出现、有哪些可成立的解释以及后来怎样排除。

159995｜{"id":"C00766","source":"35.1_隐性传递","target":"65.2_不确定性","type":"转化","condition":"隐性传递制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】既有线索被间接呈现时，核对读者当前能从实际章场推断什么，给有据可查的剩余疑问留出后续回应。

160210｜{"id":"C00767","source":"35.2_张力设计","target":"130_核心悬念","type":"触发链","condition":"张力是核心悬念来源","priority":1,"effect":"张力设计是核心悬念来源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已将张力用作核心悬念来源时，按作品实有矛盾、疑问和变化征象核对何处出现线索以及何时解决。

160823｜{"id":"C00770","source":"35.2_张力设计","target":"130_核心悬念","type":"绑定","condition":"张力是悬念来源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】围绕作者已定的悬念和目前已有张力，把双方可观察的信号、事件转折及能够答复的问题逐项对应。

161468｜{"id":"C00773","source":"35.3_半透明","target":"65.2_读者不确定性管理","type":"触发链","condition":"半透明制造不确定性","priority":1,"effect":"半透明制造读者不确定性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作采用半透明来维持不确定性时，按已有线索和未解释事实规划可验证的前后信息顺序及读者可作判断的范围。

161667｜{"id":"C00774","source":"35.3_半透明","target":"143.1_不确定性","type":"转化","condition":"半透明是不确定性来源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确定半透明设定影响悬念时，在实际章场定位可见部分、尚待回答的疑问和下一次能够查证的事件。

161882｜{"id":"C00775","source":"35.4_不变量","target":"130_核心悬念","type":"嵌套链","condition":"不变量是悬念锚点","priority":1,"effect":"不变量是核心悬念的锚点","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已经将不变量作为悬念依据时，用它在具体事件中的重复表现或限制核对何处可以排除错误解释、何时能确认答案。

162296｜{"id":"C00777","source":"35.4_不变量","target":"130_核心悬念","type":"绑定","condition":"不变量是悬念锚点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在既定悬念中，用已确认的不变量核对实际事件提供的线索、可能解释和值得保留的回应条件。

162511｜{"id":"C00778","source":"35.4_不变量","target":"132_创作承诺","type":"触发链","condition":"不变量是承诺的根基","priority":2,"effect":"不变量是创作承诺的根基","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用某项不变量形成创作承诺时，把作者确认的约束对应后续能被读者辨认的具体事件及其兑现位置。

165999｜{"id":"C00795","source":"36.5_种族进化","target":"4.1_弧光","type":"演化","condition":"种族进化伴随弧光；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已将种族变化与人物弧光相连时，用实际人物的选择、变化后的行为和后果核对各自作用。

169953｜{"id":"C00814","source":"37.5_构造的可改善性","target":"4.1_弧光","type":"演化","condition":"构造改善伴随弧光；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选构造改善作为人物弧光的一环时，用实际行为和改变后的选择核对变化的具体位置与后果。

170168｜{"id":"C00815","source":"37.5_构造的可改善性","target":"4.1_弧光五阶段","type":"触发链","condition":"构造改善伴随弧光","priority":1,"effect":"构造改善伴随弧光","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】构造改善已进入人物弧光时，把原限制、采取的选择、可见改善及后续行为差异对应到已设阶段。

171406｜{"id":"C00821","source":"38.1_能力反哺构造","target":"4.1_弧光","type":"演化","condition":"反哺伴随弧光；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已把能力反哺安排为弧光节点时，用实际选择、身体或构造变化和后续行为核对其叙事作用。

172025｜{"id":"C00824","source":"38.2_能力上限突破","target":"44.3_爽点-代价","type":"共振","condition":"突破伴随代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用突破伴随代价和回报时，把实际选择、支付时点及突破结果放进同一因果，明确接下来仍受什么约束。

173498｜{"id":"C00831","source":"39.1_职业类型","target":"39.9_剧情驱动","type":"转化","condition":"职业驱动剧情；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已选职业作为剧情动力时，用具体工作、人物目标和真实阻碍安排它在实际事件中的推进作用。

175417｜{"id":"C00840","source":"39.5_职业晋升","target":"4.1_弧光五阶段","type":"触发链","condition":"晋升伴随弧光","priority":1,"effect":"职业晋升伴随弧光","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用职业晋升推动人物弧光时，把获得机会、选择和可见改变对应到项目实际阶段与后果。

175616｜{"id":"C00841","source":"39.5_职业晋升","target":"4.1_弧光","type":"演化","condition":"职业晋升伴随弧光；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有晋升路线参与角色变化时，用实际事件、付出成本和行为前后差异核对它改变了哪一个人物选择。

177121｜{"id":"C00848","source":"39.9_职业与剧情驱动","target":"122.1_剧情推进","type":"触发链","condition":"职业驱动剧情","priority":1,"effect":"职业驱动剧情推进","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已用职业推动情节时，把实际职业使命、角色选择与发生的后果落实到可推进的事件。

177320｜{"id":"C00849","source":"39.9_职业与剧情驱动","target":"42.1_引力中心","type":"绑定","condition":"职业驱动引力中心；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有职业目标关联故事引力中心时，在实际章场核对它如何影响核心问题或人物长程选择。

177750｜{"id":"C00851","source":"4.1_弧光终点","target":"112.5_收尾","type":"绑定","condition":"结局；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光终点」经「绑定」影响「112.5_收尾」（条件：结局）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

177965｜{"id":"C00852","source":"4.1_弧光终点","target":"41.5_闭环","type":"绑定","condition":"呼应开篇；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光终点」经「绑定」影响「41.5_闭环」（条件：呼应开篇）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

178180｜{"id":"C00853","source":"4.1_弧光触发","target":"4.3_演变节奏","type":"转化","condition":"决定速度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光触发」经「转化」影响「4.3_演变节奏」（条件：决定速度）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

178395｜{"id":"C00854","source":"4.1_弧光触发","target":"44.1_爽点","type":"共振","condition":"触发爽点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光触发」经「共振」影响「44.1_爽点」（条件：触发爽点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

178610｜{"id":"C00855","source":"4.1_弧光起点","target":"4.2_演变方向","type":"转化","condition":"→；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光起点」经「转化」影响「4.2_演变方向」（条件：→）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

179040｜{"id":"C00857","source":"4.1_弧光转折","target":"4.4_成长代价","type":"绑定","condition":"伴随代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光转折」经「绑定」影响「4.4_成长代价」（条件：伴随代价）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

179255｜{"id":"C00858","source":"4.1_弧光转折","target":"155.1_缓冲","type":"约束","condition":"需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光转折」经「约束」影响「155.1_缓冲」（条件：需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

179470｜{"id":"C00859","source":"4.1_弧光顶点","target":"130_核心悬念","type":"绑定","condition":"解决；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光顶点」经「绑定」影响「130_核心悬念」（条件：解决）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

179685｜{"id":"C00860","source":"4.1_弧光顶点","target":"44.6_大爽点","type":"共振","condition":"重合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.1_弧光顶点」经「共振」影响「44.6_大爽点」（条件：重合）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

180115｜{"id":"C00862","source":"4.2_演变方向","target":"158.1_认知阶梯","type":"转化","condition":"体现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用认知阶梯来表现人物演变时，用可观察的人物发现、判断和选择核对变化方向及实际章场位置。

180330｜{"id":"C00863","source":"4.3_演变节奏","target":"61.1_重章","type":"绑定","condition":"加速；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选择重章承载演变加速时，把真实行动和后果落在已定章序，核对哪一项人物变化加快及读者能看到的依据。

180545｜{"id":"C00864","source":"4.3_演变节奏","target":"155.1_缓冲","type":"约束","condition":"减速；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.3_演变节奏」经「约束」影响「155.1_缓冲」（条件：减速）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

180975｜{"id":"C00866","source":"4.4_成长代价","target":"44.3_爽点-代价","type":"共振","condition":"同步；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品确将成长代价与回报放在同一因果内时，用实际付出、角色选择与可观察收获核对兑现位置。

181190｜{"id":"C00867","source":"4.5_成长中断","target":"155.1_缓冲","type":"约束","condition":"需缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「4.5_成长中断」经「约束」影响「155.1_缓冲」（条件：需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

183308｜{"id":"C00877","source":"40.3_技能学习条件","target":"4.1_弧光","type":"演化","condition":"技能学习伴随弧光；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色确因学习某项技能在选择上发生变化时，把实际学习、障碍与后续行为对应已有弧光节点。

185012｜{"id":"C00885","source":"41.1_三幕结构","target":"123.4_黄金三章","type":"绑定","condition":"黄金三章对应三幕开端；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已采用三幕和黄金三章时，用现有开篇事件、人物目标及承诺核对第一幕开端实际需要承担的任务。

185227｜{"id":"C00886","source":"41.1_三幕结构","target":"130_核心悬念","type":"绑定","condition":"核心悬念在三幕中解决；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已用三幕承接核心悬念时，把问题建立、线索变化与回应分别对应到真实事件和选定幕段。

185442｜{"id":"C00887","source":"41.1_三幕结构","target":"41.2_15节拍","type":"转化","condition":"三幕是15节拍框架；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已决定使用三幕和十五节拍时，将现有事件因果与实际节拍作用对照，核对每个节拍在所选幕段承担什么。

185657｜{"id":"C00888","source":"41.1_三幕结构","target":"41.2_15节拍结构","type":"嵌套链","condition":"三幕是15节拍框架","priority":1,"effect":"三幕结构是15节拍的框架","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品用三幕提供十五节拍框架时，在结构设计逐项排列选定节拍及真实事件，依据本作篇幅和转折要求决定落点。

185856｜{"id":"C00889","source":"41.1_三幕结构","target":"61.1_重章","type":"绑定","condition":"重章对应三幕高潮；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选重章承载相关幕段高潮时，将实有转折、人物选择及结果对应具体章任务，核对前后节奏。

186071｜{"id":"C00890","source":"41.1_三幕结构","target":"61.1_重章","type":"触发链","condition":"重章对应三幕高潮","priority":1,"effect":"重章对应三幕高潮","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作使用重章表现三幕高潮时，写明这一重章承接的已知冲突与变局，以及读者在哪个位置看到结果。

186270｜{"id":"C00891","source":"41.2_15节拍结构","target":"62.1_章节节奏轮换","type":"触发链","condition":"节拍决定节奏","priority":1,"effect":"15节拍决定节奏","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有十五节拍和章序时，用具体事件强弱、信息量和已定节奏轮换核对哪些章承担变化及缓冲。

186469｜{"id":"C00892","source":"41.2_15节拍结构","target":"62.1_节奏轮换","type":"绑定","condition":"15节拍决定节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用十五节拍影响轮换时，对照实际章内行动密度与关键节拍，用已定章序安排下一次升降的依据。

186684｜{"id":"C00893","source":"41.2_15节拍结构","target":"44.1_爽点压抑","type":"嵌套","condition":"15节拍包含爽点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已采用十五节拍及压抑释放安排时，把已选压力、人物受限和释放位置分别对应到具体事件。

186899｜{"id":"C00894","source":"41.2_15节拍结构","target":"48.4_章尾钩子","type":"嵌套","condition":"15节拍包含钩子；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目将选定节拍放在章尾时，用当前章已完成的事件和剩余问题安排钩子，保留后章回应。

187329｜{"id":"C00896","source":"41.3_起承转合","target":"122.1_剧情推进","type":"绑定","condition":"起承转合推进剧情；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用起承转合推进目前剧情时，将项目实际问题、阻碍、改变和结果按已定章节联系起来。

187544｜{"id":"C00897","source":"41.5_闭环结构","target":"112.1_开篇设计","type":"绑定","condition":"闭环需要开篇设计；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「41.5_闭环结构」经「绑定」影响「112.1_开篇设计」（条件：闭环需要开篇设计）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

187759｜{"id":"C00898","source":"41.5_闭环结构","target":"112.5_收尾设计","type":"绑定","condition":"闭环需要收尾设计；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「41.5_闭环结构」经「绑定」影响「112.5_收尾设计」（条件：闭环需要收尾设计）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

187974｜{"id":"C00899","source":"41.5_闭环结构","target":"132.1_创作承诺","type":"绑定","condition":"闭环兑现承诺；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已定闭环结构和创作承诺时，用开篇可见的承诺与后期实际选择、结果或余波对应兑现位置。

188189｜{"id":"C00900","source":"41.6_多线并行","target":"154.1_主线","type":"嵌套","condition":"多线包含主线；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用多线并行时，先用作者已选主线任务和实际转折确定主线承担的事件，再核对其与其他线的交点。

188404｜{"id":"C00901","source":"41.6_多线并行","target":"154.2_支线","type":"嵌套","condition":"多线包含支线；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有多条支线时，将各自角色目标、实际启动、独立结果和与主线相接的位置纳入现有章序。

188619｜{"id":"C00902","source":"41.6_多线并行","target":"121.9_配角独立行动","type":"嵌套","condition":"多线包含配角行动线；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】配角行动线已被创作者纳入并行结构时，用配角的独立目标及已发生或拟发生的事件说明该线对其他线的具体影响。

188834｜{"id":"C00903","source":"42.1_引力中心","target":"130_核心悬念","type":"绑定","condition":"引力中心是核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已把核心悬念作为故事引力中心时，将实际悬念、人物所追问的事实和可核回应位置落实到章场。

189049｜{"id":"C00904","source":"42.1_引力中心","target":"154.1_主线","type":"绑定","condition":"引力中心是主线；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品以主线承担引力中心时，按已有长期目标、关键事件和回合结果核对当前事件怎样继续牵引主线。

189264｜{"id":"C00905","source":"42.1_引力中心","target":"3.2_执念","type":"绑定","condition":"引力中心是执念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选某人物执念承担故事引力时，使用真实压力、选项与后果安排执念在各章真正牵动的决定。

189479｜{"id":"C00906","source":"42.1_引力中心","target":"41.1_三幕","type":"嵌套","condition":"引力中心是三幕核心；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用三幕结构时，在各幕的真实目标、阻碍及转折上核对本作引力中心怎样持续起作用。

189694｜{"id":"C00907","source":"42.1_引力中心设计","target":"130_核心悬念","type":"触发链","condition":"引力中心是核心悬念","priority":1,"effect":"引力中心是核心悬念","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品以核心悬念组织引力中心时，明确已设问题在哪些事件建立、改变和回应，并核对读者可得依据。

189893｜{"id":"C00908","source":"42.1_引力中心设计","target":"3.2_角色执念","type":"嵌套链","condition":"引力中心是执念","priority":1,"effect":"引力中心是角色执念","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者选用执念作为引力中心时，用人物实际所求、被挑战或强化的位置及后续选择确认牵引效果。

190092｜{"id":"C00909","source":"42.2_进度脉动","target":"62.1_节奏轮换","type":"转化","condition":"进度脉动影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据已设章序及推进节点，将实际获得线索、改变处境或遭受阻碍的位置对应节奏轮换。

190307｜{"id":"C00910","source":"42.2_进度脉动","target":"122.3_推进速度","type":"转化","condition":"进度脉动决定推进速度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作以进度脉动调节速度时，用当前事件中可见的推进量、信息变化和确有停顿的地方核对读者所感进展。

190522｜{"id":"C00911","source":"42.2_进度脉动","target":"64.1_读者情绪","type":"转化","condition":"进度脉动影响读者情绪；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「42.2_进度脉动」经「转化」影响「64.1_读者情绪」（条件：进度脉动影响读者情绪）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

190737｜{"id":"C00912","source":"42.2_进度脉动感","target":"62.1_章节节奏轮换","type":"触发链","condition":"进度影响节奏","priority":2,"effect":"进度脉动影响节奏","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】根据相邻章已有行动结果、信息累积和主要变化分配快慢，给章序保留真实的升压和停顿依据。

190936｜{"id":"C00913","source":"42.3_密度设计","target":"61.1_重章","type":"绑定","condition":"重章密度高；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实际重章承载高密度情节时，用相互影响的事件、关键选择及足以承担的后果核对该章需要完成的任务。

191151｜{"id":"C00914","source":"42.3_密度设计","target":"61.3_轻章","type":"绑定","condition":"轻章密度低；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选用轻章处理低密度段落时，保留实际人物反应、信息或余波的功能，明确下一章要承接的事实。

191995｜{"id":"C00918","source":"42.5_余波链","target":"42.1_引力中心","type":"转化","condition":"余波链影响引力中心；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】余波确实影响引力中心时，在事件因果中明确何项已有后果改变了人物的实际选择或故事主问题。

193269｜{"id":"C00924","source":"42.7_配角发起转折","target":"121.9_配角独立行动","type":"触发链","condition":"转折是配角行动","priority":1,"effect":"配角转折是独立行动线的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】一次已定转折由配角独立行动引出时，用该人实际目标、动作、可查结果和主线变化明确配角线承担的任务。

193468｜{"id":"C00925","source":"42.8_失败设计","target":"44.3_爽点-代价","type":"绑定","condition":"失败是代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已把真实失败用作回报前后的代价时，按当前章场明确失去什么、导致何种选择以及以后怎样回应。

193683｜{"id":"C00926","source":"42.8_失败设计","target":"44.3_爽点-代价同步","type":"触发链","condition":"失败是代价","priority":1,"effect":"失败设计是代价的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】选定失败确实参与代价与回报的设计时，以实际行动、失败结果和后续恢复或选择核对兑现的因果。

193882｜{"id":"C00927","source":"42.8_失败设计","target":"155.1_缓冲","type":"约束","condition":"失败需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「42.8_失败设计」经「约束」影响「155.1_缓冲」（条件：失败需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

194312｜{"id":"C00929","source":"43.10_冲突类型轮换","target":"62.1_节奏轮换","type":"绑定","condition":"冲突轮换影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作使用冲突类型轮换时，对照所选章序、实际矛盾及事件结果安排何时升压或转题，并明确前后联系。

194527｜{"id":"C00930","source":"43.10_冲突类型轮换","target":"43.1_资源争夺","type":"转化","condition":"可轮换；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用资源争夺作为轮换的一个冲突时，用真实双方、资源缺口和已定章场核对它从哪里开始及产生什么改变。

194742｜{"id":"C00931","source":"43.10_冲突类型轮换","target":"43.2_信息博弈","type":"转化","condition":"可轮换；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】信息博弈作为已选轮换项时，将实际知情差、人物行动与能影响下一段的结果对应到当前章序。

196215｜{"id":"C00938","source":"43.1_资源争夺","target":"44.1_爽点压抑","type":"触发","condition":"争夺制造压抑；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】资源争夺已被选择来积累压抑时，用项目实有阻力、人物受到的限制和前后事件明确读者何处感到受阻。

197473｜{"id":"C00944","source":"43.2_信息博弈","target":"45.1_伏笔","type":"嵌套","condition":"博弈制造伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「43.2_信息博弈」经「嵌套」影响「45.1_伏笔」（条件：博弈制造伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

198532｜{"id":"C00949","source":"43.4_道德困境","target":"44.3_爽点-代价同步","type":"触发链","condition":"道德困境有代价","priority":1,"effect":"道德困境有代价","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有具体道德困境要承担情节代价时，用实际选择、丢失或承担的结果及后续回报核对因果与兑现位置。

199575｜{"id":"C00954","source":"43.4_道德困境","target":"44.3_爽点-代价","type":"共振","condition":"困境有代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已用两难选择形成代价和回报时，在实际事件写明谁承担什么、何时看得到结果及之后的选择怎样受影响。

201263｜{"id":"C00962","source":"43.6_时间压力","target":"122.1_推进","type":"转化","condition":"压力推动推进；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用时间压力推动具体事件时，把真实期限、受影响的决定及期限前后可见结果安排现有章序。

202322｜{"id":"C00967","source":"43.8_预期反转","target":"45.11_反转类型","type":"嵌套链","condition":"反转是反转的一种","priority":1,"effect":"预期反转是反转的一种","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者已经采用预期反转时，用读者可见的前置证据、先前可以成立的预期和实际揭示核对其反转类型。

202521｜{"id":"C00968","source":"43.8_预期反转","target":"45.11_反转类型","type":"转化","condition":"反转是预期反转；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将已设预期反转安排在真实章场，核对读者依据哪些事实先作解释、后来哪个既有结果促成改判。

202951｜{"id":"C00970","source":"43.8_预期反转","target":"65.2_不确定性","type":"转化","condition":"反转制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已安排反转改变读者判断时，在 reader_plan 标明前文证据、仍可能成立的解释及实际事件会排除的内容。

203166｜{"id":"C00971","source":"43.9_冲突叠加","target":"44.8_高潮三层情感叠加","type":"触发链","condition":"叠加是高潮的一部分","priority":1,"effect":"冲突叠加是高潮的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品以冲突叠加形成高潮时，将实际冲突的来由、相互影响的选择和可感后果对应到选定情感层次。"""
