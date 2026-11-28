"""剧情设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 主角弧光、开篇共鸣与未揭历史】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

805｜{"id":"C00004","source":"1.1_主角","target":"4.1_弧光","type":"演化","condition":"全书主线；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】把项目已明确采用的主角弧光连到实际事件、决定与后果，安排哪些节点有可见变化以及后续怎样承接。

1020｜{"id":"C00005","source":"1.1_主角","target":"119.1_共鸣点","type":"约束","condition":"开篇建立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有开篇共鸣点时，把主角实际经历、困境或选择落实到选定事件，说明可被读者看见的依据。

2955｜{"id":"C00014","source":"1.5_缺席者","target":"32.7_未写明的历史","type":"绑定","condition":"关联历史；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选缺席者与未写明历史确有关系时，用可见线索记录哪里提及、谁能得知、哪些事实仍按原计划保留。

3170｜{"id":"C00015","source":"1.5_缺席者","target":"45.1_伏笔","type":"嵌套","condition":"伏笔来源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「1.5_缺席者」经「嵌套」影响「45.1_伏笔」（条件：伏笔来源）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

【动态网络原文 · 能力代价、主题、开篇与读者计划】

10031｜{"id":"C00048","source":"10.5_力量公式","target":"44.3_爽点-代价","type":"共振","condition":"公式变化伴随代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件用力量改变带来爽点时，把公式所支持的实际力量变化、作出的选择和承担的代价连进事件因果，保留对下一次选择的影响。

11468｜{"id":"C00055","source":"11.1_游离态","target":"83.1_探索","type":"转化","condition":"游离态决定探索方向；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】探索需求已有依据时，用游离态分布、可感知的线索和实际进入条件支持候选地点与探索方向，给相应事件保留阻碍。

14961｜{"id":"C00072","source":"111.1_核心象征物","target":"28.6_道具象征化","type":"触发链","condition":"道具可成为象征","priority":1,"effect":"道具成为核心象征物","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已选道具承载核心象征时，沿其已有归属和生命史安排何时出现、经历什么使用或变化，以及这些事件怎样赋予物件含义。

15160｜{"id":"C00073","source":"111.1_核心象征物","target":"63.1_核心主题","type":"触发链","condition":"象征连接主题","priority":1,"effect":"象征连接主题","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以作者已定主题和核心象征物为前置，把物件何时复现、发生什么变化及人物怎样对待它对应实际事件，让主题联系可回查。

15359｜{"id":"C00074","source":"112.1_开篇设计","target":"48.2_开篇规则","type":"嵌套链","condition":"开篇设计是规则","priority":1,"effect":"开篇设计是开篇规则的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「112.1_开篇设计」经「嵌套链」影响「48.2_开篇规则」（条件：开篇设计是规则）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

15558｜{"id":"C00075","source":"112.5_收尾设计","target":"130_核心悬念","type":"触发链","condition":"收尾解决悬念","priority":1,"effect":"收尾解决核心悬念","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「112.5_收尾设计」经「触发链」影响「130_核心悬念」（条件：收尾解决悬念）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

15757｜{"id":"C00076","source":"113.1_叙事顺序","target":"45.1_伏笔埋设","type":"嵌套链","condition":"倒叙是伏笔","priority":2,"effect":"倒叙是伏笔的一种","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选用倒叙埋设伏笔时，在 promise_plan 记下倒叙呈现的具体线索、其故事时点及后续揭示位置，按已定章场视角核对可见信息。

16171｜{"id":"C00078","source":"114.1_类型必备元素","target":"123.4_黄金三章","type":"绑定","condition":"必备元素在开篇建立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用黄金三章安排时，把前置已经选定的类型要素落实到实际开篇事件、人物选择和读者第一次能看到的位置。

16601｜{"id":"C00080","source":"114.2_类型惯例","target":"123.4_黄金三章","type":"绑定","condition":"惯例在开篇建立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用的惯例需要在开篇建立时，用现有章任务核对哪一章、哪一事件能展示所选惯例及其与人物目标的联系。

16816｜{"id":"C00081","source":"114.3_类型惯例突破","target":"45.11_反转","type":"转化","condition":"突破=反转；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作选用反转来突破惯例时，把实际前置信息、读者可形成的预期和所选揭示对应到已有事件节点。

17246｜{"id":"C00083","source":"114.4_类型读者预期","target":"65.5_读者预期","type":"转化","condition":"类型预期=读者预期；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在 reader_plan 对照本作确有的类型承诺和人物事件，安排读者何时形成、改变或兑现所选预期，并给出可见依据。

18305｜{"id":"C00088","source":"116.1_遗漏信息","target":"65.2_读者不确定性管理","type":"触发链","condition":"遗漏制造不确定性","priority":1,"effect":"遗漏信息制造不确定性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「116.1_遗漏信息」经「触发链」影响「65.2_读者不确定性管理」（条件：遗漏制造不确定性）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

18504｜{"id":"C00089","source":"117.1_错位","target":"45.11_反转类型","type":"触发链","condition":"错位是反转","priority":1,"effect":"错位是反转的一种","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已选择认知错位形成反转时，串起人物原先的理解、实际看到的依据和后续揭示，让反转可以回查前文。

18902｜{"id":"C00091","source":"119.1_共鸣点","target":"123.4_黄金三章","type":"绑定","condition":"共鸣点在开篇建立；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选开篇要求建立共鸣时，在实际人物处境、事件选择和后果中安排第一个可见触发，并在 reader_plan 记下章场位置。

19117｜{"id":"C00092","source":"119.1_共鸣点","target":"65.1_代入感","type":"转化","condition":"共鸣点→代入感；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用现有人物处境和所选行动解释读者如何理解其选择，在 reader_plan 记下拟形成代入的具体线索。

19332｜{"id":"C00093","source":"119.1_共鸣点","target":"65.1_读者代入感","type":"触发链","condition":"共鸣影响代入感","priority":1,"effect":"共鸣点影响代入感","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】上游已选定共鸣点时，把读者接触该处境的时点、能先了解的事实及随后所见选择排进 reader_plan，留出可核对的表现。

19531｜{"id":"C00094","source":"119.2_爽点","target":"44.1_爽点压抑","type":"转化","condition":"爽点是压抑释放；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「119.2_爽点」经「转化」影响「44.1_爽点压抑」（条件：爽点是压抑释放）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

19746｜{"id":"C00095","source":"119.2_爽点","target":"123.4_黄金三章","type":"绑定","condition":"爽点在开篇建立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「119.2_爽点」经「绑定」影响「123.4_黄金三章」（条件：爽点在开篇建立）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

19961｜{"id":"C00096","source":"119.3_软弱点","target":"65.1_代入感","type":"转化","condition":"软弱点→代入感；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「119.3_软弱点」经「转化」影响「65.1_代入感」（条件：软弱点→代入感）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

20176｜{"id":"C00097","source":"119.3_软弱点","target":"123.4_黄金三章","type":"绑定","condition":"软弱点在开篇建立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「119.3_软弱点」经「绑定」影响「123.4_黄金三章」（条件：软弱点在开篇建立）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

24320｜{"id":"C00117","source":"12.4_浓度分布","target":"83.1_探索","type":"转化","condition":"浓度决定探索方向；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有探索任务和浓度分布时，在实际路线中核对所选地点、指引人物的可得线索与进入阻碍。

24913｜{"id":"C00120","source":"12.4_能量浓度分布","target":"83.1_探索","type":"触发链","condition":"浓度决定探索方向","priority":2,"effect":"浓度决定探索方向","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以实际能量浓度、角色可探查的范围和探索目标说明候选路线为何改变，并在具体事件保留所选方向与后续障碍。

28784｜{"id":"C00139","source":"122.1_剧情推进","target":"48.1_起承转合","type":"嵌套链","condition":"推进是起承转合","priority":1,"effect":"剧情推进是起承转合的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】采用起承转合结构的当前范围内，把剧情推进落实到实际事件、人物选择与后果，记明当前环节怎样承上启下。

28983｜{"id":"C00140","source":"123.10_名场面","target":"44.8_高潮三层叠加","type":"转化","condition":"名场面=高潮；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有名场面承担高潮时，用实际事件核对外部行动结果、人物的情感变化和主题落点，各层都对应可见的具体后果。

29198｜{"id":"C00141","source":"123.10_名场面","target":"64.1_读者情绪","type":"转化","condition":"名场面=情绪波形高点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「123.10_名场面」经「转化」影响「64.1_读者情绪」（条件：名场面=情绪波形高点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

29413｜{"id":"C00142","source":"123.11_争议点","target":"76.1_道德困境","type":"转化","condition":"争议点=道德困境；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有争议点并选用道德困境时，用现有人物立场、具体选择和各自损失安排两难事件，让前因支持双方理由。

29628｜{"id":"C00143","source":"123.11_争议点","target":"64.1_读者情绪","type":"转化","condition":"争议点=情绪波形；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「123.11_争议点」经「转化」影响「64.1_读者情绪」（条件：争议点=情绪波形）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

30058｜{"id":"C00145","source":"123.12_读者留存曲线","target":"123.4_黄金三章","type":"绑定","condition":"留存曲线在开篇建立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用黄金三章时，在实际开篇章场核对吸引、扩展与升级的节点及其阅读依据，拟留存安排在 reader_plan 予以标记。

30273｜{"id":"C00146","source":"123.13_留存率优化","target":"42.7_配角转折","type":"转化","condition":"中段修复需配角转折；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知中段需要调整且选择由配角造成转折时，在事件节点写明配角的独立动机、实际行动、局势变化和后续因果。

30488｜{"id":"C00147","source":"123.13_留存率优化","target":"43.1_资源争夺","type":"转化","condition":"中段修复需资源争夺；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确定中段的问题，并且对立双方确有同一资源需求时，根据所需资源安排实际争夺选择、代价和后续事件。

30918｜{"id":"C00149","source":"123.14_完读率优化","target":"130_核心悬念","type":"解决","condition":"完读率=解决悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并完成作用时，推动终点的问题状态收敛。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次范围覆盖本作已选核心悬念的兑现时，在 promise_plan 对照线索、所选揭示和实际命运后果。完读效果以真实数据核对。

31133｜{"id":"C00150","source":"123.16_连载节奏","target":"48.4_章尾钩子","type":"绑定","condition":"连载=钩子；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用连载安排且覆盖章尾时，在章任务写清当前章已推进到何处、读者仍等哪个答案及下一章拟承接的节点。

31348｜{"id":"C00151","source":"123.16_连载节奏","target":"48.13_章节连续性","type":"转化","condition":"连载=连续性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按本作相邻章序，将上一章的实际行动后果或悬念接到下一章开端，在章卡保留连续性依据。

32638｜{"id":"C00157","source":"123.1_爆款定义","target":"132.1_创作承诺","type":"绑定","condition":"爆款=承诺兑现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已定创作承诺时，把实际承诺、兑现事件和可核的结果写入 reader_promise 和 promise_plan。

33498｜{"id":"C00161","source":"123.2_爆款标准","target":"123.7_读者情绪波形","type":"转化","condition":"标准与情绪相关；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用相关评估维度时，把预期情绪变化对照实际章场、触发事件和后续回应，给审稿留下可核对的 reader_plan。

34143｜{"id":"C00164","source":"123.4_黄金三章","target":"112.1_开篇设计","type":"嵌套链","condition":"黄金三章是开篇","priority":1,"effect":"黄金三章是开篇的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「123.4_黄金三章」经「嵌套链」影响「112.1_开篇设计」（条件：黄金三章是开篇）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

34342｜{"id":"C00165","source":"123.4_黄金三章","target":"112.1_开篇设计","type":"绑定","condition":"黄金三章=开篇；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「123.4_黄金三章」经「绑定」影响「112.1_开篇设计」（条件：黄金三章=开篇）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

34557｜{"id":"C00166","source":"123.4_黄金三章","target":"65.1_代入感","type":"绑定","condition":"黄金三章建立代入；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已采用前三章结构时，用真实的处境、阻碍与选择安排读者何时理解人物处境，并写明继续跟随该角色的依据。

34772｜{"id":"C00167","source":"123.4_黄金三章","target":"123.5_开篇吸引力","type":"转化","condition":"黄金三章决定吸引力；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选黄金三章结构时，按实际章节核对开局悬念、冲突扩展或所选升级怎样形成可感知的开篇引力。

34987｜{"id":"C00168","source":"123.5_开篇吸引力","target":"123.4_黄金三章","type":"转化","condition":"吸引力=黄金三章；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用开篇吸引力判据时，用已有章和对应场次定位先呈现的疑问、人物选择及后续回应，采用项目确认的篇幅口径。

35202｜{"id":"C00169","source":"123.5_开篇吸引力","target":"65.1_代入感","type":"转化","condition":"吸引力→代入感；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】利用已定开篇叙述范围和人物具体选择，在 reader_plan 写明读者能知道的处境、理解它的依据及拟形成代入的位置。

35417｜{"id":"C00170","source":"123.6_读者沉没成本","target":"123.7_读者情绪","type":"转化","condition":"沉没成本影响情绪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在已采用的章序里核对读者已经投入理解的具体问题、关系或承诺，用实际事件安排各项投入何时得到情绪回应。

35847｜{"id":"C00172","source":"123.7_读者情绪波形","target":"64.1_读者情绪","type":"转化","condition":"爆款波形=读者波形；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「123.7_读者情绪波形」经「转化」影响「64.1_读者情绪」（条件：爆款波形=读者波形）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

36062｜{"id":"C00173","source":"123.7_读者情绪波形","target":"62.7_呼吸曲线","type":"转化","condition":"波形=呼吸曲线；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选情绪波形时，用真实章场事件把积累、释放和缓冲安排到可定位的快慢变化，写明 reader_plan 上的触发及承接。

36277｜{"id":"C00174","source":"123.8_社交传播点","target":"123.10_名场面","type":"嵌套","condition":"传播点含名场面；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作确实需要候选传播场面时，从已有事件选择人物有明确结果或揭示有情节作用的高点，保留该场面在作品内的任务。

【动态网络原文 · 弧光、未知、承诺及回报】

37766｜{"id":"C00181","source":"124.2_篇幅划分","target":"41.1_三幕","type":"转化","condition":"篇幅决定三幕；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用三幕结构且篇幅明确时，用实际事件和转折安排各幕任务，核对现有冲突及结果能否在已知长度内展开。

39056｜{"id":"C00187","source":"124.9_种类与读者预期","target":"114.4_类型读者预期","type":"转化","condition":"种类预期=类型预期；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以作者已经确认的种类承诺为依据，在实际章序中安排哪些事件建立、改变和回应读者期待。

39271｜{"id":"C00188","source":"124.9_种类与读者预期","target":"65.5_读者预期","type":"转化","condition":"种类预期=读者预期；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】根据已经确认的种类期待及现有故事事件，在 reader_plan 标明读者从哪里得知线索、为何形成下一步预期、哪处予以承接。

44400｜{"id":"C00213","source":"130_核心悬念","target":"23.1_隐蔽流","type":"触发链","condition":"悬念来自隐蔽流","priority":1,"effect":"核心悬念来自隐蔽流","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已明确核心悬念来自隐蔽流时，用现有的幕后行动、早期可见痕迹和后续揭示安排真正的因果联系。

44599｜{"id":"C00214","source":"131.1_原始触动记录","target":"132.1_创作动机","type":"触发链","condition":"触动产生动机","priority":2,"effect":"原始触动产生创作动机","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者提供原始触动时，承接记录中的来源和具体感受，对照作者已说明的个人、表达或读者层面的创作动机。

44798｜{"id":"C00215","source":"132.1_创作动机","target":"63.1_核心主题","type":"触发链","condition":"动机决定主题","priority":1,"effect":"创作动机决定核心主题","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】根据作者实际表达的创作动机和已定核心主题，在现有事件里落实可以观察的选择、代价与命题呼应。

44997｜{"id":"C00216","source":"133.1_章节预览","target":"48.1_起承转合","type":"嵌套链","condition":"预览是起承转合","priority":2,"effect":"章节预览是起承转合的一部分","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已生成章节预览且采用起承转合时，在相应章任务核对现有事件的引入、发展、转折与收束，以及缺的实际承接。

45988｜{"id":"C00221","source":"14.1_感知期","target":"4.1_弧光五阶段","type":"触发链","condition":"感知期是弧光起点","priority":1,"effect":"感知期是弧光的起点","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已将首次感知用作弧光开端时，对照人物的原处境、发生的选择与后来的目标变化，定位这一节点承担的实际作用。

46177｜{"id":"C00222","source":"14.1_感知期","target":"4.1_弧光起点","type":"绑定","condition":"感知期是弧光起点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「14.1_感知期」经「绑定」影响「4.1_弧光起点」（条件：感知期是弧光起点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

47415｜{"id":"C00228","source":"14.2_聚能期","target":"4.1_弧光","type":"绑定","condition":"聚能期是弧光起点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】聚能确实承担本作弧光起点时，用人物第一次有关的选择及其后果核对既定弧光，区分能量储备进度与人物变化。

48034｜{"id":"C00231","source":"14.3_显能期","target":"44.1_爽点","type":"共振","condition":"显能期是爽点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「14.3_显能期」经「共振」影响「44.1_爽点」（条件：显能期是爽点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

48249｜{"id":"C00232","source":"14.3_显能期","target":"44.1_爽点三压抑","type":"触发链","condition":"显能期是爽点","priority":1,"effect":"显能期是爽点释放的时刻","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者选用显能作为回报时，依已有情节核对先前限制如何积累，实际选择怎样产生外部结果，以及哪些压力在该处得到释放。

49676｜{"id":"C00239","source":"14.5_固化期","target":"4.1_弧光五阶段","type":"触发链","condition":"固化期是弧光关键节点","priority":1,"effect":"固化期是弧光的关键节点","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】固化确实承担项目弧光节点时，用实际事件中的决定和随后的行为差异，核对它在人物所选成长路线中的位置。

50699｜{"id":"C00244","source":"140.1_角色未知性","target":"140.2_揭示节奏","type":"演化","condition":"未知性决定揭示节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以项目已有角色秘密和关系事实区分本人、其他角色和读者各自所知，安排实际揭示条件、时间及可能改变的选择。

50914｜{"id":"C00245","source":"140.1_角色未知性","target":"65.2_读者不确定性管理","type":"触发链","condition":"未知性制造不确定性","priority":1,"effect":"角色未知性制造不确定性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已确认的角色未知形成多种可成立的解释时，在 reader_plan 写清前文给过的线索、读者暂未获悉的事实及排除解释的时点。

51113｜{"id":"C00246","source":"140.1_角色未知性","target":"158.1_认知阶梯","type":"转化","condition":"未知性与认知阶梯相关；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用认知阶梯承接角色未知时，用实际行为、线索和新证据写清谁在什么节点理解了人物哪一层，保留读者可得范围。

51328｜{"id":"C00247","source":"140.1_角色未知性","target":"65.2_读者不确定性","type":"转化","condition":"未知性→不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】从已交付角色信息核对读者仍可作出哪些判断，把支持线索、相应不确定性及下一段拟确认的事实写入 reader_plan。

51543｜{"id":"C00248","source":"140.2_未知揭示节奏","target":"130_核心悬念","type":"绑定","condition":"揭示=悬念解决；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】某项新的人物信息用于解释已选核心悬念时，在 promise_plan 对应具体问题、实际揭示和解决范围，保留仍待回答的部分。

51758｜{"id":"C00249","source":"140.2_未知揭示节奏","target":"45.1_伏笔","type":"嵌套","condition":"揭示=伏笔揭示；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「140.2_未知揭示节奏」经「嵌套」影响「45.1_伏笔」（条件：揭示=伏笔揭示）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

51973｜{"id":"C00250","source":"140.3_未知分层","target":"130_核心悬念","type":"绑定","condition":"分层=悬念层级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作确实用人物未知为核心悬念分层时，从实际线索与认知变化安排表层及深层问题的解释顺序和回收。

52188｜{"id":"C00251","source":"140.3_未知分层","target":"45.1_伏笔","type":"嵌套","condition":"分层=伏笔层级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「140.3_未知分层」经「嵌套」影响「45.1_伏笔」（条件：分层=伏笔层级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

52403｜{"id":"C00252","source":"141.1_空间未知","target":"83.1_探索","type":"触发链","condition":"未知驱动探索","priority":1,"effect":"空间未知驱动探索","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已确认未知空间带来探索目标时，核对人物从哪里取得线索、为何需要进入、预期得到什么，并为实际探索保留阻碍。

52602｜{"id":"C00253","source":"141.1_空间未知","target":"83.1_探索","type":"驱动","condition":"空间未知驱动探索；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用未知空间驱动探索的关系时，用实际地点、人物能力和已有路线核对哪些问题确需通过所选探索事件回答。

52817｜{"id":"C00254","source":"141.1_空间未知","target":"130_核心悬念","type":"绑定","condition":"空间未知=核心悬念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】未知地点与本书已定核心悬念确实相连时，用实际进入条件、可获得的物件或信息核对它能回答的悬念范围。

53032｜{"id":"C00255","source":"141.2_信息未知","target":"130_核心悬念","type":"绑定","condition":"信息未知=核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有信息形成核心悬念时，标明哪些人物掌握线索、还有何证据缺失，以及既定事件何时允许获得或揭示。

53247｜{"id":"C00256","source":"141.2_信息未知","target":"45.1_伏笔","type":"嵌套","condition":"信息未知=伏笔；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「141.2_信息未知」经「嵌套」影响「45.1_伏笔」（条件：信息未知=伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

53677｜{"id":"C00258","source":"141.4_探索闭环","target":"122.1_推进","type":"转化","condition":"闭环推动推进；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】探索结果已有依据时，用可见的发现或代价核对人物认知、目标和关系是否改变，标出承接该结果的后续事件。

54306｜{"id":"C00261","source":"142.1_第一人称未知","target":"65.2_读者不确定性","type":"转化","condition":"第一人称→不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】沿用成书已定的第一人称安排，在 reader_plan 写清叙述者可得的信息和读者仍要排除的解释，以及已选释疑节点。

54951｜{"id":"C00264","source":"143.1_不确定性","target":"130_核心悬念","type":"绑定","condition":"不确定性=核心悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已定核心悬念且有可成立的多种解释时，用事件中的实际线索安排逐步收窄和阶段性答案，明确最终回应位置。

55166｜{"id":"C00265","source":"143.1_不确定性","target":"65.2_读者不确定性","type":"转化","condition":"故事不确定性→读者不确定性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据故事已经交付的事实，在 reader_plan 对照每种可成立的路径及其可否排除的证据，说明本段留下哪一具体疑问。

55381｜{"id":"C00266","source":"143.1_不确定性","target":"65.2_读者不确定性管理","type":"触发链","condition":"不确定性需管理","priority":1,"effect":"不确定性是不确定性管理的基础","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本段确有不确定性要管理时，为已有实际问题标注读者当前看到的信息、接下来揭示的时点和可以修正的判断。

55580｜{"id":"C00267","source":"143.4_不确定性强度","target":"65.2_读者不确定性","type":"转化","condition":"强度影响读者感受；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以已用的不确定性强度口径核对关键线索与可成立的选项，在 reader_plan 说明所选事件怎样改变预期，实际体验留给反馈。

55795｜{"id":"C00268","source":"143.4_不确定性强度","target":"130_核心悬念","type":"绑定","condition":"强度=悬念强度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用本书已定悬念的解释范围、证据和利害关系核对各章强度，将强度变化对应到真实事件的推进或回应。

57069｜{"id":"C00274","source":"145.1_目标","target":"145.5_结果","type":"转化","condition":"目标→结果；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据上游角色和事件既定目标，用实际结果核对目标达成、偏离或失败，在事件节点留下相应后果。

59617｜{"id":"C00286","source":"145.5_结果","target":"122.1_推进","type":"转化","condition":"结果→推进；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】有了实际行动结果后，核对它改变了故事中的信息、关系或选择空间的哪一项，并在已有章场节点安排后继因果。

62380｜{"id":"C00299","source":"147.3_锚点建立窗口","target":"123.4_黄金三章","type":"绑定","condition":"建立窗口在开篇；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用黄金三章且人物标记需要在开篇建立时，用现有章序和角色出场安排首次可辨的场合及其实际作用。

63869｜{"id":"C00306","source":"148.2_细节","target":"45.1_伏笔","type":"嵌套","condition":"细节=伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「148.2_细节」经「嵌套」影响「45.1_伏笔」（条件：细节=伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

67010｜{"id":"C00321","source":"15.1_进阶条件","target":"44.3_爽点-代价","type":"共振","condition":"进阶代价与爽点同步；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选进阶承担明确的读者回报时，用实际事件把尝试、人物选择、代价及得到的回报连起来，并在相应章场保留兑现的位置。

67844｜{"id":"C00325","source":"15.3_突破标志","target":"44.1_爽点","type":"共振","condition":"突破标志是爽点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「15.3_突破标志」经「共振」影响「44.1_爽点」（条件：突破标志是爽点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

68059｜{"id":"C00326","source":"15.3_突破标志","target":"4.1_弧光转折","type":"绑定","condition":"突破标志是弧光节点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「15.3_突破标志」经「绑定」影响「4.1_弧光转折」（条件：突破标志是弧光节点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

68274｜{"id":"C00327","source":"15.3_突破的标志","target":"44.1_爽点三压抑","type":"触发链","condition":"突破标志是爽点","priority":1,"effect":"突破标志是爽点释放","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目用突破标志表现回报时，按实际前置压力、人物已选行动及可见标志定位释放节点，核对之前建立的期待是否得到承接。

68678｜{"id":"C00329","source":"15.4_突破代价","target":"44.3_爽点-代价","type":"共振","condition":"突破伴随代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选需要付代价的突破时，将支付与回报落实到同一事件因果及后续选择，标明哪个实际结果持续限制人物。

69082｜{"id":"C00331","source":"15.4_突破的代价类型","target":"44.3_爽点-代价同步","type":"触发链","condition":"突破伴随代价","priority":1,"effect":"突破代价与爽点同步","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用突破代价与爽点同步的安排时，核对具体代价何时发生、读者能看到的回报及它们由哪项已有选择相连。"""
