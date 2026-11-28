"""表达设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 情感反应、视角、感官、句式及对话】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

203795｜{"id":"C00974","source":"44.1_爽点三压抑","target":"44.2_爽点身体反应","type":"触发链","condition":"压抑后释放身体反应","priority":1,"effect":"压抑后释放身体反应","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选事件释放前置压力时，用本场视角可感的动作、呼吸或停顿表现释放前后真实的身体差异。

203994｜{"id":"C00975","source":"44.1_爽点三压抑","target":"44.2_爽点身体反应","type":"转化","condition":"压抑→释放；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】承接本作已有压抑与释放安排，在 guidance 写清哪个实际动作结束压力，以及视角当下能看见的反应。

204838｜{"id":"C00979","source":"44.2_爽点身体反应","target":"52.1_视觉描写","type":"输出","condition":"身体反应通过视觉呈现；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已安排角色在关键结果后出现身体反应时，选当前视角能看见的可辨动作、姿态或外观差异来表现。

205053｜{"id":"C00980","source":"44.2_爽点身体反应","target":"7.4_情感与身体反应","type":"触发链","condition":"身体反应是情感反应","priority":1,"effect":"爽点身体反应是情感身体反应","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选回报确引起某项情感变化时，依真实事件、身体反应和本场观察者把表现与原因相连。

205252｜{"id":"C00981","source":"44.2_爽点身体反应","target":"7.4_身体反应","type":"转化","condition":"爽点是身体反应；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场面的情感释放已有设计时，用实际可感变化表现其怎样发生，遵循作者选定的情绪和人物反应。

209687｜{"id":"C01002","source":"44.8_高潮三层情感叠加","target":"6.1_基础情感","type":"触发链","condition":"高潮释放基础情感","priority":1,"effect":"高潮释放基础情感","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已确认高潮释放某项基础情感时，从实际人物处境、触发及可感反应选取与之对应的表现。

209886｜{"id":"C01003","source":"44.8_高潮三层情感叠加","target":"6.1_基础情感","type":"转化","condition":"高潮释放基础情感；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按选定高潮和当前观察者给出可辨的情感层次、身体反应与行为结果，保留先后关系。

210101｜{"id":"C01004","source":"44.8_高潮三层情感叠加","target":"7.6_情感释放","type":"嵌套链","condition":"高潮是情感释放","priority":1,"effect":"高潮是情感释放","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前高潮中已安排实际情感释放时，用可展现的停顿、动作或发言表现释放前后情绪变化。

210300｜{"id":"C01005","source":"44.8_高潮三层情感叠加","target":"7.6_情感释放","type":"转化","condition":"高潮是情感释放；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】承接明确的情感触发及角色选择，在 guidance 写出本场可见释放形态和核对效果。

215380｜{"id":"C01029","source":"45.1_伏笔埋设","target":"35.1_隐性传递","type":"嵌套","condition":"伏笔通过隐性传递；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前场景承担埋设且项目采用隐性传递时，以现有物件、说话或动作留下可回查的细节，沿用视角知情范围。

215595｜{"id":"C01030","source":"45.1_伏笔埋设","target":"35.1_隐性传递","type":"嵌套链","condition":"伏笔通过隐性传递埋设","priority":1,"effect":"伏笔通过隐性传递埋设","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】选定伏笔需要间接表现时，在 guidance 指出实际可感的内容、其表面用途和以后可复核的证据。

218095｜{"id":"C01042","source":"45.3_伏笔揭示","target":"44.2_爽点","type":"共振","condition":"揭示伴随爽感；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场采用伏笔揭示作为回报时，从视角能看到的动作、理解改变或身体反应选择可辨表现，保留真实触发。

225229｜{"id":"C01076","source":"46.3_场景过渡","target":"120.5_视角切换标记","type":"约束","condition":"过渡需视角标记；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有角色视角切换时，用项目采用的章场标记及前后观察范围组织可辨的表达，核对读者能识别新视角。

225858｜{"id":"C01079","source":"46.4_场景视角","target":"120.5_视角切换标记","type":"转化","condition":"场景视角需标记；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前切换已在章场设计中确定时，使用项目选定的标题、分隔或语言提示，给读者明确的新观察者和可感线索。

227777｜{"id":"C01088","source":"46.9_场景内快慢交替","target":"53.1_近距离","type":"转化","condition":"近距离=快；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已有需加速的近距离段落时，用当前观察者可感的动作与即时反应落实变化，并依实际可见节奏核查。

227992｜{"id":"C01089","source":"46.9_场景内快慢交替","target":"53.3_远距离","type":"转化","condition":"远距离=慢；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前实有段落采用远距离进行慢速交代时，用可辨空间、行动结果或环境变化安排叙述跨度。

235405｜{"id":"C01124","source":"48.2_开篇规则","target":"145.4_动作","type":"输出","condition":"开篇可以动作起；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】章首已经选用动作切入时，在可用视角内表现已有动作、对象及可见结果，使开篇任务能辨认。

235620｜{"id":"C01125","source":"48.2_开篇规则","target":"56.1_试探","type":"输出","condition":"开篇可以对话起；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已经采用对话开篇及试探目的时，用真实说话者、在场事实和可见反应确定首段对话如何展开。

238996｜{"id":"C01141","source":"49.1_短句","target":"53.1_近距离","type":"转化","condition":"短句=近距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本段已选近距离与较短句式时，以当前视角的动作、所见或即时想法落实节拍，并核对读者能跟上实际动作。

239211｜{"id":"C01142","source":"49.1_短句","target":"61.1_重章","type":"绑定","condition":"重章多用短句；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选重章中需要加快的段落时，依据当前动作的先后和结果使用短句，保留作用范围及可见依据。

239426｜{"id":"C01143","source":"49.1_短句","target":"62.2_快节奏","type":"转化","condition":"短句加快节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「49.1_短句」经「转化」影响「62.2_快节奏」（条件：短句加快节奏）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

239641｜{"id":"C01144","source":"49.2_中句","target":"53.2_中距离","type":"转化","condition":"中句=中距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用中距离表现某段事件时，以实在观察对象和信息量核对是否适用中等句幅，保留合适细节。

239856｜{"id":"C01145","source":"49.2_中句","target":"61.2_中章","type":"绑定","condition":"中章多用中句；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次中章采用中等句幅时，用具体行动与背景信息核对写作节拍和可理解的叙述任务。

240071｜{"id":"C01146","source":"49.3_长句","target":"53.3_远距离","type":"转化","condition":"长句=远距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选较远叙述距离和较长句式时，根据当事人能见的全局、时间变化或环境信息确定句中可交代的内容。

240286｜{"id":"C01147","source":"49.3_长句","target":"61.3_轻章","type":"绑定","condition":"轻章多用长句；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前轻章有预定放缓部分时，按所选事件和所见环境安排较长的叙述单位，给已经确立的章内任务留位置。

240501｜{"id":"C01148","source":"5.10_距离光谱","target":"53.1_近距离叙述","type":"转化","condition":"距离影响叙述；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「5.10_距离光谱」经「转化」影响「53.1_近距离叙述」（条件：距离影响叙述）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

246306｜{"id":"C01175","source":"5.7_信息不对称","target":"142.1_第一人称未知","type":"嵌套","condition":"视角制造不对称；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选第一人称处理信息差时，以叙述者确能知觉的信息、他人可见行为及所保留事实确定当下的表现。

247811｜{"id":"C01182","source":"50.1_精确动词","target":"145.4_动作","type":"转化","condition":"动词外化动作；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按当前实际动作、施作对象和结果选可区分用力方式、方向或变化的动词，核对是否和本场视角一致。

248241｜{"id":"C01184","source":"50.1_精确动词","target":"60.3_近景镜头","type":"绑定","condition":"近景聚焦精确动词；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选近景聚焦实际动作时，用能区别接触、移动及作用结果的动词呈现可辨细节。

248456｜{"id":"C01185","source":"52.1_视觉描写","target":"60.1_远景镜头","type":"转化","condition":"视觉呈现环境；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前采用远景观察环境时，用本场视角确能看到的整体轮廓、距离与显著环境变化构成画面。

248671｜{"id":"C01186","source":"52.1_视觉描写","target":"60.3_近景镜头","type":"转化","condition":"视觉聚焦动作；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前近景承担动作表现时，从真实观察位置选择能明确展示动作起点、对象与结果的细节。

249101｜{"id":"C01188","source":"52.2_听觉描写","target":"57.1_潜台词","type":"转化","condition":"听觉是潜台词体现；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已定说话者存在潜台词时，用本场听得到的语气、停顿或伴随声表现可支持的含义，沿用人物所知。

249316｜{"id":"C01189","source":"52.2_听觉描写","target":"110.1_氛围","type":"转化","condition":"听觉营造氛围；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前用声音表现氛围时，从已设场地和事件中选择真实可听的声音、方向与反应。

249531｜{"id":"C01190","source":"52.3_触觉描写","target":"8.1_身体状态","type":"转化","condition":"触觉是身体状态体现；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有可经触觉表现的身体状态时，用实际接触、角色可感范围及反应呈现当前状态的证据。

249746｜{"id":"C01191","source":"52.3_触觉描写","target":"145.4_动作","type":"转化","condition":"触觉是动作体现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以已选动作、接触对象及视角能觉察的触感核对过程和可见结果，选取与该动作相符的细节。

249961｜{"id":"C01192","source":"52.4_嗅觉描写","target":"110.1_氛围","type":"转化","condition":"嗅觉营造氛围；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场有真实气味来源时，用项目视角可辨的气味与相应环境或动作表现已有氛围。

250176｜{"id":"C01193","source":"52.4_嗅觉描写","target":"8.1_身体状态","type":"转化","condition":"嗅觉是身体状态体现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】身体状态由项目事实确定且有可闻气味时，核对它的实际来源、当前视角能察觉的范围及相关反应。

250606｜{"id":"C01195","source":"52.6_五感规则","target":"52.1_视觉","type":"嵌套","condition":"五感之一；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用视觉感官时，依据当前观察位置、可见对象和主要动作选取能服务场景目的的细节。

250821｜{"id":"C01196","source":"52.6_五感规则","target":"52.2_听觉","type":"嵌套","condition":"五感之一；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场有实际听觉线索时，选择观察者能听见的来源、方向和变化，并核对它在事件中起到的作用。

251036｜{"id":"C01197","source":"52.6_五感规则","target":"52.3_触觉","type":"嵌套","condition":"五感之一；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前人物可以实际接触对象时，根据触点、可感差异与动作结果给出贴合场景任务的触觉内容。

251251｜{"id":"C01198","source":"53.1_近距离叙述","target":"58.1_第一人称","type":"转化","condition":"近距离=第一人称；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选第一人称和近距离叙述时，以叙述者确能感知及理解的实际内容表现当前行动和想法。

251466｜{"id":"C01199","source":"53.1_近距离叙述","target":"61.1_重章","type":"绑定","condition":"重章用近距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场所在重章已选近距离处理关键动作时，给出能观察的即时细节及其在本章推进中的作用。

251681｜{"id":"C01200","source":"53.1_近距离叙述","target":"145.3_心理描写","type":"转化","condition":"近距离展示心理；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「53.1_近距离叙述」经「转化」影响「145.3_心理描写」（条件：近距离展示心理）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

251896｜{"id":"C01201","source":"53.2_中距离叙述","target":"61.2_中章","type":"绑定","condition":"中章用中距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前中章采用中距离叙述时，依据角色可知范围与事件任务选择适量动作、背景和反应。

252111｜{"id":"C01202","source":"53.2_中距离叙述","target":"148.1_观察","type":"转化","condition":"中距离是观察体现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已用中距离承载观察时，给出人物实际观察的对象、间隔及从中能确认的具体变化。

252326｜{"id":"C01203","source":"53.3_远距离叙述","target":"61.3_轻章","type":"绑定","condition":"轻章用远距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前轻章已有需要拉远的段落时，用可观察环境、后果和时间变化完成现有章内任务。

252541｜{"id":"C01204","source":"53.3_远距离叙述","target":"115.1_空间结构","type":"转化","condition":"远距离展示空间；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用远距离展示空间时，按选定视角所能看到的地点、整体位置和事件留下的路线组织表达。

252756｜{"id":"C01205","source":"53.4_距离变化","target":"53.1_近距离","type":"嵌套","condition":"距离之一；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有叙述距离变化时，依据当下可感动作、情绪和观察条件明确变近的节点及具体表现。

252971｜{"id":"C01206","source":"53.4_距离变化","target":"53.3_远距离","type":"嵌套","condition":"距离之一；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已设叙述距离拉远时，用实际时间跨度或可看到的环境结果确定转换位置与适用范围。

253186｜{"id":"C01207","source":"53.4_距离变化","target":"62.2_快慢交替","type":"转化","condition":"距离变化影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】场中确实改变叙述距离时，以已知动作轻重和可得信息核对前后语速变化，并保留视角约束。

253401｜{"id":"C01208","source":"54.1_快节奏语言","target":"49.1_短句","type":"绑定","condition":"快节奏用短句；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已选择加快实际行动段落时，使用贴合动作先后和观察范围的短句，核对动作和结果仍清楚。

253616｜{"id":"C01209","source":"54.1_快节奏语言","target":"50.1_精确动词","type":"绑定","condition":"快节奏动词密集；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已设本段快节奏时，从实际行动选取能快速辨认方式、对象和结果的准确动词。

253831｜{"id":"C01210","source":"54.1_快节奏语言","target":"61.1_重章","type":"绑定","condition":"重章用快节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前重章已有选定的加速片段时，依据具体事件、行动次序和转折点安排句式速度。

254046｜{"id":"C01211","source":"54.3_慢节奏语言","target":"49.3_长句","type":"绑定","condition":"慢节奏用长句；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本段已选慢节奏时，用较长的叙述单位交代实际动作、感知或停顿，符合当前视角与情境。

254261｜{"id":"C01212","source":"54.3_慢节奏语言","target":"52.1_视觉","type":"绑定","condition":"慢节奏多描写；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用慢节奏展开视觉时，从本场真实观察过程选择有作用的空间或外观细节，留出可理解的次序。

254476｜{"id":"C01213","source":"54.3_慢节奏语言","target":"61.3_轻章","type":"绑定","condition":"轻章用慢节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已让轻章承担放缓时，用现有关系余波、环境或人物反应决定展开处及其结束条件。

254691｜{"id":"C01214","source":"55.3_语言风格锚点","target":"57.5_说话风格","type":"约束","condition":"风格锚点决定说话风格；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「55.3_语言风格锚点」经「约束」影响「57.5_说话风格」（条件：风格锚点决定说话风格）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

254906｜{"id":"C01215","source":"55.3_语言风格锚点","target":"124.1_小说种类","type":"嵌套","condition":"类型决定语言风格；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「55.3_语言风格锚点」经「嵌套」影响「124.1_小说种类」（条件：类型决定语言风格）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

255121｜{"id":"C01216","source":"56.1_试探","target":"57.1_潜台词","type":"转化","condition":"试探通过潜台词；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已选择的试探对话，用实际说话者目标、表面所说和人物可见反应表现具体潜台词。

255766｜{"id":"C01219","source":"56.2_隐瞒","target":"57.1_潜台词","type":"转化","condition":"隐瞒通过潜台词；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】人物已选择隐瞒某项事实时，用可见措辞、回避、停顿或动作表现他当下能够说的范围。

256841｜{"id":"C01224","source":"56.9_对话目的","target":"57.1_潜台词","type":"转化","condition":"目的通过潜台词；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据已明定的对话目的和角色关系，在本场用具体说法、动作或停顿表现话语外的实际意图。

257056｜{"id":"C01225","source":"56.9_对话目的","target":"43.2_信息博弈","type":"嵌套","condition":"目的是博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前对话已确立为信息博弈时，用已知目的和角色各自所知核对读者可辨的措辞变化及其效果。

257271｜{"id":"C01226","source":"57.1_潜台词","target":"56.1_试探","type":"转化","condition":"潜台词承载试探；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本段的潜台词承担试探时，用已选台词、停顿及可见反应表现试探的具体对象和暂时结果。

257486｜{"id":"C01227","source":"57.1_潜台词","target":"56.2_隐瞒","type":"转化","condition":"潜台词承载隐瞒；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已经安排的隐瞒内容，用当前说话者允许透露的事实及可感动作落实潜台词的边界。

257701｜{"id":"C01228","source":"57.1_潜台词","target":"43.2_信息博弈","type":"嵌套","condition":"潜台词推动博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场信息博弈确通过潜台词推进时，按真实信号及回应核对对话前后能确认什么、什么仍保留。

257916｜{"id":"C01229","source":"57.3_非台词元素","target":"52.1_视觉","type":"转化","condition":"非台词通过视觉；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场对话中的非台词元素采用视觉时，选择当前视角能见的物件、表情或动作，并明确其与所说内容的关系。

258131｜{"id":"C01230","source":"57.3_非台词元素","target":"52.2_听觉","type":"转化","condition":"非台词通过听觉；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据场中真实声音、说话者所在位置及可闻变化安排非台词信息，核对它怎样影响对话理解。

258346｜{"id":"C01231","source":"57.3_非台词元素","target":"7.4_身体反应","type":"转化","condition":"非台词通过身体反应；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前动作或身体反应确会改变一轮对话时，用实际触发和本场可观察的反应表现该作用。

258561｜{"id":"C01232","source":"57.4_对话速度","target":"62.1_节奏轮换","type":"转化","condition":"对话速度影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已定对话节奏变化时，按实际往返、停顿与事件推进核对它如何承接场内快慢。

258776｜{"id":"C01233","source":"57.4_对话速度","target":"56.1_试探","type":"转化","condition":"速度影响试探效果；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对当前已选试探，用既有说话速度、回应时点和角色可感反应核对关键问题如何被接住或回避。

258991｜{"id":"C01234","source":"57.5_说话风格","target":"146.1_人格外化","type":"转化","condition":"说话风格是人格外化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「57.5_说话风格」经「转化」影响「146.1_人格外化」（条件：说话风格是人格外化）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

259421｜{"id":"C01236","source":"57.5_说话风格","target":"55.3_风格锚点","type":"约束","condition":"风格保持一致；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「57.5_说话风格」经「约束」影响「55.3_风格锚点」（条件：风格保持一致）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。"""
