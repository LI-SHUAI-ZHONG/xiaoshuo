"""类型适配步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 已选作品的类型承诺与组合】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

15956｜{"id":"C00077","source":"114.1_类型必备元素","target":"124.1_小说种类","type":"嵌套","condition":"必备元素=种类；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以作者已选种类及明确承诺为前置，在 adaptations 写清该作品实际采用哪些核心元素，以及各自服务的内容和适用范围。

16386｜{"id":"C00079","source":"114.2_类型惯例","target":"114.3_惯例突破","type":"冲突","condition":"惯例 vs 突破；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确认的惯例与本作所选突破确有冲突时，指出受影响的具体结构、节奏或情感期待，在 boundaries 记下作者确认的保留与调整范围。

17031｜{"id":"C00082","source":"114.3_类型惯例突破","target":"114.2_惯例","type":"冲突","condition":"突破 vs 惯例；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】由作者采用的突破方式回看受到影响的具体惯例，按本边方向核对作品要保留的承诺和实际改变的位置。

17461｜{"id":"C00084","source":"114.4_类型读者预期","target":"124.9_种类预期","type":"转化","condition":"类型预期=种类预期；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以作者已确认的种类、承诺和创新范围为准，写清本作采用的种类预期及触及哪些实际内容。

17676｜{"id":"C00085","source":"114.5_类型融合","target":"124.5_种类融合","type":"转化","condition":"类型融合=种类融合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选融合方案时，在 adaptations 写明各参与类型在主线、辅线中的实际作用、共享的承诺和所选的融合方法。

17891｜{"id":"C00086","source":"114.5_类型融合","target":"123.18_类型融合策略","type":"转化","condition":"类型融合是爆款策略；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者确认采用这条商业创作思路时，围绕项目已选组合核对共同兴奋点、主干冲突与辅线差异，按已定构成口径记录。

31563｜{"id":"C00152","source":"123.18_类型融合","target":"114.5_类型融合","type":"转化","condition":"爆款类型融合=类型融合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已选择融合方式并采用该创作策略时，用实际主辅类型的分工、共同兴奋点和主线冲突核对本作选用的方法。

31778｜{"id":"C00153","source":"123.18_类型融合","target":"124.5_种类融合","type":"转化","condition":"爆款类型融合=种类融合；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】只对已选种类组合梳理主类驱动力、辅类供给及本作共同期待，构成比例使用项目已定口径。

32423｜{"id":"C00156","source":"123.1_爆款定义","target":"124.1_小说种类","type":"嵌套","condition":"爆款与种类相关；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已明确种类和商业定位时，记录本作采用的读者承诺、适用范围和可供审查的目标，商业效果留待依据核实。

【动态网络原文 · 种类、篇幅及融合的已选条件】

37137｜{"id":"C00178","source":"124.1_小说种类","target":"114.1_类型必备元素","type":"触发链","condition":"种类决定必备元素","priority":1,"effect":"小说种类决定必备元素","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者已确定作品种类和要给读者的承诺时，列出本作实际需要哪些核心要素，以及各项服务的情节或体验。

37336｜{"id":"C00179","source":"124.1_小说种类","target":"114.1_类型必备元素","type":"转化","condition":"种类=类型；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用种类与核心元素的关系时，把作者已选的具体内容写入 adaptations，保留适用范围和作品尚待决定的部分。

37551｜{"id":"C00180","source":"124.1_小说种类","target":"123.1_爆款定义","type":"嵌套","condition":"种类与爆款相关；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者明确采用商业定位时，沿已选种类和读者期待记录作品要实现的目标及其评价依据，结果以实际反馈核对。

37981｜{"id":"C00182","source":"124.2_篇幅划分","target":"124.5_种类融合","type":"转化","condition":"篇幅影响融合；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知篇幅和已选组合时，核对主辅类型实际承担的冲突、承诺和展开范围，把需要取舍的部分交回现有作者决策。

38196｜{"id":"C00183","source":"124.3_类型划分","target":"114.1_类型必备元素","type":"转化","condition":"类型决定必备元素；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】根据已定的题材与类型划分，确认作品实际采用的核心元素，各条的用途按当前叙事要求落实。

38411｜{"id":"C00184","source":"124.3_类型划分","target":"124.5_种类融合","type":"转化","condition":"类型影响融合；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已选多个类型时，用实际主线目标和辅线任务核对其分工、接口及相互影响，保留项目选定的融合法。

38626｜{"id":"C00185","source":"124.5_种类融合","target":"114.5_类型融合","type":"转化","condition":"种类融合=类型融合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用种类融合时，将真实的主辅类型、场景或人物分工写进 adaptations，对应作者已选的融合方式。

38841｜{"id":"C00186","source":"124.5_种类融合","target":"123.18_类型融合策略","type":"转化","condition":"种类融合=爆款融合；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选组合确实采用这条市场策略时，核对共同的读者兴奋点、主干驱动力和辅类型提供的差异，比例沿用本作尺度。

41520｜{"id":"C00199","source":"13.1_等级划分","target":"124_小说种类","type":"触发链","condition":"等级决定小说类型","priority":2,"effect":"等级体系决定小说类型","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「13.1_等级划分」经「触发链」影响「124_小说种类」（条件：等级决定小说类型）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。"""
