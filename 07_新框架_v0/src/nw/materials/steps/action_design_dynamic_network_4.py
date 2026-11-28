"""行动设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 意志、决策、两难及状态待核】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

318755｜{"id":"C01518","source":"70.1_坚韧","target":"72.4_审慎","type":"放大","condition":"坚韧保持冷静；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已设角色的坚韧影响本次审慎选择时，用当前压力、角色知道的事实和能做的行动核对其判断与后果。

319169｜{"id":"C01520","source":"70.2_坚定","target":"72.1_果断","type":"放大","condition":"坚定强化果断；且当前故事明确采用该静态关系","priority":1,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前已有明确目标且角色坚定时，用实际冲突、可得信息和可执行办法核对他如何及时作出选择。

319599｜{"id":"C01522","source":"70.3_软弱","target":"72.2_犹豫","type":"触发","condition":"软弱激活；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目角色确因当前软弱表现而迟疑时，用所处情境、实有选项和可查后果核对他的应对。

320244｜{"id":"C01525","source":"70.4_动摇","target":"72.2_犹豫","type":"触发","condition":"动摇激活；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知角色在本场动摇时，用不同实际解释、尚未确认的事实和真实选择核对其犹豫行为。

320889｜{"id":"C01528","source":"70.5_执着","target":"80.1_抗争","type":"驱动","condition":"执着驱动抗争；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「70.5_执着」经「驱动」影响「80.1_抗争」（条件：执着驱动抗争）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

321534｜{"id":"C01531","source":"70.7_忍耐","target":"145.4_动作","type":"触发链","condition":"忍耐状态","priority":2,"effect":"忍耐影响动作选择","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有本作认可的忍耐及真实行动限制时，写明角色此时可承受什么、选择何种具体动作及何时调整。

322163｜{"id":"C01534","source":"72.1_果断","target":"145.4_动作","type":"触发链","condition":"果断决策","priority":1,"effect":"果断导致快速动作","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色已经在具体时限内作出果断选择时，以实际对象、可做动作及后果核对迅速行动的表现。

322362｜{"id":"C01535","source":"72.1_果断","target":"145.4_动作","type":"转化","condition":"果断→动作；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将现有果断决定落实为明确动作、对象和可观察结果，保留当时信息与能力边界。

322577｜{"id":"C01536","source":"72.1_果断","target":"149.2_判断","type":"转化","condition":"果断=快速判断；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】人物已需快速判断时，依据实际证据、选项及后果核对何时作出决定、采用哪项应对。

322792｜{"id":"C01537","source":"72.2_犹豫","target":"149.1_权衡","type":"转化","condition":"犹豫=持续权衡；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在角色迟疑的已设事件中，对照尚需权衡的实际条件、可做选项和他停留的具体原因。

323007｜{"id":"C01538","source":"72.2_犹豫","target":"73.3_决策成本","type":"转化","condition":"犹豫增加决策成本；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】如果拖延已产生可查成本，按角色真实用时、错过的机会和仍可作出的选择核对实际决策成本。

323222｜{"id":"C01539","source":"72.3_冲动","target":"145.4_动作","type":"触发链","condition":"冲动状态","priority":1,"effect":"冲动导致直接动作","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前角色已因冲动采取行动时，用直接触发、他当时所知和真实可做动作核对实际后果。

323421｜{"id":"C01540","source":"72.3_冲动决策","target":"145.4_动作","type":"转化","condition":"冲动→行动；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已选冲动决策时，在本轮记录具体动机、未完成的实际权衡及立即实施的动作。

324066｜{"id":"C01543","source":"72.4_审慎决策","target":"149.1_权衡","type":"转化","condition":"审慎=充分权衡；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前已有审慎选择时，根据当事人确知的依据、不同可行方案、所得与损失说明取舍。

324281｜{"id":"C01544","source":"72.4_审慎决策","target":"73.3_决策成本","type":"嵌套","condition":"审慎消耗时间精力；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】考量审慎方案的实际负担时，用明确时限、需要的信息及人物投入核对等待和继续行动的成本。

324496｜{"id":"C01545","source":"72.5_冒险","target":"43.6_时间压力","type":"触发链","condition":"时间压力下","priority":2,"effect":"冒险决策增加时间压力","direction":"双向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】若本次冒险确使本作既有时限收紧，用实际剩余时段、所选动作和出现的风险核对可行应对。

324910｜{"id":"C01547","source":"72.5_冒险决策","target":"72.3_冲动","type":"转化","condition":"冒险可能源于冲动；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前已确认冒险由冲动引出时，用此前所知、真实触发和可做选择核对角色为何采取该动作。

325125｜{"id":"C01548","source":"72.6_保守决策","target":"73.3_决策成本","type":"转化","condition":"保守=低成本；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色采用保守办法时，按实际可行方案分别核对即时成本、仍要承担的风险或放弃的收益。

325340｜{"id":"C01549","source":"72.6_保守决策","target":"72.4_审慎","type":"转化","condition":"保守是审慎的一种；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有审慎和保守的具体选择时，用角色真实权衡和选中低风险路径的依据核对两者作用。

325555｜{"id":"C01550","source":"73.1_决策依据","target":"149.1_权衡","type":"嵌套链","condition":"依据决定权衡","priority":1,"effect":"决策依据决定权衡方式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】依据当前角色确实掌握的依据，明确他实际比较哪几个选项、如何赋予分量及所选后果。

325754｜{"id":"C01551","source":"73.1_决策依据","target":"149.1_权衡","type":"转化","condition":"依据决定权衡；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】使用已设目的、所知信号和可证约束核对角色如何权衡，注明对应的实际选择。

325969｜{"id":"C01552","source":"73.1_决策依据","target":"2.7_角色价值","type":"嵌套","condition":"价值决定依据；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色已有明确价值排序时，说明它如何影响这次决定采用的真实证据、取舍和行动。

326184｜{"id":"C01553","source":"73.2_决策时机","target":"77.1_时间紧迫","type":"转化","condition":"紧迫影响时机；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前任务已设真正时限时，以剩余时间、可得依据和到期后果确定角色能采取决定的时机。

326399｜{"id":"C01554","source":"73.2_决策时机","target":"72.1_果断","type":"转化","condition":"果断影响时机；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作需要表现果断影响时机时，用已知证据、实际行动窗口和角色所选做法核对决定的具体时点。

327474｜{"id":"C01559","source":"73.6_责任冲突","target":"74.5_责任","type":"冲突","condition":"多责任不可兼容；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色有两项不能兼顾的责任时，以已设承诺对象、各项行动条件和不可兼得的实际后果核对选择。

327689｜{"id":"C01560","source":"73.6_责任冲突","target":"76.1_道德困境","type":"转化","condition":"责任冲突是道德困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已明确具体责任冲突时，把人物能做的选项、要承担的损失和哪项责任受影响写进本次候选。

327904｜{"id":"C01561","source":"74.1_是非","target":"76.1_道德困境","type":"冲突","condition":"对错不可兼得；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已有无法兼顾的是非判据时，用实有角色、可做选择及各自后果写明其实际两难。

328119｜{"id":"C01562","source":"74.1_是非","target":"76.1_道德困境","type":"触发链","condition":"是非判断产生困境","priority":1,"effect":"是非判断产生道德困境","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当该人物依据已知原则得出相冲突的判断时，在实际情节中逐项核对哪些选择可行及其代价。

328318｜{"id":"C01563","source":"74.1_是非","target":"73.1_决策依据","type":"嵌套","condition":"是非是决策维度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前人物已采用相应是非原则时，把实际事实、价值取舍及已有选项对应到本次决策依据。

328533｜{"id":"C01564","source":"74.1_是非","target":"75.1_利己","type":"冲突","condition":"是非与利益冲突；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】既有价值标准与人物自身实际利益发生冲突时，给出角色可做行为及其会放弃或保有的项目结果。

328748｜{"id":"C01565","source":"74.1_是非","target":"75.2_利他","type":"冲突","condition":"是非与利他冲突；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有助人选择与人物的是非判断不同向时，依实际受影响者、当时所知和两项代价核对选择。

329608｜{"id":"C01569","source":"74.3_正义","target":"80.1_抗争","type":"驱动","condition":"正义驱动抗争；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「74.3_正义」经「驱动」影响「80.1_抗争」（条件：正义驱动抗争）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

330038｜{"id":"C01571","source":"74.4_公平","target":"76.1_道德困境","type":"转化","condition":"公平冲突是困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品以公平冲突构成两难时，对照具体分配方式、各方所受影响和人物可做选择核对代价。

330667｜{"id":"C01574","source":"74.5_责任","target":"76.1_道德困境","type":"触发","condition":"责任冲突是困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前角色实际不能兼顾多个已定责任时，根据可做选项和受影响人核对本次道德取舍。

330882｜{"id":"C01575","source":"75.1_利己","target":"73.1_决策依据","type":"嵌套链","condition":"利己是决策依据","priority":1,"effect":"利己是决策依据之一","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前决定已经将个人利益作为一项依据时，用真实收益、风险和其他价值核对角色如何作出选择。

331081｜{"id":"C01576","source":"75.1_利己","target":"73.1_决策依据","type":"约束","condition":"利己优先；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知某人物在本情境优先考虑自己的利益时，用实际选项、所获和所失确认决定依据及后果。

331296｜{"id":"C01577","source":"75.1_利己","target":"43.1_资源争夺","type":"驱动","condition":"利己驱动争夺；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有个人利益确实推动角色争夺项目内资源时，按真实需求、具体对手和可做行动核对当前做法。

331511｜{"id":"C01578","source":"75.1_利己","target":"68.7_自利偏误","type":"放大","condition":"自利偏误强化利己；且当前故事明确采用该静态关系","priority":3,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已设自利偏误时，以实际得失、角色对事实的理解和可查行动核对其为何优先选择自身利益。

331726｜{"id":"C01579","source":"75.2_利他","target":"73.1_决策依据","type":"嵌套链","condition":"利他是决策依据","priority":1,"effect":"利他是决策依据之一","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当本次选择已把他人实际利益纳入判断时，用可执行的办法及所需承担代价核对是否采用。

331925｜{"id":"C01580","source":"75.2_利他","target":"74.1_是非","type":"约束","condition":"利他优先；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品设角色在当前事件优先顾及他人时，依实际受益者、角色已定原则和选择结果核对是非判断。

332140｜{"id":"C01581","source":"75.2_利他","target":"86.1_合作","type":"驱动","condition":"利他驱动合作；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有利他选择促使双方合作时，用具体帮助对象、双方接受条件与可执行分工核对行为。

332570｜{"id":"C01583","source":"75.3_功利","target":"73.1_决策依据","type":"约束","condition":"功利优先；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已设当前决定考虑整体结果时，用已知各方得失、实际选择及限度说明角色采取的做法。

332785｜{"id":"C01584","source":"75.3_功利","target":"43.1_资源争夺","type":"驱动","condition":"功利驱动争夺；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色确因既定利益权衡参与资源争夺时，以实际资源、行动条件、对手与成本核对可选应对。

336209｜{"id":"C01600","source":"76.8_道德悖论","target":"76.1_道德困境","type":"转化","condition":"悖论是困境一种；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已设某一悖论使人物面对实际两难时，用已知事实、可行做法及后果核对当前选择。

337284｜{"id":"C01605","source":"77.1_时间紧迫","target":"72.5_冒险决策","type":"触发","condition":"紧迫感推动冒险；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前紧迫时限确推动一次冒险选择时，以实有时间、风险、可用替代与实际决定核对角色行为。

337499｜{"id":"C01606","source":"77.1_时间紧迫","target":"73.2_决策时机","type":"转化","condition":"紧迫加速决策；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】人物面临明确的到期点时，用剩余时段和可得依据确定本场作决定的时机及逾期结果。

338144｜{"id":"C01609","source":"77.1_紧迫","target":"72.5_冒险","type":"触发链","condition":"紧迫驱动冒险","priority":1,"effect":"紧迫驱动冒险决策","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有迫近期限时，在候选比较实际冒险、仍可实施的其他办法及各自能保留的时间。

338558｜{"id":"C01611","source":"77.2_时间从容","target":"72.4_审慎决策","type":"放大","condition":"从容允许审慎；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目确给角色足够时间审慎决定时，用实有时段、可查信息和各方案结果核对他可以采取的具体动作。

343041｜{"id":"C01632","source":"8.1_受伤","target":"70.7_忍耐","type":"触发","condition":"带伤行动；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_受伤」经「触发」影响「70.7_忍耐」（条件：带伤行动）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

343256｜{"id":"C01633","source":"8.1_受伤","target":"86.2_竞争弱势","type":"嵌套","condition":"冲突场景；且当前故事明确采用该静态关系","priority":3,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_受伤」经「嵌套」影响「86.2_竞争弱势」（条件：冲突场景）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

343471｜{"id":"C01634","source":"8.1_疲惫","target":"145.4_动作迟缓","type":"转化","condition":"≥10小时；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疲惫」经「转化」影响「145.4_动作迟缓」（条件：≥10小时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

343901｜{"id":"C01636","source":"8.1_疲惫","target":"70.3_软弱","type":"放大","condition":"加情绪低落；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疲惫」经「放大」影响「70.3_软弱」（条件：加情绪低落）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

344116｜{"id":"C01637","source":"8.1_疲惫","target":"72.4_审慎削弱","type":"抑制","condition":"持续；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，降低终点状态的强度或可见性。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疲惫」经「抑制」影响「72.4_审慎削弱」（条件：持续）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

344331｜{"id":"C01638","source":"8.1_疲惫","target":"77.1_时间紧迫","type":"触发","condition":"有截止时限；且当前故事明确采用该静态关系","priority":3,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疲惫」经「触发」影响「77.1_时间紧迫」（条件：有截止时限）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

344761｜{"id":"C01640","source":"8.1_疾病","target":"70.3_软弱","type":"放大","condition":"疾病削弱意志；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疾病」经「放大」影响「70.3_软弱」（条件：疾病削弱意志）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

344976｜{"id":"C01641","source":"8.1_疾病","target":"72.2_犹豫","type":"触发","condition":"疾病影响判断；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疾病」经「触发」影响「72.2_犹豫」（条件：疾病影响判断）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

345390｜{"id":"C01643","source":"8.1_身体状态_饥饿","target":"24.1_资源类型_食物","type":"转化链","condition":"饥饿状态","priority":1,"effect":"食物被识别为高优先级生存资源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「转化链」影响「24.1_资源类型_食物」（条件：饥饿状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

345589｜{"id":"C01644","source":"8.1_身体状态_饥饿","target":"3.5_角色冲动","type":"触发链","condition":"饥饿持续≥6小时","priority":1,"effect":"求生本能被激活，决策加速，行为冲动倾向增强","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「触发链」影响「3.5_角色冲动」（条件：饥饿持续≥6小时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

345987｜{"id":"C01646","source":"8.1_身体状态_饥饿","target":"72.3_决策类型_冲动","type":"触发链","condition":"饥饿持续≥12小时且无其他获取途径","priority":1,"effect":"冲动决策替代审慎决策，行动先于思考","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「触发链」影响「72.3_决策类型_冲动」（条件：饥饿持续≥12小时且无其他获取途径）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

346186｜{"id":"C01647","source":"8.1_身体状态_饥饿","target":"74.1_是非","type":"冲突链","condition":"饥饿持续≥6小时且有机会获取食物","priority":1,"effect":"道德判断被挑战，是非观在生存压力下动摇","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「冲突链」影响「74.1_是非」（条件：饥饿持续≥6小时且有机会获取食物）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

347181｜{"id":"C01652","source":"8.1_身体状态_饥饿","target":"68.1_确认偏误","type":"放大链","condition":"饥饿状态看到他人成功获取食物的案例","priority":2,"effect":"冒险意愿被放大，失败风险被低估","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「放大链」影响「68.1_确认偏误」（条件：饥饿状态看到他人成功获取食物的案例）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

347977｜{"id":"C01656","source":"8.1_饥饿","target":"24.1_食物资源","type":"转化","condition":"饥饿状态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「转化」影响「24.1_食物资源」（条件：饥饿状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

348192｜{"id":"C01657","source":"8.1_饥饿","target":"3.5_冲动","type":"触发","condition":"饥饿≥3级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「触发」影响「3.5_冲动」（条件：饥饿≥3级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

348837｜{"id":"C01660","source":"8.1_饥饿","target":"72.3_冲动决策","type":"冲突","condition":"无其他途径；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「冲突」影响「72.3_冲动决策」（条件：无其他途径）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

349052｜{"id":"C01661","source":"8.1_饥饿","target":"74.1_是非","type":"冲突","condition":"有获取机会；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「冲突」影响「74.1_是非」（条件：有获取机会）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

349697｜{"id":"C01664","source":"8.1_饥饿","target":"68.1_确认偏误","type":"放大","condition":"看到他人成功；且当前故事明确采用该静态关系","priority":3,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「放大」影响「68.1_确认偏误」（条件：看到他人成功）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

350127｜{"id":"C01666","source":"8.2_亢奋","target":"72.1_果断","type":"放大","condition":"亢奋状态；且当前故事明确采用该静态关系","priority":1,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_亢奋」经「放大」影响「72.1_果断」（条件：亢奋状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

350342｜{"id":"C01667","source":"8.2_亢奋","target":"72.5_冒险决策","type":"放大","condition":"亢奋增加冒险；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_亢奋」经「放大」影响「72.5_冒险决策」（条件：亢奋增加冒险）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

350987｜{"id":"C01670","source":"8.2_恐惧","target":"83.5_逃避","type":"触发","condition":"≥4级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_恐惧」经「触发」影响「83.5_逃避」（条件：≥4级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

351202｜{"id":"C01671","source":"8.2_恐惧","target":"68.3_悲观偏误","type":"放大","condition":"恐惧状态；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_恐惧」经「放大」影响「68.3_悲观偏误」（条件：恐惧状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

351417｜{"id":"C01672","source":"8.2_恐惧","target":"80.1_抗争","type":"冲突","condition":"恐惧+执念；且当前故事明确采用该静态关系","priority":3,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_恐惧」经「冲突」影响「80.1_抗争」（条件：恐惧+执念）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

351632｜{"id":"C01673","source":"8.2_愤怒","target":"3.5_冲动","type":"触发","condition":"≥3级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_愤怒」经「触发」影响「3.5_冲动」（条件：≥3级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

352062｜{"id":"C01675","source":"8.2_愤怒","target":"72.5_冒险决策","type":"触发","condition":"加机会出现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_愤怒」经「触发」影响「72.5_冒险决策」（条件：加机会出现）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

352277｜{"id":"C01676","source":"8.2_抑郁","target":"70.3_软弱","type":"触发","condition":"抑郁状态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_抑郁」经「触发」影响「70.3_软弱」（条件：抑郁状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

352707｜{"id":"C01678","source":"8.2_抑郁","target":"72.2_犹豫","type":"放大","condition":"抑郁削弱决断；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_抑郁」经「放大」影响「72.2_犹豫」（条件：抑郁削弱决断）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

352922｜{"id":"C01679","source":"8.2_焦虑","target":"68.1_确认偏误","type":"放大","condition":"接收信息时；且当前故事明确采用该静态关系","priority":1,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_焦虑」经「放大」影响「68.1_确认偏误」（条件：接收信息时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

353352｜{"id":"C01681","source":"8.2_焦虑","target":"72.2_犹豫","type":"触发","condition":"≥3级；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_焦虑」经「触发」影响「72.2_犹豫」（条件：≥3级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

353782｜{"id":"C01683","source":"8.2_精神状态_焦虑","target":"68.1_确认偏误","type":"放大链","condition":"焦虑状态","priority":1,"effect":"焦虑放大确认偏误，角色只注意支持自己担忧的信息","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_精神状态_焦虑」经「放大链」影响「68.1_确认偏误」（条件：焦虑状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

353981｜{"id":"C01684","source":"8.2_精神状态_焦虑","target":"68.3_悲观偏误","type":"放大链","condition":"焦虑状态且处于不确定情境","priority":1,"effect":"焦虑放大悲观偏误，高估坏结果的可能性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_精神状态_焦虑」经「放大链」影响「68.3_悲观偏误」（条件：焦虑状态且处于不确定情境）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

354578｜{"id":"C01687","source":"8.2_精神状态_焦虑","target":"72.2_决策类型_犹豫","type":"触发链","condition":"焦虑状态且决策重要性高","priority":2,"effect":"焦虑导致决策犹豫，无法做出明确选择","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_精神状态_焦虑」经「触发链」影响「72.2_决策类型_犹豫」（条件：焦虑状态且决策重要性高）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

354976｜{"id":"C01689","source":"8.3_能量充裕","target":"72.1_果断","type":"放大","condition":"能量充裕；且当前故事明确采用该静态关系","priority":1,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量充裕」经「放大」影响「72.1_果断」（条件：能量充裕）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

355191｜{"id":"C01690","source":"8.3_能量充裕","target":"10.3_技巧","type":"放大","condition":"能量充裕提升技巧；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量充裕」经「放大」影响「10.3_技巧」（条件：能量充裕提升技巧）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

355621｜{"id":"C01692","source":"8.3_能量匮乏","target":"72.5_冒险","type":"触发","condition":"能量匮乏+冲突；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量匮乏」经「触发」影响「72.5_冒险」（条件：能量匮乏+冲突）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。"""
