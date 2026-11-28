"""场景设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 配角传递信息与遗物的披露范围】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

1880｜{"id":"C00009","source":"1.3_次要配角","target":"121.11_信息承载","type":"转化","condition":"出场时释放信息；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选次要配角出场且承担信息传递时，以本场其真实所知和获准披露的具体事实核对其他人物谁能得知。

2740｜{"id":"C00013","source":"1.5_缺席者","target":"28.5_道具记忆","type":"转化","condition":"通过遗物影响；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前确有遗物承载缺席者记忆时，根据实际对象、选定动作和视角边界安排可见记忆线索及本场人物反应。

【动态网络原文 · 叙述人称、时间窗口和注意边界】

10246｜{"id":"C00049","source":"109.1_叙述者类型","target":"58.1_第一人称","type":"触发链","condition":"类型决定人称","priority":1,"effect":"叙述者类型决定人称","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者已选第一人称时，按本场实际参与者确定谁在叙述、能感知什么和可以披露的事实。人称随已确认的叙述方式使用。

25317｜{"id":"C00122","source":"12.5_浓度时间变化","target":"77.1_时间紧迫","type":"触发","condition":"浓度变化影响时间感知；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件受浓度时窗影响时，把剩余时间、错过的实际机会及角色获得时限线索的方式落实到本场进入状态和冲突。

27148｜{"id":"C00131","source":"12.8_感知范围","target":"67.2_注意","type":"转化","condition":"范围决定注意；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依本场人物感知边界和注意目标限定 allowed_disclosure，说明哪个线索能被选中视角实际注意到。

27578｜{"id":"C00133","source":"12.8_能量感知范围","target":"67.2_注意","type":"触发链","condition":"感知范围决定注意","priority":2,"effect":"感知范围影响注意力分配","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场能量感知范围会改变注意力时，沿用实际观察者、对象与环境，在场景卡写清注意力从何处转到何处以及能够看到的迹象。

28386｜{"id":"C00137","source":"120.1_多视角必要性","target":"59.5_视角切换条件","type":"触发链","condition":"必要性决定切换条件","priority":1,"effect":"多视角必要性决定切换条件","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用多视角且剧情给出切换需要时，用既有章场分界选择接续观察者，核对他多获得的实际信息以及本场披露范围。

【动态网络原文 · 第三人称有限的实有知情范围】

54736｜{"id":"C00263","source":"142.2_第三人称有限未知","target":"59.8_信息差","type":"转化","condition":"第三人称=信息差；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已采用第三人称有限时，核对跟随人物与读者从已存在前文取得的不同信息，在 allowed_disclosure 明确本场能给出的线索。

【动态网络原文 · 任务、信息边界和实际时窗】

77514｜{"id":"C00371","source":"154.3_任务目标","target":"145.1_目标","type":"转化","condition":"任务=目标；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】承接本场已选任务和上游事件，把项目任务落实成场中可做的角色目标，核对进入状态、障碍和拟达结果。

79616｜{"id":"C00381","source":"155.2_共情铺垫","target":"65.2_不确定性","type":"转化","condition":"铺垫管理不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已有共情铺垫时，依实际人物处境和允许披露的事实安排读者先理解的选择及仍待解开的信息。

87985｜{"id":"C00422","source":"17.5_浓度时间变化","target":"77.1_时间紧迫","type":"触发","condition":"变化影响时间感知；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场任务确实依赖浓度变化窗口时，把所剩实际时间、可用机会和人物能知道时限的线索写入进入状态与冲突。

88200｜{"id":"C00423","source":"17.5_能量浓度时间变化","target":"77.1_时间感知_紧迫","type":"触发链","condition":"时间变化影响感知","priority":2,"effect":"浓度时间变化影响时间感知","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选事件因浓度周期使时间紧迫时，用人物能感知的信号体现接近的节点及会失去的机会，具体感知沿用已有视角。

90891｜{"id":"C00436","source":"18.4_潮汐减弱","target":"77.1_时间紧迫","type":"触发","condition":"潮汐减弱加剧紧迫；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前事件依赖的潮汐机会足以构成时限时，把剩余时间、人物可察觉的征象和失去的具体机会落实到本场。

【动态网络原文 · 道具与地理造成的实际空间条件】

126710｜{"id":"C00607","source":"29.2_道具与环境交互","target":"115.1_空间结构","type":"转化","condition":"交互影响空间感知；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已选道具改变空间感知时，依据作用条件、角色可见范围和实有场地确认通行方向、可感位置及障碍。

145237｜{"id":"C00696","source":"31.2_地理结构","target":"115.1_空间结构","type":"转化","condition":"地理影响空间感知；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】把已确认的地理、路径和可见范围落实成本场能到达、能看到的区域以及所选行动面对的空间阻碍。

【动态网络原文 · 章场分工、实际时限与叠加冲突】

187114｜{"id":"C00895","source":"41.3_起承转合","target":"48.1_起承转合","type":"转化","condition":"起承转合是章节结构；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前章已采用起承转合时，按已选事件及所处章内位置核对本场引入、发展、转折或收束的具体任务。

200849｜{"id":"C00960","source":"43.6_时间压力","target":"77.1_时间感知_紧迫","type":"触发链","condition":"时间压力产生紧迫感","priority":1,"effect":"时间压力产生紧迫感","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前事件已有明确的到期条件时，把剩余时间、可见的紧迫信号及过期的后果落实到本场条件。

203580｜{"id":"C00973","source":"43.9_冲突叠加","target":"44.8_高潮三层叠加","type":"共振","condition":"叠加是高潮；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场确已选冲突叠加为高潮时，按实有事件与动作将各重冲突落实为本场进入状态、选择及可感结果。

【动态网络原文 · 场间因果、节奏、视角、对抗及章场衔接】

220826｜{"id":"C01055","source":"46.10_场景与下一场景因果","target":"46.3_场景过渡","type":"转化","condition":"因果是过渡一种；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据上游选定事件和前场真实结果，在本场明确由哪个动作、信息或限制进入，并核对过渡条件。

221041｜{"id":"C01056","source":"46.10_场景与下一场景因果","target":"48.4_章尾钩子","type":"转化","condition":"因果是钩子；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有本场结果引出章尾钩子时，用可确认的前序后果和下一场真实问题安排结束边界。

221256｜{"id":"C01057","source":"46.10_场景与下一场景因果","target":"122.5_跨章连续性","type":"转化","condition":"因果影响连续性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】跨章衔接已有确凿事实时，在当前场进入状态核对前章留下的事件、状态值及谁已知情。

221471｜{"id":"C01058","source":"46.10_场景与下一场景因果连接","target":"48.4_钩子设计","type":"嵌套链","condition":"因果连接是钩子","priority":1,"effect":"场景因果连接是钩子","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作选择以场间因果形成钩子时，核对前场实际改变、读者可辨疑问以及进入下场需要的条件。

221670｜{"id":"C01059","source":"46.11_场景结局不可逆","target":"122.1_剧情推进","type":"触发链","condition":"不可逆是推进","priority":1,"effect":"场景结局不可逆是剧情推进","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选场景结局确有不可逆影响时，写清终点后哪项机会或状态已经改变，以及下一场必须承接的具体事实。

221869｜{"id":"C01060","source":"46.11_场景结局不可逆","target":"122.1_推进","type":"转化","condition":"不可逆是推进；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已选动作带来不可逆结果时，以实际限制、关系或信息变化核对推进和计划结果。

222299｜{"id":"C01062","source":"46.12_场景尾钩子","target":"48.4_章尾钩子","type":"转化","condition":"尾钩子是钩子；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场也是所选章尾且设置钩子时，以实际结果、仍可推进的疑问和后场任务确定尾部落点。

222514｜{"id":"C01063","source":"46.12_场景尾钩子","target":"48.4_钩子设计","type":"嵌套链","condition":"尾钩子是钩子","priority":1,"effect":"场景尾钩子是钩子","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有尾钩子服务既定章场时，核对本场真正完成的事项、读者看得到的未解问题与下场衔接点。

222713｜{"id":"C01064","source":"46.12_场景尾钩子","target":"65.2_不确定性","type":"转化","condition":"尾钩子制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场结束需要留有不确定性时，用已允许披露的事实和既有角色行动确定还未能排除的解释。

222928｜{"id":"C01065","source":"46.1_场景数量","target":"46.2_场景节奏","type":"约束","condition":"4场景决定节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目采用四场且当前覆盖整章时，用已定四场各自任务、事件强度和后效核对章内节奏。

223143｜{"id":"C01066","source":"46.1_场景数量","target":"46.2_场景节奏","type":"触发链","condition":"数量决定节奏","priority":1,"effect":"场景数量决定节奏","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】沿本作采用的实际场数，核对每场已有行动、信息量和结果怎样形成章内快慢，沿用上游已选场景。

223342｜{"id":"C01067","source":"46.1_场景数量","target":"46.3_场景过渡","type":"触发链","condition":"场景需要过渡","priority":1,"effect":"场景需要过渡","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对本次实际存在的相邻场景核对上一场已定结果、后场进入条件及足够的转场提示。

223541｜{"id":"C01068","source":"46.1_场景数量","target":"48.1_起承转合","type":"映射","condition":"4场景对应起承转合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，将起点状态映射为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选四场承接起承转合时，将这四场各自的实际目标、转折与收束对应既定章内职责。

223756｜{"id":"C01069","source":"46.1_场景数量","target":"122.1_剧情推进","type":"绑定","condition":"场景承载推进；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以本次已有场景和其上游事件为依据，逐场核对真正改变了信息、状态或所选行动的内容。

223971｜{"id":"C01070","source":"46.2_场景节奏","target":"62.2_场景内快慢交替","type":"触发链","condition":"节奏决定快慢","priority":1,"effect":"场景节奏决定快慢交替","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】场景使用快慢交替时，按当前已选动作链与实际事件强弱确定交替时点和重要结果。

224170｜{"id":"C01071","source":"46.2_场景节奏","target":"62.2_快慢交替","type":"转化","condition":"节奏决定快慢；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据当前章场既定节奏，给实有行动、反应和停顿安排顺序，核对加速和减速分别作用在哪些过程。

224385｜{"id":"C01072","source":"46.2_场景节奏","target":"44.1_爽点压抑","type":"嵌套","condition":"节奏影响爽点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已有压抑或释放任务时，将实际障碍、当事人的应对与场内快慢对应到所选事件。

224600｜{"id":"C01073","source":"46.2_场景节奏","target":"47.2_对抗回合","type":"嵌套","condition":"节奏包含对抗；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】上游对抗已经选定时，把实际行动、对方回应与后果按本场节奏安排到不同节拍。

224815｜{"id":"C01074","source":"46.3_场景过渡","target":"48.1_起承转合","type":"嵌套链","condition":"过渡是起承转合的一部分","priority":1,"effect":"场景过渡是起承转合的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用起承转合并有场间切换时，用前场结果、后场进入状态与章内任务核对实际过渡。

225014｜{"id":"C01075","source":"46.3_场景过渡","target":"59.7_场景内视角一致","type":"约束","condition":"过渡需视角一致；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】核对前后场时间、地点、可用视角及允许披露的事实，沿用每场已定观察者和转场边界。

225444｜{"id":"C01077","source":"46.4_场景视角","target":"120.1_多视角必要性","type":"转化","condition":"场景视角决定必要性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已确定使用多视角时，以本场需要交付的事实与既有章场分界核对承担观察的角色及切换必要性。

225659｜{"id":"C01078","source":"46.4_场景视角","target":"59.7_场景内视角一致","type":"触发链","condition":"场景视角需要一致","priority":1,"effect":"场景视角需要一致","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】按已定场景视角核对本场信息和事件表现，保留从开始到结束同一观察者所能知道的范围。

226073｜{"id":"C01080","source":"46.5_场景内部因果链","target":"145.1_目标","type":"嵌套","condition":"因果链包含目标；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前事件的因果链中，以实际角色的章场目标为前置，核对目标怎样产生或影响所选行动。

226288｜{"id":"C01081","source":"46.5_场景内部因果链","target":"145.1_目标","type":"嵌套链","condition":"因果链包含目标","priority":1,"effect":"场景因果链包含目标","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】场景已有明确目标时，用进入状态、物件或人物实有条件把目标与后续行为的成立依据相连。

226487｜{"id":"C01082","source":"46.5_场景内部因果链","target":"145.4_动作","type":"嵌套","condition":"因果链包含动作；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以当前确已选择的动作及实际目标为准，核对该动作在场景因果链中的触发、阻碍和可见影响。

226702｜{"id":"C01083","source":"46.5_场景内部因果链","target":"145.5_结果","type":"嵌套","condition":"因果链包含结果；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用本场实际动作、对方回应和可观察改变核对结果，注明后续场景会承接的事实。

227132｜{"id":"C01085","source":"46.6_场景情绪标记","target":"64.1_读者情绪","type":"转化","condition":"情绪标记影响读者；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「46.6_场景情绪标记」经「转化」影响「64.1_读者情绪」（条件：情绪标记影响读者）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

227347｜{"id":"C01086","source":"46.7_戏剧性温度","target":"64.1_读者情绪","type":"转化","condition":"温度影响读者情绪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「46.7_戏剧性温度」经「转化」影响「64.1_读者情绪」（条件：温度影响读者情绪）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

227562｜{"id":"C01087","source":"46.7_戏剧性温度","target":"62.2_快慢交替","type":"转化","condition":"温度影响节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实际场景强度已有安排时，把所选动作、回应和停顿对应到本场快慢，核对何处需要减压或加速。

228207｜{"id":"C01090","source":"46.9_场景内快慢交替","target":"62.2_快慢交替","type":"转化","condition":"快慢交替是场景节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】根据已定场景目的及实际行动，把快速发生的变化与较慢消化的部分分别安排到可见节拍。

228422｜{"id":"C01091","source":"47.1_对抗结构","target":"47.2_对抗回合","type":"触发链","condition":"结构决定回合","priority":1,"effect":"对抗结构决定回合","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场采用对抗结构时，以已选双方和动作核对每回合在场景中的进入条件、真实回应及变化。

228621｜{"id":"C01092","source":"47.1_对抗结构","target":"47.2_对抗回合","type":"转化","condition":"结构含回合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场景已有对抗过程时，按上游选定行动及角色反应核对回合次序和各回合需要保留的结果。

231599｜{"id":"C01106","source":"47.5_冲突锋利度","target":"47.1_对抗结构","type":"约束","condition":"锋利度是结构一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场的对抗已被选定时，按实际双方、场中出入条件和失败后果核对冲突的关键利害。

233303｜{"id":"C01114","source":"47.8_冲突叠加","target":"44.8_高潮三层叠加","type":"共振","condition":"叠加是高潮一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场采用叠加冲突形成高潮时，将上游已有各项冲突的实际动作、回应与关键结果落实在场景中。

233518｜{"id":"C01115","source":"48.13_章节连续性","target":"48.4_章尾钩子","type":"约束","condition":"连续性回应钩子；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当本场接续上一章钩子时，用已知问题、前章状态及本场选定行动核对答复如何开始。

233733｜{"id":"C01116","source":"48.13_章节连续性","target":"48.4_钩子设计","type":"触发链","condition":"连续性回应钩子","priority":1,"effect":"章节连续性回应钩子","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前场承担当初已留钩子的回应时，在进入状态保留具体前情及实际可回应的事件。

234147｜{"id":"C01118","source":"48.1_起承转合","target":"46.1_场景数量","type":"转化","condition":"起承转合对应场景；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用起承转合的章节中，根据实际任务核对哪些场承担各环节，沿用本章已选场数。

234362｜{"id":"C01119","source":"48.1_起承转合","target":"48.2_开篇规则","type":"触发链","condition":"起是开篇","priority":1,"effect":"起承转合的起是开篇","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本章开篇承担引入时，对照项目已定章序与所选事件，在首场明确人物当前目标、进入状态和主要阻碍。

234561｜{"id":"C01120","source":"48.1_起承转合","target":"48.2_开篇规则","type":"转化","condition":"起是开篇；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】开场需完成起的任务时，用真实触发、在场角色及可披露信息核对章初可见的具体目的。

234776｜{"id":"C01121","source":"48.1_起承转合","target":"48.3_结尾规则","type":"触发链","condition":"合是结尾","priority":1,"effect":"起承转合的合是结尾","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本章选定收束位置时，按已有最后事件与计划结果明确已完成的事项，以及后续章仍承接的事实。

234975｜{"id":"C01122","source":"48.1_起承转合","target":"48.3_结尾规则","type":"转化","condition":"合是结尾；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场承担结尾时，依据章内既有行动、意外或成果写明实际收束与所留下的下一任务。

235835｜{"id":"C01126","source":"48.3_结尾规则","target":"48.4_章尾钩子","type":"转化","condition":"结尾是钩子；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选结尾需要立章尾钩子时，依真实前置事件与本章结果确定哪一问题留给相邻章。

236050｜{"id":"C01127","source":"48.3_结尾规则","target":"48.4_钩子设计","type":"嵌套链","condition":"结尾是钩子","priority":1,"effect":"结尾是钩子","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目在某章结尾需要钩子时，把实际收束、可见疑问和下一场进入依据安排在既有章场分界。

248886｜{"id":"C01187","source":"52.1_视觉描写","target":"115.1_空间结构","type":"转化","condition":"视觉展示空间；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按上游选定场地、角色方位与可见范围核对实际空间的通行路线、障碍及观察边界。

250391｜{"id":"C01194","source":"52.6_五感规则","target":"48.1_起承转合","type":"约束","condition":"五感规则影响起承转合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前章已选感官线索时，在各场的实际作用里核对哪种感官帮助引入、推动、改变或收束，并沿用本场视角。

【动态网络原文 · 观察者、视角交接、场内节奏与情感任务】

259636｜{"id":"C01237","source":"58.1_第一人称","target":"142.1_第一人称未知","type":"绑定","condition":"第一人称制造未知；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用第一人称时，按选定叙述者的实际知识、进入状态与行动，明确本场能看见的事实和仍未知的问题。

260281｜{"id":"C01240","source":"58.3_第三人称有限","target":"59.1_主角POV","type":"转化","condition":"第三人称有限是主角POV；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已采用第三人称有限并选主角为观察者时，依据角色实际在场、视野与对事件的理解确定场景信息。

260496｜{"id":"C01241","source":"58.3_第三人称有限","target":"59.8_信息差","type":"转化","condition":"第三人称有限决定信息差；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】第三人称有限场景有已设信息差时，核对观察者亲历的事实、别人知道的内容及可披露顺序。

261356｜{"id":"C01245","source":"59.1_主角POV","target":"59.8_信息差","type":"转化","condition":"主角POV决定信息差；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场由主角观察时，用其已知事实、可接触信息和所在位置核对人物之间的信息差。

261571｜{"id":"C01246","source":"59.2_配角POV","target":"120.15_配角POV前置条件","type":"约束","condition":"配角POV需前置条件；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已安排配角视角时，按实际章场和该角色的独立行动核对启用条件、可知信息及其能补充的内容。

261786｜{"id":"C01247","source":"59.2_配角POV","target":"121.17_配角视角限制","type":"约束","condition":"配角POV有信息限制；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场使用配角视角时，以该配角实际在场的位置、行动与所知范围判断哪些内容可以在场中呈现。

262216｜{"id":"C01249","source":"59.3_配角POV前500字","target":"59.2_配角POV","type":"约束","condition":"是配角POV规则；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已决定采用配角前五百字限制时，核对开场承担的视角任务、当前观察者及真实可交付信息。

262431｜{"id":"C01250","source":"59.5_视角切换条件","target":"120.4_视角切换时机","type":"转化","condition":"条件决定时机；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已经采用多视角时，依实际章场边界、当事人行动和信息变化核对所选视角切换时机。

262646｜{"id":"C01251","source":"59.5_视角切换条件","target":"120.2_多视角规则","type":"嵌套","condition":"条件是规则一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用作品已定多视角规则核对某次切换的前置条件、章节位置和观察任务。

263291｜{"id":"C01254","source":"59.7_场景内视角一致","target":"46.3_场景过渡","type":"约束","condition":"场景内视角一致决定过渡；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对本场及相邻场的时序和可披露内容，以各场已定观察者核对过渡，在实有章场边界承接上游结果。

263506｜{"id":"C01255","source":"59.7_场景内视角一致","target":"120.2_多视角规则","type":"约束","condition":"是规则一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品采用多视角时，核对每个实际场景内部的观察者、所知信息及已有场间切换依据。

281157｜{"id":"C01340","source":"60.1_远景镜头","target":"46.1_场景建立","type":"绑定","condition":"远景建立场景；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已选远景建立实际环境时，用作者已定地点、观察位置、人物入口和空间边界核对开场安排。

287328｜{"id":"C01369","source":"62.2_场景内快慢交替","target":"46.2_场景节奏","type":"转化","condition":"快慢交替是场景节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已有场内快慢安排时，按实际动作、可见后果与停顿拟定先后并和章场目标相连。

288172｜{"id":"C01373","source":"62.3_空隙","target":"46.3_场景过渡","type":"转化","condition":"空隙是过渡一种；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前相邻场景之间有已确定的时间或行动空隙时，以实际前场结果及后场进入条件安排出现位置和衔接。

288387｜{"id":"C01374","source":"62.3_空隙","target":"155.1_缓冲","type":"转化","condition":"空隙是缓冲；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「62.3_空隙」经「转化」影响「155.1_缓冲」（条件：空隙是缓冲）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

288602｜{"id":"C01375","source":"62.5_情绪承接","target":"48.13_章节连续性","type":"转化","condition":"承接是连续性一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场承接前章情绪时，使用前章实际发生的动作、关系前值与已有反应核对本场进入状态。

296246｜{"id":"C01411","source":"65.4_读者阅读速度","target":"62.2_快慢交替","type":"转化","condition":"阅读速度=节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定事件拟交替快慢时，按已用场景节拍、停顿及具体行动变化安排快段与慢段的位置。

317298｜{"id":"C01511","source":"7.9_情感密度控制","target":"61.1_重章","type":"绑定","condition":"重章密度高；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场承担已定重章的情感推进时，用所选事件的主要情绪触发、真实选择及结果核对本场作用。

317513｜{"id":"C01512","source":"7.9_情感密度控制","target":"61.1_重章","type":"触发链","condition":"重章需要高情感密度","priority":1,"effect":"重章情感密度高","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前重章已给本场高情感密度任务时，依据实际动作及可见反应核对哪些事件应在本场发生。

317712｜{"id":"C01513","source":"7.9_情感密度控制","target":"61.3_轻章","type":"绑定","condition":"轻章密度低；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已作为轻章的一部分时，用前场确有的余波、当前人物反应与所选任务核对可适当放缓的位置。

317927｜{"id":"C01514","source":"7.9_情感密度控制","target":"61.3_轻章","type":"触发链","condition":"轻章需要低情感密度","priority":1,"effect":"轻章情感密度低","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已选轻章承接事件时，从现有场景对象与人物感受确定实际留白、停顿或消化的节拍。

【动态网络原文 · 实际时间跨度、空间变化及待核状态】

340692｜{"id":"C01621","source":"78.2_时间跳跃","target":"79.3_时间密度","type":"转化","condition":"跳跃决定密度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已有时间跳跃时，从实有起止时点、事件密度和进入状态核对被略去或展开的过程。

346783｜{"id":"C01650","source":"8.1_身体状态_饥饿","target":"33.1_阶层划分","type":"嵌套链","condition":"饥饿状态","priority":2,"effect":"饥饿与阶层身份关联，底层角色更容易饥饿","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「嵌套链」影响「33.1_阶层划分」（条件：饥饿状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

347579｜{"id":"C01654","source":"8.1_身体状态_饥饿","target":"77.1_时间感知_紧迫","type":"触发链","condition":"饥饿状态","priority":2,"effect":"时间感知扭曲，寻找食物的紧迫感增强","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「触发链」影响「77.1_时间感知_紧迫」（条件：饥饿状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

349482｜{"id":"C01663","source":"8.1_饥饿","target":"33.1_阶层感知","type":"嵌套","condition":"反复发生；且当前故事明确采用该静态关系","priority":3,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「嵌套」影响「33.1_阶层感知」（条件：反复发生）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

354777｜{"id":"C01688","source":"8.2_精神状态_焦虑","target":"77.1_时间感知_紧迫","type":"触发链","condition":"焦虑状态且有时间限制的任务","priority":2,"effect":"焦虑放大时间紧迫感，时间感知扭曲","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_精神状态_焦虑」经「触发链」影响「77.1_时间感知_紧迫」（条件：焦虑状态且有时间限制的任务）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

366370｜{"id":"C01743","source":"83.3_改造","target":"115.1_空间结构","type":"转化","condition":"改造改变空间；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场选用改造动作时，用实际物件或地形前后差异核对本场路线、障碍及可视边界如何改变。"""
