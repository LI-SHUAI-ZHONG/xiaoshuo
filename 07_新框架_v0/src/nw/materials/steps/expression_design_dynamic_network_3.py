"""表达设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 叙述人称、镜头、感知和可见情感】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

259851｜{"id":"C01238","source":"58.1_第一人称","target":"53.1_近距离","type":"绑定","condition":"第一人称=近距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】第一人称本段已选择近距离时，用叙述者确能感到的动作、反应和即时想法呈现所选内容。

260066｜{"id":"C01239","source":"58.1_第一人称","target":"65.1_代入感","type":"放大","condition":"第一人称强化代入；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前作者采用第一人称加强代入时，依据实际处境、叙述者所知和所作选择提供可见细节，按稿段证据核对。

260711｜{"id":"C01242","source":"58.4_全知视角","target":"109.1_叙述者类型","type":"转化","condition":"全知=叙述者知道一切；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已确认使用全知叙述时，在 guidance 依既定披露安排和真实事实明确本段涉及的角色信息及呈现顺序。

262001｜{"id":"C01248","source":"59.3_配角POV前500字","target":"52.1_视觉","type":"约束","condition":"前500字无主角感官；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目采用配角视角前五百字规则时，按本场配角实际所见、所听和可辨物件安排开段，以该配角作为感知主体。

262861｜{"id":"C01252","source":"59.6_视角切换标记","target":"120.5_视角切换标记","type":"转化","condition":"标记是视角切换一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前视角切换已在章场设计确定时，依据项目采用的标题、分隔或措辞标记实际新观察者。

263076｜{"id":"C01253","source":"59.6_视角切换标记","target":"120.7_读者重置成本","type":"转化","condition":"标记降低重置成本；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有切换位置和新观察者时，用本场开头可核的地点、行动或感知线索让读者识别切换。

263721｜{"id":"C01256","source":"59.8_视角与信息差","target":"142.1_第一人称未知","type":"转化","condition":"视角决定未知；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「59.8_视角与信息差」经「转化」影响「142.1_第一人称未知」（条件：视角决定未知）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

266221｜{"id":"C01268","source":"6.1_厌恶","target":"52.4_嗅觉描写","type":"输出","condition":"厌恶→嗅觉；且当前故事明确采用该静态关系","priority":2,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_厌恶」经「输出」影响「52.4_嗅觉描写」（条件：厌恶→嗅觉）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

266436｜{"id":"C01269","source":"6.1_喜悦","target":"44.2_爽点身体反应","type":"共振","condition":"喜悦与爽点重合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_喜悦」经「共振」影响「44.2_爽点身体反应」（条件：喜悦与爽点重合）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

266651｜{"id":"C01270","source":"6.1_喜悦","target":"7.4_身体反应","type":"转化","condition":"喜悦→身体信号；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_喜悦」经「转化」影响「7.4_身体反应」（条件：喜悦→身体信号）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

267264｜{"id":"C01273","source":"6.1_基础情感_喜悦","target":"44.2_爽点身体反应","type":"共振链","condition":"喜悦被触发且伴随爽点","priority":1,"effect":"喜悦在爽点释放时通过身体反应呈现：放松、微笑、深呼吸","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_喜悦」经「共振链」影响「44.2_爽点身体反应」（条件：喜悦被触发且伴随爽点）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

268259｜{"id":"C01278","source":"6.1_基础情感_悲伤","target":"7.4_情感与身体反应","type":"触发链","condition":"悲伤被触发","priority":1,"effect":"悲伤通过身体反应呈现：肩膀下沉、呼吸变慢、眼神失焦","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_悲伤」经「触发链」影响「7.4_情感与身体反应」（条件：悲伤被触发）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

269055｜{"id":"C01282","source":"6.1_基础情感_愤怒","target":"7.4_情感与身体反应","type":"触发链","condition":"愤怒被触发","priority":1,"effect":"愤怒通过身体反应呈现：握拳、咬牙、瞳孔收缩、脸色发红","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_愤怒」经「触发链」影响「7.4_情感与身体反应」（条件：愤怒被触发）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

270528｜{"id":"C01289","source":"6.1_悲伤","target":"53.1_近距离叙述","type":"绑定","condition":"悲伤场景用近距离；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_悲伤」经「绑定」影响「53.1_近距离叙述」（条件：悲伤场景用近距离）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

270958｜{"id":"C01291","source":"6.1_惊讶","target":"67.2_注意锚定","type":"触发","condition":"惊讶时注意聚焦；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_惊讶」经「触发」影响「67.2_注意锚定」（条件：惊讶时注意聚焦）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

271603｜{"id":"C01294","source":"6.1_愤怒","target":"7.4_身体反应","type":"转化","condition":"愤怒→身体信号；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_愤怒」经「转化」影响「7.4_身体反应」（条件：愤怒→身体信号）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

271818｜{"id":"C01295","source":"6.1_愤怒","target":"52.1_视觉描写","type":"输出","condition":"愤怒→表情；且当前故事明确采用该静态关系","priority":2,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_愤怒」经「输出」影响「52.1_视觉描写」（条件：愤怒→表情）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

279071｜{"id":"C01330","source":"6.8_审美情感","target":"160.1_审美情感","type":"转化","condition":"审美情感分类；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前段落采用审美情感时，按作者已定的感受范围选择与实际物件、事件和视角相符的细节。

279286｜{"id":"C01331","source":"6.8_审美情感","target":"111.1_核心象征物","type":"触发链","condition":"审美情感与象征物关联","priority":2,"effect":"审美情感通过象征物呈现","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已存在象征物承担审美作用时，用当前观察者确能看到的形态、变化和动作呈现所定感受。

279485｜{"id":"C01332","source":"6.8_审美情感","target":"156.2_描述审美","type":"转化","condition":"审美情感影响描述；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】场中已有审美体验时，以实有描写对象和叙述距离核对感觉如何经过所见或所闻得以呈现。

279700｜{"id":"C01333","source":"6.8_审美情感","target":"160.1_审美情感","type":"触发链","condition":"审美情感被触发","priority":2,"effect":"审美情感是审美体验的核心","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已安排审美情感的触发时，从实际体验对象和角色反应选择可感表现及其在当段的效果。

280512｜{"id":"C01337","source":"6.9_道德情感","target":"160.2_道德审美","type":"转化","condition":"道德情感是道德审美的基础；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有可见的道德情感及审美任务时，用人物实际行为、身体反应或可闻措辞表现已定感受。

280727｜{"id":"C01338","source":"60.15_定格","target":"60.4_特写","type":"转化","condition":"定格是特写极端；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】如果本段已采用定格式表现，依据当前实际对象、可见细部及停顿时间核对特写要强调的结果。

280942｜{"id":"C01339","source":"60.15_定格","target":"44.8_高潮三层叠加","type":"绑定","condition":"定格用于高潮；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作选用定格表现高潮节点时，用既有动作结果、可感反应或关键物件确定结束于何处及要突出什么。

281372｜{"id":"C01341","source":"60.1_远景镜头","target":"52.1_视觉","type":"转化","condition":"远景呈现视觉；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前环境从远处可见时，用真实整体方位、轮廓与实际移动表现所选空间关系。

281587｜{"id":"C01342","source":"60.3_近景镜头","target":"52.1_视觉","type":"转化","condition":"近景聚焦细节；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本段选用近景时，从当前视角可辨的身体、物件或动作细部核对阅读焦点。

281802｜{"id":"C01343","source":"60.3_近景镜头","target":"50.1_精确动词","type":"绑定","condition":"近景聚焦动作；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有近景呈现动作时，选实际对应动作方向、对象和结果的准确动词。

282017｜{"id":"C01344","source":"60.5_主观镜头","target":"58.1_第一人称","type":"转化","condition":"主观=第一人称体现；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选第一人称或本段主观化表达时，以真实观察者的感知和已有叙述人称表现其可知内容。

282232｜{"id":"C01345","source":"60.5_主观镜头","target":"59.8_信息差","type":"转化","condition":"主观决定信息差；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前采用主观观察时，用已确定人物真正看见的事实和其他人持有的信息范围核对披露方式。

282447｜{"id":"C01346","source":"60.7_推镜头","target":"60.1_远景","type":"转化","condition":"推从远景开始；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选观察从远处推进到细节时，根据本场空间和动作编排观察顺序与真实焦点。

282662｜{"id":"C01347","source":"60.7_推镜头","target":"62.2_快慢交替","type":"转化","condition":"推镜头影响节奏；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前观察过程确用来改变快慢时，按实际视野变化、所选动作及最终可见结果安排节拍。

283076｜{"id":"C01349","source":"61.1_重章","target":"49.1_短句","type":"绑定","condition":"重章多用短句；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】重章已有需要加快的段落时，用具体前因、所见动作和结果核对短句适用位置。

283291｜{"id":"C01350","source":"61.1_重章","target":"53.1_近距离","type":"绑定","condition":"重章用近距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前重章已选近距离时，以观察者确能感知的动作、当下想法或身体反应表现关键变化。

283506｜{"id":"C01351","source":"61.1_重章","target":"53.1_近距离叙述","type":"触发链","condition":"重章使用近距离叙述","priority":1,"effect":"重章使用近距离叙述","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】重章采用近距离叙述时，以真实人物行动、可得信息和可查结果划定所用段落。

284350｜{"id":"C01355","source":"61.2_中章","target":"53.2_中距离","type":"绑定","condition":"中章用中距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】中章已经采用中距离时，按本场人物可观察到的行为和背景材料确定可感细节。

284979｜{"id":"C01358","source":"61.3_轻章","target":"49.3_长句","type":"绑定","condition":"轻章多用长句；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当轻章已定部分需要放缓时，用实际可感结果和角色所见安排较长句式，核对其作用。

285194｜{"id":"C01359","source":"61.3_轻章","target":"53.3_远距离","type":"绑定","condition":"轻章用远距离；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本段轻章已经采用远距离时，以既定视角、时间或环境变化给出可见的整体结果。

285409｜{"id":"C01360","source":"61.3_轻章","target":"110.1_氛围","type":"绑定","condition":"轻章侧重氛围；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已用轻章呈现气氛时，从实际地点、人物状态和可接触信号说明本章采用的氛围与可辨证据。

287543｜{"id":"C01370","source":"62.2_场景内快慢交替","target":"53.1_近距离","type":"转化","condition":"近距离=快；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在已选加速段落使用近距离时，根据当前视角可感动作和即时变化核对叙述焦点及快慢。

287758｜{"id":"C01371","source":"62.2_场景内快慢交替","target":"53.1_近距离叙述","type":"触发链","condition":"快用近距离","priority":1,"effect":"快慢交替由叙述距离控制","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目采用叙述距离调节场内快慢时，从实际动作中选用近距离片段，核对前后可见的变化和节拍。

287957｜{"id":"C01372","source":"62.2_场景内快慢交替","target":"53.3_远距离","type":"转化","condition":"远距离=慢；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定段落需要拉远并放缓时，依据实有场景和可查环境变化安排叙述跨度及放缓位置。

294128｜{"id":"C01401","source":"65.1_读者代入感","target":"53.1_近距离叙述","type":"绑定","condition":"近距离强化代入；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本段以近距离支持代入时，依已定视角的实在感知、即时反应和可做选择安排具体表现。

294343｜{"id":"C01402","source":"65.1_读者代入感","target":"53.1_近距离叙述","type":"触发链","condition":"近距离强化代入感","priority":1,"effect":"近距离叙述强化代入感","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作选用近距离叙述增强投入时，用当前人物真实处境、能见信息和可感区分核对重点。

295601｜{"id":"C01408","source":"65.3_读者注意力","target":"52.1_视觉","type":"转化","condition":"注意力通过视觉引导；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定视觉线索要引导注意时，从当前视角能够辨认的具体对象、位置或变化安排观察焦点。

296031｜{"id":"C01410","source":"65.4_读者阅读速度","target":"53.1_近距离","type":"转化","condition":"近距离=快阅读；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前用近距离计划加快阅读时，依实有动作、断句及视角核对可见节拍，实际阅读速度依已有反馈。

297950｜{"id":"C01419","source":"67.1_感知","target":"52.1_视觉","type":"输出","condition":"角色在看；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色正在可视范围观察时，用当下能看见的物件、行动及变化表现真正进入视野的信息。

298165｜{"id":"C01420","source":"67.1_感知","target":"52.2_听觉","type":"输出","condition":"角色在听；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当场角色确能听见信号时，用当前方位、实际声音来源及可辨变化表现所获信息。

298380｜{"id":"C01421","source":"67.1_感知","target":"52.3_触觉","type":"输出","condition":"角色在触摸；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色实际接触对象时，用其可感的接触方式、触感和反应表现此项感知结果。

298595｜{"id":"C01422","source":"67.1_感知","target":"52.4_嗅觉","type":"输出","condition":"角色在闻；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】场中采用嗅觉时，从项目已知气味来源及当下风向或距离核对人物能感到什么。

299869｜{"id":"C01428","source":"67.3_记忆","target":"158.3_回忆设计","type":"转化","condition":"记忆触发回忆；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】剧情已确认有人物记忆被触发时，用当前可感线索、真实回忆范围和情境返回点组织表现。

304137｜{"id":"C01448","source":"68.6_后见之明","target":"159.3_事后归因","type":"扭曲","condition":"事后认为'早就知道'；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，改变终点状态的解释或表现方式。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】场中有人物回顾已知结果时，用当时可见的信息与当前回顾的真实措辞表现其事后解释。

304567｜{"id":"C01450","source":"68.7_自利偏误","target":"159.3_事后归因","type":"扭曲","condition":"成功归己失败归外；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，改变终点状态的解释或表现方式。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用自利偏误写事后归因时，以角色真实的回顾和能够回查的行动结果表现他如何分配责任。

309464｜{"id":"C01473","source":"7.1_情感触发条件","target":"7.4_情感与身体反应","type":"触发链","condition":"情感被触发","priority":1,"effect":"触发条件产生身体反应","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本段已设实际情感触发和身体回应时，用视角可感的动作、声音或变化呈现二者的具体因果。

309663｜{"id":"C01474","source":"7.1_情感触发条件","target":"7.4_身体反应","type":"触发","condition":"条件满足→身体反应；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】根据当前角色实际遇到的触发，核对随之出现的可见身体细节及与所选场景的联系。

309878｜{"id":"C01475","source":"7.2_情感在对话中","target":"57.1_潜台词","type":"转化","condition":"情感→潜台词；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前对话已设真实情感及交流目的时，用可闻表达、停顿或反应表现潜台词的主要变化。

310093｜{"id":"C01476","source":"7.2_情感在对话中","target":"57.5_说话风格","type":"转化","condition":"情感→说话风格；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「7.2_情感在对话中」经「转化」影响「57.5_说话风格」（条件：情感→说话风格）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

310308｜{"id":"C01477","source":"7.2_情感在对话中的呈现","target":"57.1_潜台词","type":"触发链","condition":"情感需要被呈现","priority":1,"effect":"情感通过潜台词在对话中呈现","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以人物现有情感、对话目标和所知信息为前置，用实际话语之外的具体含义与可见反应呈现。

310507｜{"id":"C01478","source":"7.2_情感在对话中的呈现","target":"52.2_听觉描写","type":"触发链","condition":"情感通过声音被感知","priority":2,"effect":"情感通过听觉描写呈现","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场情感已经通过声音表露时，依听者能感知的语气、停顿或声音变化核对该表现。

310706｜{"id":"C01479","source":"7.2_情感在对话中的呈现","target":"57.5_说话风格一致性","type":"触发链","condition":"情感影响说话风格","priority":2,"effect":"情感状态影响说话风格","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以本作已批准的角色说话风格为前置，用本次情感及实际台词核对短时变化和可辨的持续特征。

312346｜{"id":"C01487","source":"7.4_情感与身体反应","target":"145.3_心理","type":"触发链","condition":"情感被感知","priority":1,"effect":"身体反应反映心理状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场已有人物真实的情感反应时，按观察者可见的身体变化及已知情境留下支持心理理解的具体线索。

312545｜{"id":"C01488","source":"7.4_情感与身体反应","target":"52.3_触觉描写","type":"触发链","condition":"情感通过身体反应呈现","priority":1,"effect":"情感通过触觉描写呈现","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色确能感到由情感引起的体感时，依实际触发、感觉范围及所选动作安排可辨细节。

312943｜{"id":"C01490","source":"7.4_情感与身体反应","target":"156.5_动作审美","type":"触发链","condition":"身体反应需要审美呈现","priority":2,"effect":"身体反应通过动作审美呈现","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前场确以身体反应表现关键情感时，选择能体现实际动作和结果的细节，沿用已经确定的表达目标。

313142｜{"id":"C01491","source":"7.4_身体反应","target":"52.1_视觉描写","type":"输出","condition":"身体反应→视觉；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前视角能够观察真实身体反应时，以实际动作、部位或变化表现情感证据。

313357｜{"id":"C01492","source":"7.4_身体反应","target":"52.3_触觉描写","type":"输出","condition":"身体反应→触觉；且当前故事明确采用该静态关系","priority":1,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场有真实可感体感时，依当前视角、实际接触和反应给出触觉差异。

313572｜{"id":"C01493","source":"7.4_身体反应","target":"145.3_心理","type":"转化","condition":"身体反应反映心理；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用当前人物可观察的身体反应和已知处境支撑心理呈现，按本作已经确定的可知范围交代。

315212｜{"id":"C01501","source":"7.6_情感释放","target":"44.8_高潮三层情感叠加","type":"共振","condition":"释放是高潮；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前高潮已选情感释放时，以实际身体反应、决定或可闻表达给出可感结果，保持情感层次的区别。

315427｜{"id":"C01502","source":"7.6_情感释放","target":"44.8_高潮三层情感叠加","type":"触发链","condition":"情感释放发生在高潮","priority":1,"effect":"情感释放是高潮的核心","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场高潮中有已安排的情感释放时，把真实动作及其可见后果落实到当前视角。

【动态网络原文 · 时间体验、观察及可感反应】

323851｜{"id":"C01542","source":"72.3_冲动决策","target":"44.2_爽点","type":"共振","condition":"冲动释放；且当前故事明确采用该静态关系","priority":3,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确认冲动是本段回报或情感释放的一部分时，按当前视角可感行动、发言或身体反应表现结果。

338773｜{"id":"C01612","source":"77.3_时间漫长","target":"79.3_时间密度","type":"转化","condition":"漫长=高密度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前视角已设感到时间漫长时，用实际等待、可辨过程与出现的变化安排叙述密度。

339402｜{"id":"C01615","source":"77.4_时间短暂","target":"79.3_时间密度","type":"转化","condition":"短暂=低密度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】人物确感觉某段短暂时，结合当前所见事件数量、发生顺序及选定叙述距离给出真实表现。

339617｜{"id":"C01616","source":"77.4_时间短暂","target":"62.2_快节奏","type":"绑定","condition":"短暂=快节奏；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「77.4_时间短暂」经「绑定」影响「62.2_快节奏」（条件：短暂=快节奏）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

340047｜{"id":"C01618","source":"77.5_时间停滞","target":"160.1_审美情感","type":"转化","condition":"停滞产生审美情感；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作以时间停滞感表现审美情感时，从实际环境、人物等待和可感变化确定能看到的细节与节拍。

342181｜{"id":"C01628","source":"79.2_时间密度","target":"77.3_漫长","type":"转化","condition":"密度决定漫长感；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选细写一段时间时，用同一视角实际得到的动作、等待与变化核对表现出的漫长感。

351847｜{"id":"C01674","source":"8.2_愤怒","target":"6.1_释放","type":"转化","condition":"行动后；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_愤怒」经「转化」影响「6.1_释放」（条件：行动后）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

353137｜{"id":"C01680","source":"8.2_焦虑","target":"7.4_心跳加速","type":"触发","condition":"突发；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_焦虑」经「触发」影响「7.4_心跳加速」（条件：突发）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

354180｜{"id":"C01685","source":"8.2_精神状态_焦虑","target":"7.4_情感与身体反应","type":"触发链","condition":"焦虑状态","priority":1,"effect":"焦虑通过身体反应呈现：手心出汗、呼吸变浅、心跳加速","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_精神状态_焦虑」经「触发链」影响「7.4_情感与身体反应」（条件：焦虑状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

360000｜{"id":"C01713","source":"80.1_抗争","target":"44.1_爽点压抑","type":"共振","condition":"抗争是爽点根源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「80.1_抗争」经「共振」影响「44.1_爽点压抑」（条件：抗争是爽点根源）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

362779｜{"id":"C01726","source":"81.6_命运揭示时机","target":"45.3_伏笔揭示","type":"转化","condition":"命运揭示=伏笔揭示；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前段落确要揭示已知命运线索时，用视角可见的物件、措辞或行动兑现已设揭示范围。

365096｜{"id":"C01737","source":"83.1_探索","target":"52.1_视觉","type":"输出","condition":"探索通过视觉呈现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点完成处理时，将其状态结果传递给终点。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用视觉表现探索时，用叙述者确能看到的路线、物件及空间变化显示所得线索。

371036｜{"id":"C01765","source":"85.1_询问","target":"56.1_试探","type":"转化","condition":"询问=试探；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定询问确承担试探时，用真实谈话目标、所问事实与已安排反应呈现台词作用。

373584｜{"id":"C01777","source":"85.5_透露","target":"57.1_潜台词","type":"转化","condition":"透露=潜台词；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选含蓄透露某项信息时，用实际说话、接触对象与视角可辨动作呈现可推知部分。

373799｜{"id":"C01778","source":"85.5_透露","target":"45.1_伏笔","type":"嵌套","condition":"透露是伏笔；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「85.5_透露」经「嵌套」影响「45.1_伏笔」（条件：透露是伏笔）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。"""
