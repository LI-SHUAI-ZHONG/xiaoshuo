"""剧情设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 回报、伏笔、反转、章场节奏与悬念】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

204209｜{"id":"C00976","source":"44.1_爽点三压抑","target":"44.3_爽点-代价","type":"绑定","condition":"压抑伴随代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】压抑过程已产生代价时，把所限条件、人物确实付出的部分及后来的实际回报对应到章场。

204424｜{"id":"C00977","source":"44.1_爽点三压抑","target":"44.3_爽点-代价同步","type":"触发链","condition":"压抑伴随代价","priority":1,"effect":"爽点三压抑伴随代价","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用压抑与回报同步的安排时，以真实选择、前置受阻和仍要付出的代价核对兑现的发生位置。

204623｜{"id":"C00978","source":"44.1_爽点三压抑","target":"4.1_弧光","type":"演化","condition":"压抑推动弧光；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】既有压力实际推动弧光时，用受阻事件、角色的具体决定与后续行为差异确认改变落在哪个已设节点。

205881｜{"id":"C00984","source":"44.3_爽点-代价同步","target":"44.1_爽点压抑","type":"绑定","condition":"代价在压抑中积累；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有随压力积累的成本时，用具体受阻事件、人物行动和可感后果安排代价逐步出现的位置。

206096｜{"id":"C00985","source":"44.3_爽点-代价同步","target":"4.4_成长代价","type":"绑定","condition":"代价是成长一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品以代价承接人物成长时，把付出、得到的回报以及角色后来的实际选择对应到现有弧光。

206311｜{"id":"C00986","source":"44.4_小爽点分布","target":"61.1_重章","type":"绑定","condition":"小爽点对应重章；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选择重章承载某个小回报时，用具体前因、实际获益和会影响的下一步安排该章的位置。

206526｜{"id":"C00987","source":"44.4_小爽点分布","target":"61.1_重章","type":"触发链","condition":"小爽点对应重章","priority":2,"effect":"小爽点对应重章","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已定小回报落在实有重章时，对照章内冲突、人物选择和可辨结果，核对它是否完成本章相应任务。

206725｜{"id":"C00988","source":"44.4_小爽点分布","target":"62.1_节奏轮换","type":"绑定","condition":"小爽点决定节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选若干小回报时，用具体章序核对发生时点、相互间的压力或余波，以及节奏轮换的作用。

206940｜{"id":"C00989","source":"44.5_中爽点分布","target":"61.1_重章","type":"绑定","condition":"中爽点对应重章；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实有重章承担所选中等回报时，把累积事件、阶段性结果及承接它的后效落到项目章序。

207155｜{"id":"C00990","source":"44.5_中爽点分布","target":"62.1_节奏轮换","type":"绑定","condition":"中爽点决定节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作以中等回报调节轮换时，对照实际前置压力、兑现和余波安排章序中的升降及理由。

207370｜{"id":"C00991","source":"44.6_大爽点分布","target":"130_核心悬念","type":"触发链","condition":"大爽点解决悬念","priority":1,"effect":"大爽点解决核心悬念","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者已把大回报用来回应核心悬念时，以现有问题、证据和人物选择核对这一节点解决到哪一层。

207569｜{"id":"C00992","source":"44.6_大爽点分布","target":"44.7_高潮前奏","type":"绑定","condition":"大爽点需前奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有大回报及其前奏时，按所选事件安排前方具体压力、人物可察觉的变化和伏线出现的位置。

207784｜{"id":"C00993","source":"44.6_大爽点分布","target":"44.7_高潮前奏","type":"触发链","condition":"大爽点需要前奏","priority":1,"effect":"大爽点需要高潮前奏","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以本作已确认的高潮目标为前置，把前奏的真实信号、角色选择及最后的回报按因果对应起来。

207983｜{"id":"C00994","source":"44.6_大爽点分布","target":"44.8_高潮三层叠加","type":"转化","condition":"大爽点是高潮；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前大回报已作为高潮时，用项目实有的行动、人物情感和主题变化核对叠加效果与可感结果。

208198｜{"id":"C00995","source":"44.6_大爽点分布","target":"61.1_重章","type":"绑定","condition":"大爽点对应重章；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作将大回报放在已指定重章时，核对该章按实际章序兑现的是哪项承诺以及对后续任务的影响。

208413｜{"id":"C00996","source":"44.6_大爽点分布","target":"130_核心悬念","type":"绑定","condition":"大爽点解决核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确认在这一回报处解决核心悬念时，在 promise_plan 保存前置线索、当前解释和仍待回答的事实。

208628｜{"id":"C00997","source":"44.7_高潮前奏","target":"44.1_爽点三压抑","type":"触发链","condition":"前奏是压抑加深","priority":1,"effect":"高潮前奏是压抑的加深","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选高潮前奏承接已有压抑时，按角色正在遇到的限制、后果和可见征象增加已定事件的压力。

208827｜{"id":"C00998","source":"44.7_高潮前奏","target":"44.1_爽点压抑","type":"转化","condition":"前奏是压抑加深；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】现有前奏确用来加深压抑时，核对是哪个实际阻碍加重、人物如何应对以及后续要释放什么。

209042｜{"id":"C00999","source":"44.7_高潮前奏","target":"155.1_缓冲","type":"约束","condition":"前奏需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「44.7_高潮前奏」经「约束」影响「155.1_缓冲」（条件：前奏需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

209257｜{"id":"C01000","source":"44.7_高潮前奏","target":"62.1_节奏轮换","type":"转化","condition":"前奏是节奏一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以已定高潮事件和前后章序为依据，安排实际前奏出现的位置、速度变化及其承接的冲突。

209472｜{"id":"C01001","source":"44.8_高潮三层情感叠加","target":"44.6_大爽点","type":"转化","condition":"高潮是大爽点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已将三层情感叠加作为大回报时，核对各层在实际事件里可见的行动、变化及兑现结果。

210515｜{"id":"C01006","source":"44.8_高潮三层情感叠加","target":"64.1_读者情绪","type":"转化","condition":"高潮是读者情绪峰值；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「44.8_高潮三层情感叠加」经「转化」影响「64.1_读者情绪」（条件：高潮是读者情绪峰值）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

210730｜{"id":"C01007","source":"44.9_高潮余波","target":"155.1_情绪缓冲","type":"触发链","condition":"高潮后需要缓冲","priority":1,"effect":"高潮后需要情绪缓冲","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选高强度高潮后的读者情绪缓冲时，用实有余波、人物反应和下一步任务安排消化的位置。

210929｜{"id":"C01008","source":"44.9_高潮余波","target":"155.1_缓冲","type":"约束","condition":"余波是缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「44.9_高潮余波」经「约束」影响「155.1_缓冲」（条件：余波是缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

211574｜{"id":"C01011","source":"45.11_反转类型","target":"45.12_反转前奏","type":"绑定","condition":"反转需前奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已选反转，沿实际章序明确哪些事件先给出可复核信号、为哪项预期的改变作准备。

211789｜{"id":"C01012","source":"45.11_反转类型","target":"45.12_反转前奏","type":"触发链","condition":"反转需要前奏","priority":1,"effect":"反转需要前奏","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有计划反转需要前奏时，用当前已有线索与触发条件安排前奏及真正改判的位置。

211988｜{"id":"C01013","source":"45.11_反转类型","target":"130_核心悬念","type":"绑定","condition":"反转关联核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已选反转与核心悬念相连时，对照原疑问、解释变化和新证据安排实际揭示及其范围。

212203｜{"id":"C01014","source":"45.11_反转类型","target":"65.2_不确定性","type":"转化","condition":"反转制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定反转影响读者不确定性时，记录哪些解释先成立、何种事实后来改变它们及仍留的真实疑问。

212418｜{"id":"C01015","source":"45.12_反转前奏","target":"155.1_缓冲","type":"约束","condition":"前奏需缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「45.12_反转前奏」经「约束」影响「155.1_缓冲」（条件：前奏需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

212633｜{"id":"C01016","source":"45.12_反转前奏","target":"155.1_情绪缓冲","type":"触发链","condition":"前奏需要缓冲","priority":2,"effect":"反转前奏需要缓冲","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品确在反转前奏安排读者情绪缓冲时，按实际事件强度和既定章序写明停顿或余波的位置及用途。

212832｜{"id":"C01017","source":"45.12_反转前奏","target":"45.16_伏笔联动","type":"绑定","condition":"前奏联动伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】反转前奏已关联伏笔时，在 promise_plan 对照此前安置的实际线索、前奏中的变化与后续可核回收。

213047｜{"id":"C01018","source":"45.13_反转余响","target":"155.1_缓冲","type":"约束","condition":"余响是缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「45.13_反转余响」经「约束」影响「155.1_缓冲」（条件：余响是缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

213477｜{"id":"C01020","source":"45.14_反转时机","target":"65.2_不确定性","type":"转化","condition":"时机影响不确定性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已定反转时机时，依据读者当前可得证据与还能成立的解释核对何时真正改变判断。

213692｜{"id":"C01021","source":"45.14_反转时机","target":"130_核心悬念","type":"转化","condition":"时机关联核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选反转牵动实际核心悬念时，明确在哪一章场推进或回应哪一问，保留本作剩余的开放范围。

213907｜{"id":"C01022","source":"45.15_反转合理性","target":"45.1_伏笔埋设","type":"触发链","condition":"合理性需要伏笔","priority":1,"effect":"反转合理性需要伏笔","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已安排反转需要前文依据时，把可回查的实际伏笔、安置位置和揭示动作对应起来，使反转可以复核。

214106｜{"id":"C01023","source":"45.16_伏笔与反转联动","target":"45.7_伏笔网络","type":"嵌套","condition":"联动是网络一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当作品使用伏笔与反转联动时，将当前实有线索和相关反转的前后位置连入现有伏笔网络。

214321｜{"id":"C01024","source":"45.16_伏笔与反转联动","target":"45.7_伏笔网络","type":"嵌套链","condition":"联动是网络的一部分","priority":1,"effect":"联动是伏笔网络的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作有已确认的伏笔网络时，核对联动节点承担的线索输入、反转触发及后续回收，沿用原先的伏笔记录。

214520｜{"id":"C01025","source":"45.16_伏笔与反转联动","target":"130_核心悬念","type":"绑定","condition":"联动是核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已明确联动服务核心悬念时，在实际事件里说明哪条伏笔来自哪里、何时因反转改变及会解释什么。

214735｜{"id":"C01026","source":"45.17_预感制造","target":"130_核心悬念","type":"绑定","condition":"预感是悬念铺垫；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「45.17_预感制造」经「绑定」影响「130_核心悬念」（条件：预感是悬念铺垫）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

214950｜{"id":"C01027","source":"45.17_预感制造","target":"45.1_伏笔","type":"转化","condition":"预感是伏笔前奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「45.17_预感制造」经「转化」影响「45.1_伏笔」（条件：预感是伏笔前奏）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

215165｜{"id":"C01028","source":"45.17_预感制造","target":"65.2_不确定性","type":"转化","condition":"预感制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「45.17_预感制造」经「转化」影响「65.2_不确定性」（条件：预感制造不确定性）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

215794｜{"id":"C01031","source":"45.1_伏笔埋设","target":"45.2_伏笔休眠","type":"演化","condition":"埋设→休眠；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】某条伏笔已经安置时，在当前章序记录其埋设点、进入休眠的事件及后来再次可见的条件。

216009｜{"id":"C01032","source":"45.1_伏笔埋设","target":"45.2_伏笔休眠期","type":"触发链","condition":"埋设后休眠","priority":1,"effect":"伏笔埋设后进入休眠期","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有项目伏笔进入休眠安排时，在 promise_plan 记录实际线索、被暂时搁置的范围和计划再出现的触发。

216208｜{"id":"C01033","source":"45.1_伏笔埋设","target":"130_核心悬念","type":"绑定","condition":"伏笔指向核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作明确一条伏笔指向核心悬念时，显示实际安置的信息怎样对应待答疑问及以后可查的回应。

216423｜{"id":"C01034","source":"45.1_伏笔埋设","target":"45.5_伏笔密度","type":"转化","condition":"埋设决定密度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次采用伏笔密度规则时，以本书实有线索、所处章序及本作口径核对埋设数量和各自承担的问题。

216638｜{"id":"C01035","source":"45.2_伏笔休眠期","target":"45.3_伏笔揭示","type":"演化","condition":"休眠→揭示；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已安排休眠后的揭示时，用此前确有的痕迹、实际时点和新取得的信息核对揭示的适用范围。

216853｜{"id":"C01036","source":"45.2_伏笔休眠期","target":"45.3_伏笔揭示","type":"触发链","condition":"休眠后被揭示","priority":1,"effect":"休眠期后被揭示","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】在选定章场安排已有休眠线索的重新出现，用可查事件和人物当时所知核对何时足以解释它。

217052｜{"id":"C01037","source":"45.2_伏笔休眠期","target":"65.2_读者不确定性管理","type":"触发链","condition":"休眠期制造不确定性","priority":1,"effect":"伏笔休眠期制造不确定性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用伏笔休眠造成读者疑问时，记录当前仍可成立的解释、实有线索及恢复验证的触发。

217251｜{"id":"C01038","source":"45.2_伏笔休眠期","target":"65.2_不确定性","type":"转化","condition":"休眠制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在 reader_plan 保留休眠期间读者已经接触的细节和仍未确定的事实，对应后面可验证的时点。

217466｜{"id":"C01039","source":"45.3_伏笔揭示","target":"130_核心悬念","type":"绑定","condition":"揭示核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次揭示处置实际核心悬念时，按先前线索和新事件写明解答的具体问题以及此后仍保留的未知。

217681｜{"id":"C01040","source":"45.3_伏笔揭示","target":"65.2_不确定性","type":"转化","condition":"揭示减少不确定性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实际伏笔被揭示时，用可查新证据说明会排除哪些既有解释和留下哪些合理疑问。

217896｜{"id":"C01041","source":"45.3_伏笔揭示","target":"65.2_读者不确定性管理","type":"触发链","condition":"揭示减少不确定性","priority":1,"effect":"伏笔揭示减少不确定性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对已经安排的揭示核对读者从哪一事件得到答案，记录此前假设的变化与仍需后续验证的部分。

218310｜{"id":"C01043","source":"45.4_伏笔延迟解码","target":"45.3_伏笔揭示","type":"嵌套链","condition":"延迟解码是揭示的一种","priority":1,"effect":"延迟解码是揭示的一种","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已将线索延迟理解作为揭示方式时，用此前实际看见的内容、当时的解释和后来能证实的事件保持因果。

218509｜{"id":"C01044","source":"45.4_伏笔延迟解码","target":"45.7_伏笔网络","type":"嵌套","condition":"延迟解码是网络一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品有多条伏笔联动时，给当前延迟解码的线索记录安置节点、与其他线索相接位置和真正理解它的事件。

218724｜{"id":"C01045","source":"45.4_伏笔延迟解码","target":"65.2_不确定性","type":"转化","condition":"延迟解码延长不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目用延迟解码维持不确定性时，在 reader_plan 标明现有证据足以理解的部分、仍缺内容与预计揭示的位置。

218939｜{"id":"C01046","source":"45.5_伏笔密度","target":"45.1_伏笔埋设","type":"触发链","condition":"密度决定埋设","priority":1,"effect":"伏笔密度决定埋设数量","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对已选密度规则和现有章节，核对实际打算埋设的线索数量、各自任务及以后可核回收的范围。

219138｜{"id":"C01047","source":"45.5_伏笔密度","target":"48.1_起承转合","type":"转化","condition":"密度影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本章采用起承转合且控制伏笔密度时，将实际埋设、暂留和揭示对应具体章内节点及节奏需要。

219353｜{"id":"C01048","source":"45.5_伏笔密度","target":"45.1_伏笔","type":"转化","condition":"密度决定埋设；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「45.5_伏笔密度」经「转化」影响「45.1_伏笔」（条件：密度决定埋设）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

219783｜{"id":"C01050","source":"45.6_伏笔回收率","target":"132.1_创作承诺","type":"绑定","condition":"回收率兑现承诺；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确定某些伏笔承担创作承诺时，沿时间线写明实际读者预期、计划回收事件及承诺兑现的可核证据。

219998｜{"id":"C01051","source":"45.7_伏笔网络","target":"130_核心悬念","type":"绑定","condition":"网络是核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】如果项目伏笔网络确实支撑同一核心悬念，用实有线索、相互依赖和验证顺序对应待回答的问题。

220213｜{"id":"C01052","source":"45.7_伏笔网络","target":"130_核心悬念","type":"触发链","condition":"网络是核心悬念","priority":1,"effect":"伏笔网络是核心悬念","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者将伏笔网络用于核心悬念时，核对哪些线索共同解释哪个事实、在各章按什么先后可被验证。

220412｜{"id":"C01053","source":"45.7_伏笔网络","target":"45.1_伏笔","type":"转化","condition":"网络是伏笔集合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「45.7_伏笔网络」经「转化」影响「45.1_伏笔」（条件：网络是伏笔集合）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

220627｜{"id":"C01054","source":"45.7_伏笔网络","target":"45.1_伏笔埋设","type":"嵌套链","condition":"网络是伏笔的集合","priority":1,"effect":"伏笔网络是伏笔的集合","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】现有伏笔网络已包含实际埋设时，在已定章序把每条线索对应各自出现的事件、作用与后续证实的位置。

229266｜{"id":"C01095","source":"47.2_对抗回合","target":"44.1_爽点三压抑","type":"嵌套链","condition":"回合是压抑的一部分","priority":1,"effect":"对抗回合是爽点压抑","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选对抗回合承担压抑时，用实际失败、受阻范围或代价累积安排后续释放的证据。

230110｜{"id":"C01099","source":"47.2_对抗回合","target":"44.1_爽点压抑","type":"嵌套","condition":"回合是爽点压抑；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】使用对抗积累读者感到的压力时，把某回合实际受阻、对方应对和后面会释放的矛盾放入既定章场。

230755｜{"id":"C01102","source":"47.4_对抗回合强度","target":"44.1_爽点压抑","type":"转化","condition":"强度影响爽点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作以回合强度影响压抑时，核对真实风险、人物所知和付出如何变化，并安排后续可见的释放依据。

230970｜{"id":"C01103","source":"47.4_对抗回合强度","target":"61.1_重章","type":"绑定","condition":"重章用高强度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】现有重章已安排较高强度的回合时，用已知行动和关键结果核对该章承担的冲突及节奏。

232658｜{"id":"C01111","source":"47.7_冲突类型轮换","target":"62.1_节奏轮换","type":"绑定","condition":"轮换影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已经采用冲突轮换时，依据具体章序及可查结果安排哪一项冲突如何接到下一项。

232873｜{"id":"C01112","source":"47.7_冲突类型轮换","target":"43.1_资源争夺","type":"转化","condition":"可轮换；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】资源争夺已进入轮换方案时，保留真实参争者、已有资源缺口及它与当前相邻冲突的因果联系。

233932｜{"id":"C01117","source":"48.13_章节连续性","target":"122.5_跨章连续性","type":"转化","condition":"连续性是跨章连续性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用真实相邻章序核对前章行动结果、尚存问题和后章回应之间的承接，并保留共享的状态事实。

235190｜{"id":"C01123","source":"48.1_起承转合","target":"122.1_推进","type":"绑定","condition":"起承转合推进剧情；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用章内起承转合推进时，按实际事件核对起点、变化、兑现或届时仍开放的疑问。

236249｜{"id":"C01128","source":"48.3_结尾规则","target":"65.2_不确定性","type":"转化","condition":"结尾制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本章确实选用结尾保留未知时，用读者可见的结果和已确认的范围列出仍可成立的解释。

236464｜{"id":"C01129","source":"48.4_章尾钩子","target":"123.16_连载节奏","type":"绑定","condition":"钩子维持追更；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品采用连载节奏时，用现有章尾事件、已兑现的部分和可核后续回应安排所用钩子。

236679｜{"id":"C01130","source":"48.4_章尾钩子","target":"65.2_不确定性","type":"触发","condition":"钩子制造悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有章尾悬念时，在 reader_plan 记下当前事件还未说明的实际问题、已有线索和能继续查证的条件。

236894｜{"id":"C01131","source":"48.4_章尾钩子","target":"48.13_章节连续性","type":"约束","condition":"钩子需下章回应；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已有章尾钩子与实际下一章，安排最先承接的事件和能够回应多少，保留前后章状态。

237109｜{"id":"C01132","source":"48.4_钩子设计","target":"65.2_读者不确定性管理","type":"触发链","condition":"钩子制造不确定性","priority":1,"effect":"钩子制造读者不确定性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已选钩子维持不确定性时，以目前可得真实线索和开放解释规划其后验证的章场。

237308｜{"id":"C01133","source":"48.5_悬念管理","target":"130_核心悬念","type":"嵌套链","condition":"悬念是核心悬念","priority":1,"effect":"悬念管理是核心悬念","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有核心悬念管理安排时，把实有主问题、阶段线索和回答时点对应到项目事件及章序。

237507｜{"id":"C01134","source":"48.5_悬念管理","target":"130_核心悬念","type":"转化","condition":"悬念管理是核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对作者已经确认的核心悬念，用实际线索、人物行动和各次回应核对本章任务及下一步要解决的问题。

237722｜{"id":"C01135","source":"48.5_悬念管理","target":"65.2_不确定性","type":"转化","condition":"悬念管理制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次悬念设计需要保留具体未知时，用现有证据标明还可成立的解释、读者可得信息及计划揭示。

237937｜{"id":"C01136","source":"48.6_信息释放节奏","target":"45.1_伏笔","type":"嵌套","condition":"信息释放是伏笔；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「48.6_信息释放节奏」经「嵌套」影响「45.1_伏笔」（条件：信息释放是伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

238152｜{"id":"C01137","source":"48.6_信息释放节奏","target":"65.2_不确定性","type":"转化","condition":"信息释放影响不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按既有披露次序和实际事件核对读者各时点可知的事实、仍可成立的解释以及计划核验的位置。

238367｜{"id":"C01138","source":"48.7_情绪波形设计","target":"64.1_读者情绪","type":"转化","condition":"波形设计影响读者情绪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「48.7_情绪波形设计」经「转化」影响「64.1_读者情绪」（条件：波形设计影响读者情绪）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

238582｜{"id":"C01139","source":"48.7_情绪波形设计","target":"64.1_读者情绪波形","type":"触发链","condition":"波形是读者情绪基础","priority":1,"effect":"情绪波形设计是读者情绪基础","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选读者情绪波形时，用现有章场触发、角色选择与预期观感安排情绪转变，实际读者结果依可查反馈。

238781｜{"id":"C01140","source":"48.7_情绪波形设计","target":"62.1_节奏轮换","type":"转化","condition":"情绪波形影响节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已用情绪波形组织相邻章节时，以实际事件的情感峰谷、缓冲和变化原因核对节奏轮换。

244156｜{"id":"C01165","source":"5.4_关系演变","target":"4.1_弧光","type":"演化","condition":"关系演变伴随弧光；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已把关系变化作为弧光节点时，安排具体互动和前后选择，检查关系改变怎样影响已选弧光。

244371｜{"id":"C01166","source":"5.4_关系演变","target":"121.14_配角关系演变","type":"转化","condition":"配角关系演变；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有配角关系线时，用真实前值、关键互动及可见结果明确哪一事件改变其行为或剧情作用。

244801｜{"id":"C01168","source":"5.5_关系变化速度","target":"121.14_配角关系演变","type":"转化","condition":"决定演变速度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用关系变化速度作为配角线的一部分时，按实际章序和前后互动标出哪一步改变关系、变化持续多久。

245016｜{"id":"C01169","source":"5.5_关系变化速度","target":"62.1_节奏轮换","type":"绑定","condition":"速度影响节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】关系线确影响叙事节奏时，以实际关系进展、需要消化的后果及相邻事件核对章序中升降的位置。"""
