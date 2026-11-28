"""剧情设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 读者波形、认知转变、情感铺垫及弧光】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

260926｜{"id":"C01243","source":"58.4_全知视角","target":"142.3_全知视角未知","type":"绑定","condition":"全知也制造未知；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】全知叙述仍有本作明确保留的未知时，以已定章序和悬念核对当前可披露事实、读者所知及后续揭示位置。

261141｜{"id":"C01244","source":"59.1_主角POV","target":"120.14_主角视角优先级","type":"约束","condition":"主角POV有优先级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选主角视角优先规则时，将实际高强度推进或关键转折安排在项目已确定的视角，保留其他章场使用的理由。

267463｜{"id":"C01274","source":"6.1_基础情感_喜悦","target":"145.5_结果","type":"共振链","condition":"喜悦来自成功的结果","priority":2,"effect":"喜悦强化成功结果的正面反馈","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_喜悦」经「共振链」影响「145.5_结果」（条件：喜悦来自成功的结果）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

271173｜{"id":"C01292","source":"6.1_惊讶","target":"45.3_伏笔揭示","type":"共振","condition":"惊讶伴随揭示；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_惊讶」经「共振」影响「45.3_伏笔揭示」（条件：惊讶伴随揭示）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

275560｜{"id":"C01313","source":"6.4_存在情感","target":"158.1_认知阶梯","type":"触发链","condition":"存在情感在深度认知中被触发","priority":2,"effect":"存在情感推动认知阶梯向深度发展","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品有实际认知阶梯时，把人物深度理解的变化对应到已发生事件、所见事实及随后的行动。

275759｜{"id":"C01314","source":"6.4_存在情感","target":"158.1_认知阶梯","type":"转化","condition":"存在情感影响认知；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作选用存在情感推动认知时，以具体人物处境、由此领会的内容及后续选择确定现有认知阶段。

276173｜{"id":"C01316","source":"6.5_驱动情感","target":"122.1_剧情推进","type":"触发链","condition":"驱动情感存在","priority":1,"effect":"驱动情感推动剧情向前发展","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有驱动情感影响具体目标时，用实际行动及结果核对它如何推动已选事件和下一步章场任务。

283705｜{"id":"C01352","source":"61.1_重章","target":"155.1_缓冲","type":"约束","condition":"重章后需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「61.1_重章」经「约束」影响「155.1_缓冲」（条件：重章后需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

283920｜{"id":"C01353","source":"61.1_重章","target":"44.1_爽点","type":"绑定","condition":"重章爽点密集；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「61.1_重章」经「绑定」影响「44.1_爽点」（条件：重章爽点密集）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

284565｜{"id":"C01356","source":"61.2_中章","target":"155.1_缓冲","type":"转化","condition":"中章可作缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「61.2_中章」经「转化」影响「155.1_缓冲」（条件：中章可作缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

284780｜{"id":"C01357","source":"61.3_轻章","target":"155.1_情绪缓冲","type":"触发链","condition":"轻章是缓冲","priority":1,"effect":"轻章是情绪缓冲","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已经用轻章承接读者情绪时，安排已知高压事件后的真实人物反应、消化和下一段任务。

285624｜{"id":"C01361","source":"61.3_轻章","target":"155.1_缓冲","type":"转化","condition":"轻章是缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「61.3_轻章」经「转化」影响「155.1_缓冲」（条件：轻章是缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

285839｜{"id":"C01362","source":"61.4_空章","target":"69.1_心智模型","type":"转化","condition":"空章侧重心智；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选空章处理人物的理解或反思时，把真实事件后怎样修正旧解释以及后续选择对应到章序。

286269｜{"id":"C01364","source":"61.4_空章","target":"155.1_缓冲","type":"转化","condition":"空章是缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「61.4_空章」经「转化」影响「155.1_缓冲」（条件：空章是缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

286484｜{"id":"C01365","source":"62.1_章节节奏轮换","target":"48.11_节奏类型","type":"触发链","condition":"轮换决定节奏类型","priority":1,"effect":"轮换决定节奏类型","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用某项章序轮换时，从相邻章节已有冲突、余波和读者信息变化核对所选节奏类型。

286683｜{"id":"C01366","source":"62.1_章节节奏轮换","target":"48.11_节奏类型","type":"转化","condition":"轮换决定节奏类型；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用现有真实章序与各章职责说明节奏怎样由已选交替方式产生，并保留具体事件依据。

286898｜{"id":"C01367","source":"62.1_章节节奏轮换","target":"61.1_重章","type":"转化","condition":"轮换决定重章位置；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已有节奏轮换和实际重章时，依事件密度、主要转折及前后缓冲安排其所处位置。

287113｜{"id":"C01368","source":"62.1_章节节奏轮换","target":"155.1_缓冲","type":"约束","condition":"轮换需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「62.1_章节节奏轮换」经「约束」影响「155.1_缓冲」（条件：轮换需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

288817｜{"id":"C01376","source":"62.5_情绪承接","target":"64.1_读者情绪","type":"转化","condition":"承接是读者情绪一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「62.5_情绪承接」经「转化」影响「64.1_读者情绪」（条件：承接是读者情绪一部分）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

289032｜{"id":"C01377","source":"62.5_情绪承接","target":"64.1_读者情绪波形","type":"触发链","condition":"承接是波形的一部分","priority":1,"effect":"情绪承接是读者波形的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选情绪承接参与读者波形时，用相邻事件已经提供的结果和下次希望引出的感受核对拟定关联。

289231｜{"id":"C01378","source":"62.5_情绪承接","target":"155.1_缓冲","type":"转化","condition":"承接是缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「62.5_情绪承接」经「转化」影响「155.1_缓冲」（条件：承接是缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

289446｜{"id":"C01379","source":"62.7_呼吸曲线","target":"41.1_三幕","type":"转化","condition":"呼吸曲线是三幕一种；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已经选用三幕和呼吸曲线时，按实际事件强弱及现有幕段落实拟定的起伏、消化和收束。

289661｜{"id":"C01380","source":"62.7_呼吸曲线","target":"61.1_重章","type":"转化","condition":"重章是呼吸高点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前重章承担波形高点时，用选定转折、可感压力与已定结果核对本章在整体章序的作用。

289876｜{"id":"C01381","source":"62.7_呼吸曲线","target":"61.3_轻章","type":"转化","condition":"轻章是呼吸低点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选轻章放低强度时，依据真实前后事件、人物反应和仍在延续的问题明确波形位置。

290091｜{"id":"C01382","source":"64.1_读者情绪波形","target":"123.7_读者情绪波形","type":"转化","condition":"爆款情绪波形是读者波形细化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用相应商业节奏模型时，用作者选定的实际章场和预期情绪变化核对读者期待的组织，实际效果依反馈。

290306｜{"id":"C01383","source":"64.1_读者情绪波形","target":"48.7_情绪波形设计","type":"触发链","condition":"波形设计是基础","priority":1,"effect":"读者波形是章节波形的基础","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已确定作品尺度的读者情绪波形时，把具体章节承担的感受、事件及变化节点与全书计划对应。

290505｜{"id":"C01384","source":"64.1_读者情绪波形","target":"48.7_情绪波形设计","type":"转化","condition":"读者情绪波形是章节波形基础；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以已定读者波形与现有章序为前置，核对章内可见情绪变化、诱因及前后连续性。

290720｜{"id":"C01385","source":"64.1_读者情绪波形","target":"62.7_呼吸曲线","type":"触发链","condition":"波形是呼吸曲线的一部分","priority":1,"effect":"读者波形是呼吸曲线的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已把波形纳入呼吸曲线时，注明实际事件中哪些部分需增强、维持或舒缓，并保留对应章场。

290919｜{"id":"C01386","source":"64.1_读者情绪波形","target":"62.5_情绪承接","type":"转化","condition":"波形影响情绪承接；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已安排读者情绪延续时，用上场真实结果和下场会看见的触发核对情绪怎样传进新章场。

291134｜{"id":"C01387","source":"64.2_读者情绪峰值","target":"44.8_高潮三层叠加","type":"绑定","condition":"情绪峰值=高潮；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已将高潮作为情绪高点时，用实际行动、角色反应与所选主题落点确认层次及可感证据。

291349｜{"id":"C01388","source":"64.2_读者情绪峰值","target":"62.7_呼吸曲线","type":"转化","condition":"峰值是呼吸曲线部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】现有读者峰值已被安排在具体节点时，用实际事件前后的强弱对照它在章序呼吸曲线的位置。

291564｜{"id":"C01389","source":"64.3_读者情绪低谷","target":"44.1_爽点压抑","type":"绑定","condition":"低谷=压抑；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目采用压抑呈现读者情绪低谷时，以实际受限处境及所见结果定位需要承受的压力。

291779｜{"id":"C01390","source":"64.3_读者情绪低谷","target":"62.7_呼吸曲线","type":"转化","condition":"低谷是呼吸曲线部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将作者已定的低谷节点对应到既有事件、相关角色选择及以后真正回升的依据。

291994｜{"id":"C01391","source":"64.4_读者情绪梯度","target":"62.2_快慢交替","type":"转化","condition":"梯度影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已经确定情绪梯度变化时，以实际由缓至急或反向变化的片段核对节奏及真实触发。

292209｜{"id":"C01392","source":"64.4_读者情绪梯度","target":"62.7_呼吸曲线","type":"转化","condition":"梯度是呼吸曲线部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前波形有必要逐步转变时，按实有章场说明哪项信息或行动使阅读感受逐段改变。

292424｜{"id":"C01393","source":"64.5_读者情绪拐点","target":"45.11_反转类型","type":"转化","condition":"拐点=反转；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目以反转设置某个情绪拐点时，用已有预期、揭示事件及实际新证据定位发生的转折。

292639｜{"id":"C01394","source":"64.5_读者情绪拐点","target":"42.7_配角转折","type":"转化","condition":"拐点=转折；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】某个已设拐点由配角发起时，用其实际目标、行动和已选结果说明发生位置与后续影响。

292854｜{"id":"C01395","source":"64.6_读者情绪记忆","target":"66.1_读者情感记忆","type":"转化","condition":"情绪记忆=情感记忆；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已选反复出现的情感记忆时，给实际事件、物件或措辞留下前后可回查的情绪关联。

293069｜{"id":"C01396","source":"64.6_读者情绪记忆","target":"123.10_名场面","type":"绑定","condition":"情绪记忆是名场面基础；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作有拟形成记忆的名场面时，把实际人物选择、感受和后来能重现的线索放到已定章场。

293284｜{"id":"C01397","source":"64.7_读者情绪疲劳管理","target":"155.1_情绪缓冲","type":"约束","condition":"疲劳管理=缓冲；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已采用读者情绪疲劳管理时，依据既有高强度章场、前后余波及所选轻缓任务安排实际缓冲。

293499｜{"id":"C01398","source":"64.7_读者情绪疲劳管理","target":"62.5_情绪承接","type":"转化","condition":"疲劳影响承接；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】连续章节确需承接并调整读者情绪时，以项目实有事件和已披露信息核对上一段结束处及下一段的进入强度。

293714｜{"id":"C01399","source":"65.1_读者代入感","target":"119.1_共鸣点","type":"触发链","condition":"代入感与共鸣相关","priority":1,"effect":"读者代入感需要共鸣","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已选择由共鸣建立代入时，用真实角色处境、早期可见选择及后果确定读者可理解的具体内容。

293913｜{"id":"C01400","source":"65.1_读者代入感","target":"119.1_共鸣点","type":"转化","condition":"代入感与共鸣相关；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选共鸣点以承接读者代入时，把角色实际目标、相似或可理解经历及其首次出现位置写入 reader_plan。

294542｜{"id":"C01403","source":"65.1_读者代入感","target":"123.4_黄金三章","type":"绑定","condition":"代入感在开篇建立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用黄金三章且计划在开篇建立代入时，按实际人物目标、阻碍和早期选择安排可明确理解的情境。

294757｜{"id":"C01404","source":"65.2_读者不确定性","target":"45.1_伏笔","type":"嵌套","condition":"不确定性是伏笔；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「65.2_读者不确定性」经「嵌套」影响「45.1_伏笔」（条件：不确定性是伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

294972｜{"id":"C01405","source":"65.2_读者不确定性","target":"48.5_悬念管理","type":"转化","condition":"不确定性=悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已有明确悬念时，用读者现有所知、实际未知和可排除解释安排各次披露。

295187｜{"id":"C01406","source":"65.2_读者不确定性","target":"143.1_不确定性","type":"转化","condition":"读者不确定性=故事不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对照故事中尚未确定的实际结果和读者已经取得的事实，核对读者此时仍可支持哪些解释。

295402｜{"id":"C01407","source":"65.2_读者不确定性管理","target":"48.5_悬念管理","type":"嵌套链","condition":"不确定性是悬念","priority":1,"effect":"不确定性是悬念管理的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品把读者疑问纳入悬念管理时，按实有事件标明该疑问如何产生、何时可核及仍需保留的内容。

295816｜{"id":"C01409","source":"65.3_读者注意力","target":"45.1_伏笔","type":"嵌套","condition":"注意力引导是伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「65.3_读者注意力」经「嵌套」影响「45.1_伏笔」（条件：注意力引导是伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

296461｜{"id":"C01412","source":"65.5_读者预期管理","target":"45.11_反转","type":"转化","condition":"预期管理=反转；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已选反转改变读者预期时，用可确认的前置线索、原先成立的判断和后来解释核对变化。

296676｜{"id":"C01413","source":"65.5_读者预期管理","target":"65.2_不确定性","type":"转化","condition":"预期管理=不确定性管理；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】围绕既定预期写明读者何时得到何项证据、仍可怎样判断以及现有事件何时给出回应。

297106｜{"id":"C01415","source":"66.1_读者情感记忆","target":"123.10_名场面设计","type":"触发链","condition":"情感记忆是名场面","priority":1,"effect":"读者情感记忆是名场面的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已拟某场作为可回想的名场面时，安排实际人物选择、可感后果和后来能辨认的记忆对象。

297305｜{"id":"C01416","source":"66.1_读者情感记忆","target":"64.1_读者情绪","type":"转化","condition":"情感记忆=情绪波形；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「66.1_读者情感记忆」经「转化」影响「64.1_读者情绪」（条件：情感记忆=情绪波形）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

297520｜{"id":"C01417","source":"66.2_读者合上书体验","target":"112.5_收尾设计","type":"绑定","condition":"合上书体验=收尾；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「66.2_读者合上书体验」经「绑定」影响「112.5_收尾设计」（条件：合上书体验=收尾）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

299439｜{"id":"C01426","source":"67.2_注意","target":"45.1_伏笔","type":"嵌套","condition":"注意到的细节可作伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「67.2_注意」经「嵌套」影响「45.1_伏笔」（条件：注意到的细节可作伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

302202｜{"id":"C01439","source":"68.1_确认偏误","target":"45.1_伏笔误读","type":"嵌套","condition":"偏误导致读者误判；且当前故事明确采用该静态关系","priority":3,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「68.1_确认偏误」经「嵌套」影响「45.1_伏笔误读」（条件：偏误导致读者误判）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

307561｜{"id":"C01464","source":"69.4_心智模型破裂","target":"4.1_弧光五阶段","type":"触发链","condition":"破裂推动弧光","priority":1,"effect":"心智模型破裂推动弧光","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品以心智模型失效推动人物弧光时，用实际事件、受冲击想法和可见选择标出所选节点与后果。

307975｜{"id":"C01466","source":"69.4_心智模型破裂","target":"4.1_弧光转折","type":"绑定","condition":"破裂是弧光节点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「69.4_心智模型破裂」经「绑定」影响「4.1_弧光转折」（条件：破裂是弧光节点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

308405｜{"id":"C01468","source":"69.5_心智模型重塑","target":"4.1_弧光顶点","type":"绑定","condition":"重塑是弧光顶点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「69.5_心智模型重塑」经「绑定」影响「4.1_弧光顶点」（条件：重塑是弧光顶点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

313787｜{"id":"C01494","source":"7.5_情感铺垫","target":"44.7_高潮前奏","type":"触发链","condition":"情感铺垫为高潮服务","priority":1,"effect":"情感铺垫是高潮前奏的组成部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已用情感铺垫为高潮作准备时，把实际触发、关联选择和后来释放的条件按章序对应起来。

313986｜{"id":"C01495","source":"7.5_情感铺垫","target":"45.1_伏笔","type":"转化","condition":"情感铺垫类似伏笔；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「7.5_情感铺垫」经「转化」影响「45.1_伏笔」（条件：情感铺垫类似伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

314201｜{"id":"C01496","source":"7.5_情感铺垫","target":"45.1_伏笔埋设","type":"嵌套链","condition":"情感需要被铺垫","priority":1,"effect":"情感铺垫是伏笔的一种形式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前情感铺垫确包含已选伏笔时，在实际章场标出可回查的情绪线索和后续兑现事件。

314400｜{"id":"C01497","source":"7.5_情感铺垫","target":"155.1_情绪缓冲","type":"触发链","condition":"铺垫需要缓冲","priority":2,"effect":"情感铺垫需要缓冲空间","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用缓冲承接铺垫或前序高压时，以真实章序、当前人物反应和读者消化任务核对安排的位置。

314599｜{"id":"C01498","source":"7.5_情感铺垫","target":"44.7_高潮前奏","type":"转化","condition":"情感铺垫是高潮前奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用情感铺垫作为高潮前奏时，依具体事件和角色已有变化说明先呈现何种压力及后来怎样回应。

314814｜{"id":"C01499","source":"7.6_情感释放","target":"155.1_情绪缓冲","type":"触发链","condition":"情感释放后需要缓冲","priority":1,"effect":"情感释放后需要缓冲恢复","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已确定释放之后的读者缓冲时，以实际余波、角色反应和下段章场任务定位消化的位置。

315013｜{"id":"C01500","source":"7.6_情感释放","target":"4.1_弧光五阶段","type":"触发链","condition":"情感释放推动弧光","priority":1,"effect":"情感释放推动弧光向前发展","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】有实际情感释放推动既有弧光时，用前置经历、角色在场选择和后续可见行为核对变化节点。

315626｜{"id":"C01503","source":"7.6_情感释放","target":"155.1_缓冲","type":"约束","condition":"释放后需缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「7.6_情感释放」经「约束」影响「155.1_缓冲」（条件：释放后需缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

315841｜{"id":"C01504","source":"7.7_情感铺垫-释放距离","target":"62.1_章节节奏轮换","type":"触发链","condition":"距离影响节奏","priority":2,"effect":"情感铺垫-释放距离决定节奏","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已经设定铺垫与释放的距离时，用具体埋下的情绪、章序和兑现事件核对节奏变化。

316040｜{"id":"C01505","source":"7.7_铺垫释放距离","target":"155.1_缓冲","type":"约束","condition":"距离决定缓冲需求；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「7.7_铺垫释放距离」经「约束」影响「155.1_缓冲」（条件：距离决定缓冲需求）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

316255｜{"id":"C01506","source":"7.7_铺垫释放距离","target":"62.1_节奏轮换","type":"绑定","condition":"距离决定节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品采用由铺垫到释放调整章序时，将真实前置事件、累积压力与实际兑现对应到已有轮换。

316470｜{"id":"C01507","source":"7.8_情感弧光追踪","target":"4.1_弧光","type":"转化","condition":"情感弧光是弧光的一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据已选人物变化和具体章场，在现有弧光标出情感发生转变的触发、行动及后果。

316685｜{"id":"C01508","source":"7.8_情感弧光追踪","target":"4.1_弧光五阶段","type":"触发链","condition":"情感需要被追踪","priority":1,"effect":"情感弧光是弧光的内部证据","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作采用已确认的弧光节点时，用实有情感前后、关键决定和能观察到的行为保存内部变化证据。

318126｜{"id":"C01515","source":"7.9_情感密度控制","target":"62.1_章节节奏轮换","type":"触发链","condition":"情感密度影响节奏","priority":1,"effect":"情感密度是节奏控制的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品采用情感密度指导章序时，将实际高低情感节点、事件后果和章场切换对应到既定节奏方案。"""
