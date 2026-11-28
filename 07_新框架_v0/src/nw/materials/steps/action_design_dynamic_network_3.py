"""行动设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 角色的情感、判断依据与实际选择】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

263936｜{"id":"C01257","source":"59.8_视角与信息差","target":"43.2_信息博弈","type":"转化","condition":"信息差驱动博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「59.8_视角与信息差」经「转化」影响「43.2_信息博弈」（条件：信息差驱动博弈）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

264565｜{"id":"C01260","source":"6.10_精神情感","target":"80.1_抗争","type":"共振链","condition":"精神情感与命运抗争相关","priority":2,"effect":"精神情感驱动命运抗争","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.10_精神情感」经「共振链」影响「80.1_抗争」（条件：精神情感与命运抗争相关）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

264764｜{"id":"C01261","source":"6.10_精神情感","target":"80.1_抗争","type":"驱动","condition":"精神情感驱动抗争；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.10_精神情感」经「驱动」影响「80.1_抗争」（条件：精神情感驱动抗争）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

265592｜{"id":"C01265","source":"6.11_生存情感","target":"70.7_忍耐","type":"触发链","condition":"生存情感伴随身体痛苦","priority":2,"effect":"生存情感驱动忍耐行为","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有身体不适且当事人选择继续行动时，依据实有任务、能力限制和可替代做法核对忍耐影响的具体行为。

265791｜{"id":"C01266","source":"6.11_生存情感","target":"70.7_忍耐","type":"驱动","condition":"生存情感驱动忍耐；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选生存事件确需要角色忍耐时，注明角色能承受的已定范围、所选动作及出现何种变化后调整。

266006｜{"id":"C01267","source":"6.1_厌恶","target":"83.5_逃避","type":"触发","condition":"厌恶源可见；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_厌恶」经「触发」影响「83.5_逃避」（条件：厌恶源可见）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

267065｜{"id":"C01272","source":"6.1_基础情感_厌恶","target":"86.2_竞争","type":"触发链","condition":"厌恶对象是竞争对手","priority":2,"effect":"厌恶强化竞争动机","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_厌恶」经「触发链」影响「86.2_竞争」（条件：厌恶对象是竞争对手）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

267861｜{"id":"C01276","source":"6.1_基础情感_恐惧","target":"83.5_逃避","type":"触发链","condition":"恐惧强度≥8且威胁在眼前","priority":1,"effect":"恐惧驱动逃避行为","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_恐惧」经「触发链」影响「83.5_逃避」（条件：恐惧强度≥8且威胁在眼前）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

268060｜{"id":"C01277","source":"6.1_基础情感_恐惧","target":"72.6_决策类型_保守","type":"触发链","condition":"恐惧强度≥6","priority":2,"effect":"恐惧驱动保守决策，选择低风险路径","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_恐惧」经「触发链」影响「72.6_决策类型_保守」（条件：恐惧强度≥6）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

268458｜{"id":"C01279","source":"6.1_基础情感_悲伤","target":"70.3_软弱","type":"触发链","condition":"悲伤强度≥7且无法释放","priority":2,"effect":"悲伤导致意志软弱，行动力下降","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_悲伤」经「触发链」影响「70.3_软弱」（条件：悲伤强度≥7且无法释放）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

268657｜{"id":"C01280","source":"6.1_基础情感_惊讶","target":"67.4_理解","type":"触发链","condition":"惊讶被触发且信息量充足","priority":2,"effect":"惊讶驱动理解过程，重新整合信息","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_惊讶」经「触发链」影响「67.4_理解」（条件：惊讶被触发且信息量充足）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

268856｜{"id":"C01281","source":"6.1_基础情感_愤怒","target":"3.5_角色冲动","type":"触发链","condition":"愤怒强度≥7","priority":1,"effect":"愤怒触发冲动行为","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_愤怒」经「触发链」影响「3.5_角色冲动」（条件：愤怒强度≥7）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

269254｜{"id":"C01283","source":"6.1_基础情感_愤怒","target":"72.1_决策类型_果断","type":"触发链","condition":"愤怒强度≥5且目标明确","priority":2,"effect":"愤怒驱动果断决策，不拖延","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_基础情感_愤怒」经「触发链」影响「72.1_决策类型_果断」（条件：愤怒强度≥5且目标明确）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

269668｜{"id":"C01285","source":"6.1_恐惧","target":"83.5_逃避","type":"触发","condition":"恐惧≥4级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_恐惧」经「触发」影响「83.5_逃避」（条件：恐惧≥4级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

269883｜{"id":"C01286","source":"6.1_恐惧","target":"68.3_悲观偏误","type":"放大","condition":"恐惧状态；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_恐惧」经「放大」影响「68.3_悲观偏误」（条件：恐惧状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

270098｜{"id":"C01287","source":"6.1_恐惧","target":"80.1_抗争","type":"冲突","condition":"恐惧+执念；且当前故事明确采用该静态关系","priority":3,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_恐惧」经「冲突」影响「80.1_抗争」（条件：恐惧+执念）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

270313｜{"id":"C01288","source":"6.1_悲伤","target":"70.3_软弱","type":"触发","condition":"悲伤≥3级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_悲伤」经「触发」影响「70.3_软弱」（条件：悲伤≥3级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

271388｜{"id":"C01293","source":"6.1_愤怒","target":"3.5_冲动","type":"触发","condition":"愤怒≥3级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_愤怒」经「触发」影响「3.5_冲动」（条件：愤怒≥3级）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

272033｜{"id":"C01296","source":"6.1_愤怒","target":"72.5_冒险决策","type":"触发","condition":"愤怒+机会；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.1_愤怒」经「触发」影响「72.5_冒险决策」（条件：愤怒+机会）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

272248｜{"id":"C01297","source":"6.2_复合情感_愧疚","target":"74.1_是非","type":"冲突链","condition":"愧疚被触发","priority":1,"effect":"愧疚挑战是非判断，驱动补救行为","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_愧疚」经「冲突链」影响「74.1_是非」（条件：愧疚被触发）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

272447｜{"id":"C01298","source":"6.2_复合情感_愧疚","target":"74.1_是非","type":"触发","condition":"违背道德；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_愧疚」经「触发」影响「74.1_是非」（条件：违背道德）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

272662｜{"id":"C01299","source":"6.2_复合情感_愧疚","target":"76.1_道德困境","type":"触发链","condition":"愧疚与道德选择相关","priority":1,"effect":"愧疚在道德困境中产生","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_愧疚」经「触发链」影响「76.1_道德困境」（条件：愧疚与道德选择相关）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

273275｜{"id":"C01302","source":"6.2_复合情感_愧疚","target":"76.1_道德困境","type":"转化","condition":"愧疚→困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_愧疚」经「转化」影响「76.1_道德困境」（条件：愧疚→困境）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

273490｜{"id":"C01303","source":"6.2_复合情感_渴望","target":"145.1_目标","type":"触发链","condition":"渴望对象明确","priority":1,"effect":"渴望转化为具体目标","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_渴望」经「触发链」影响「145.1_目标」（条件：渴望对象明确）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

274103｜{"id":"C01306","source":"6.2_复合情感_渴望","target":"145.1_目标","type":"转化","condition":"渴望→目标；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_渴望」经「转化」影响「145.1_目标」（条件：渴望→目标）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

274318｜{"id":"C01307","source":"6.2_复合情感_羞耻","target":"70.3_软弱","type":"触发链","condition":"羞耻被触发","priority":2,"effect":"羞耻导致意志软弱，回避公开行动","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_羞耻」经「触发链」影响「70.3_软弱」（条件：羞耻被触发）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

274517｜{"id":"C01308","source":"6.3_社会情感","target":"86.1_合作","type":"驱动","condition":"社会情感驱动合作；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实际社会情感影响共同任务时，依据当前人物与目标确认愿意合作的条件、可做动作及选择后果。

274732｜{"id":"C01309","source":"6.3_社会情感","target":"86.1_合作","type":"触发链","condition":"社会情感正向","priority":2,"effect":"正向社会情感驱动合作行为","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有情感促成合作时，使用双方已建立的关系、共同目标和可实施分工核对具体行为。

274931｜{"id":"C01310","source":"6.3_社会情感","target":"86.2_竞争","type":"触发链","condition":"社会情感负向","priority":2,"effect":"负向社会情感驱动竞争行为","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前社会情感确需表现为竞争时，用实际争夺目标、关系前提和可选动作核对人物回应。

275130｜{"id":"C01311","source":"6.3_社会情感","target":"86.2_竞争","type":"驱动","condition":"社会情感驱动竞争；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用社会情感推动竞争时，按真实对象、角色已有利益和能力约束写明所选办法及影响。

276372｜{"id":"C01317","source":"6.5_驱动情感","target":"3.5_冲动","type":"触发","condition":"驱动情感→冲动；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】驱动情感在所选人物确触发冲动时，以当时所知和可做动作核对他怎样直接行动、留下什么后果。

276587｜{"id":"C01318","source":"6.5_驱动情感","target":"3.5_角色冲动","type":"触发链","condition":"驱动情感强度≥6","priority":1,"effect":"驱动情感触发冲动行为","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已采用该强度条件时，用本次已设情感前值、可见触发和角色的实际做法核对冲动路径。

276786｜{"id":"C01319","source":"6.5_驱动情感","target":"145.1_目标","type":"转化","condition":"驱动情感→目标；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】情感已形成某个具体目标时，在候选中明确当事人实际想要的结果、影响选择的条件与动作。

277001｜{"id":"C01320","source":"6.5_驱动情感","target":"72.1_决策类型_果断","type":"触发链","condition":"驱动情感伴随明确目标","priority":2,"effect":"驱动情感驱动果断决策","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色已有明确目标又受实际情感驱动时，依据当时可得信息核对他为何决定此动作及可见后果。

277200｜{"id":"C01321","source":"6.5_驱动情感","target":"72.1_果断","type":"驱动","condition":"驱动情感→果断决策；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确认驱动情感支持快速决定时，按当前任务、角色能力和具体选项写明已选择的行为。

278028｜{"id":"C01325","source":"6.6_关系情感","target":"76.1_道德困境","type":"触发","condition":"关系情感产生困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】关系情感确引出本次两难时，依据实际对象、既有承诺和可做选择核对人物牺牲与可能后果。

278243｜{"id":"C01326","source":"6.7_认知情感","target":"67.4_理解","type":"转化","condition":"认知情感影响理解；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前情感确影响角色理解时，用已看到的事实、实际反应和已有解释核对哪些信息影响最终选择。

278458｜{"id":"C01327","source":"6.7_认知情感","target":"67.4_理解","type":"触发链","condition":"认知情感被触发","priority":2,"effect":"认知情感影响理解过程，情感偏向决定理解方向","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有认知情感引导理解时，为具体角色保留当时可得证据、他采用的解释及结果。

278657｜{"id":"C01328","source":"6.7_认知情感","target":"68.1_确认偏误","type":"放大链","condition":"认知情感与已有信念一致","priority":2,"effect":"认知情感放大确认偏误","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色当前情感与已有信念一致并产生偏向时，核对他采用过的真实线索、忽略的信息及实际应对。

278856｜{"id":"C01329","source":"6.7_认知情感","target":"68.1_确认偏误","type":"转化","condition":"认知情感影响偏差；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已用认知情感影响确认偏误时，以当事人能获取的支持和反对依据核对当前判断。

279899｜{"id":"C01334","source":"6.9_道德情感","target":"74.1_是非","type":"触发链","condition":"道德情感被触发","priority":1,"effect":"道德情感影响是非判断","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】道德情感确参与人物当前决定时，依据实际事实、角色已有价值及行动后果核对其判断。

280098｜{"id":"C01335","source":"6.9_道德情感","target":"74.1_是非","type":"转化","condition":"道德情感影响道德判断；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前判断已有道德情感依据时，用作品已定人物原则、可用选择和谁承担损失核对其做法。

280313｜{"id":"C01336","source":"6.9_道德情感","target":"76.1_道德困境","type":"触发链","condition":"道德情感在困境中被触发","priority":1,"effect":"道德情感在道德困境中产生","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】所选事件已构成道德困境时，写清人物所感与实有选项相连的原因，并核对各项代价。

282877｜{"id":"C01348","source":"61.1_重章","target":"47.2_对抗回合","type":"触发链","condition":"重章对抗回合多","priority":1,"effect":"重章对抗回合密集","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作的重章已指定多个对抗回合时，向实际双方分配上游确定的目标和动作，核对回合结果怎样接续。

284135｜{"id":"C01354","source":"61.2_中章","target":"47.2_对抗回合","type":"嵌套","condition":"中章对抗回合适中；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】现有中章确有对抗时，以实际冲突、适用手段和章内任务核对回合数量及关联结果。

299654｜{"id":"C01427","source":"67.2_注意","target":"68.5_可得性偏误","type":"放大","condition":"注意集中在易得信息；且当前故事明确采用该静态关系","priority":3,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当角色确实偏重容易回忆或获得的信号时，用真实信息、被忽略的依据和可做动作核对所选反应。

300084｜{"id":"C01429","source":"67.3_记忆","target":"68.1_确认偏误","type":"转化","condition":"记忆受偏误影响；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已设偏向影响记忆使用时，以实有人物回想、当下证据和已知矛盾核对判断及实际选择。

300299｜{"id":"C01430","source":"67.4_理解","target":"149.2_判断","type":"触发链","condition":"理解决定判断","priority":1,"effect":"理解决定判断","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色已对实际事件形成理解时，用目前可得的信息、已有解释及新结果核对他做出的判断。

300498｜{"id":"C01431","source":"67.4_理解","target":"149.2_判断","type":"转化","condition":"理解后输出判断；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】通过角色具体看到或听到的证据核对他怎样完成理解并选择某一判断，写清可做动作。

300928｜{"id":"C01433","source":"67.4_理解","target":"67.5_判断","type":"转化","condition":"理解完成；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有当事人能理解的事实时，以实际信息范围与相应行动核对其当前判断及依据。

301143｜{"id":"C01434","source":"67.5_判断","target":"149.2_判断","type":"转化","condition":"认知判断输出；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用角色当时证据、已形成解释及可选择做法核对如何得出具体判断。

301358｜{"id":"C01435","source":"67.5_判断","target":"73.1_决策依据","type":"转化","condition":"判断是决策依据；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当当前判断是决策依据时，写清人物据以比较的事实、所想达成的目标与真实选择。

301573｜{"id":"C01436","source":"68.1_确认偏误","target":"149.2_判断","type":"触发链","condition":"偏误影响判断","priority":1,"effect":"确认偏误影响判断","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用确认偏误影响角色判断时，以可查信念、实际支持与反对信息核对他采用的依据和后果。

301772｜{"id":"C01437","source":"68.1_确认偏误","target":"149.2_判断偏差","type":"转化","condition":"偏误影响判断；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「68.1_确认偏误」经「转化」影响「149.2_判断偏差」（条件：偏误影响判断）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

301987｜{"id":"C01438","source":"68.1_确认偏误","target":"67.4_理解扭曲","type":"扭曲","condition":"偏误激活；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，改变终点状态的解释或表现方式。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「68.1_确认偏误」经「扭曲」影响「67.4_理解扭曲」（条件：偏误激活）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

302417｜{"id":"C01440","source":"68.2_乐观偏误","target":"72.5_冒险决策","type":"触发","condition":"高估好结果；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色确高估某项实际好结果时，以已知信息、可承担风险和可做替代核对该冒险选择。

302632｜{"id":"C01441","source":"68.2_乐观偏误","target":"73.3_决策成本","type":"转化","condition":"低估风险；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对本场存在乐观偏误的已选决定，检查实际低估的成本、应对动作和仍可能的后果。

302847｜{"id":"C01442","source":"68.3_悲观偏误","target":"72.2_犹豫","type":"触发","condition":"高估坏结果；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】人物已预期实际坏结果并因此犹豫时，说明所见依据、等待后果和仍存在的替代行动。

303062｜{"id":"C01443","source":"68.3_悲观偏误","target":"70.4_动摇","type":"放大","condition":"悲观加剧动摇；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色的悲观判断确引起当前动摇时，以真实阻力及各可行选项核对暂停、改变或继续的依据。

303277｜{"id":"C01444","source":"68.4_锚定效应","target":"149.1_权衡","type":"扭曲","condition":"过度依赖第一印象；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，改变终点状态的解释或表现方式。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色确过度依赖本场第一项信息时，用实际起点、后来取得的证据与所选动作核对权衡怎样被改变。

303492｜{"id":"C01445","source":"68.4_锚定效应","target":"73.1_决策依据","type":"转化","condition":"锚定影响决策；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前判断采用既有锚点时，记录其具体内容、实际替代依据和角色用什么做出决定。

303707｜{"id":"C01446","source":"68.5_可得性偏误","target":"67.2_注意","type":"放大","condition":"容易回忆的信息被高估；且当前故事明确采用该静态关系","priority":1,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有角色偏重易取得的信号时，写清他实际注意的对象、可查但未选的依据和后续选择。

303922｜{"id":"C01447","source":"68.5_可得性偏误","target":"72.5_冒险决策","type":"触发","condition":"近期成功案例易得；且当前故事明确采用该静态关系","priority":3,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当近期成功例子确使人物冒险时，用该人能回想的实有事件及当前风险核对其判断和可行应对。

304352｜{"id":"C01449","source":"68.6_后见之明","target":"68.1_确认偏误","type":"放大","condition":"后见之明强化确认偏误；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】人物在结果出现后按原信念选择证据时，核对他实际上见过什么、怎样重新解释及由此选择的行动。

304782｜{"id":"C01451","source":"68.7_自利偏误","target":"75.1_利己","type":"放大","condition":"自利偏误强化利己；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已有人物因自利偏向选择利益时，沿项目给定目标和事实核对他对成本与所获的判断。

304997｜{"id":"C01452","source":"68.8_沉没成本谬误","target":"73.3_决策成本","type":"转化","condition":"已投入太多难放弃；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当角色因已经付出的成本难以退出时，把可查投入、现在可做选择及会增加的成本对应到本次决定。

305642｜{"id":"C01455","source":"68.9_认知失调","target":"70.4_动摇","type":"触发","condition":"失调导致动摇；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前冲突使人物已有判断动摇时，用所见事实、不同解释及可做选项核对实际暂停或改变的行为。

305857｜{"id":"C01456","source":"69.1_心智模型","target":"149.1_权衡","type":"嵌套链","condition":"心智模型决定权衡","priority":1,"effect":"心智模型决定权衡方式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已定角色如何解释世界时，以真实目标与可得信号核对他为何给某些选项更大分量及最终取舍。

306056｜{"id":"C01457","source":"69.1_心智模型","target":"149.2_判断","type":"约束","condition":"模型决定判断；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在当事人已有心智模型下，说明具体事实如何被理解、认为什么可信及选择了哪项应对。

306271｜{"id":"C01458","source":"69.1_心智模型","target":"67.4_理解","type":"约束","condition":"模型决定理解方式；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前人物已有稳定解释框架时，核对它影响这次经历理解的实际方式、所用线索和行动结果。

306916｜{"id":"C01461","source":"69.2_心智模型更新","target":"149.2_判断","type":"转化","condition":"更新后判断改变；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】人物已经形成更新后的理解时，在后续实际选择中使用新证据核对其判断与决策的差异。

307346｜{"id":"C01463","source":"69.3_心智模型固化","target":"68.1_确认偏误","type":"放大","condition":"固化强化确认偏误；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知旧信念固化影响此轮决策时，使用角色当前能获取的支持与反对事实比较其偏向及实际行动。

308620｜{"id":"C01469","source":"69.6_信念系统","target":"74.1_是非","type":"嵌套","condition":"信念决定是非；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按本作该角色已确定的信念和实际情势核对其价值判断、可做选择与他能承受的结果。

308835｜{"id":"C01470","source":"69.6_信念系统","target":"75.1_利己","type":"嵌套","condition":"信念决定利己；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当既有信念确影响角色考虑自身利益时，使用真实利害、角色已定原则和现有选项核对其做法。

310905｜{"id":"C01480","source":"7.3_情感在冲突中","target":"43.1_资源争夺","type":"驱动","condition":"情感驱动争夺；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有情感确推动当前资源争夺时，用人物所求、实际资源、对方条件与能执行的动作核对选择。

311120｜{"id":"C01481","source":"7.3_情感在冲突中","target":"150.3_博弈回合","type":"嵌套","condition":"情感是博弈工具；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前情感确改变一轮博弈时，用实际各方、人物动机、可做动作和回应核对本轮变化。

311335｜{"id":"C01482","source":"7.3_情感在冲突中","target":"43.2_信息博弈","type":"转化","condition":"情感影响博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有情感参与信息博弈时，以当事人确知的事实、实际偏向和可选应对核对信息的取得或保留。

311550｜{"id":"C01483","source":"7.3_情感在冲突中的使用","target":"150_人性博弈","type":"触发链","condition":"情感参与人性博弈","priority":1,"effect":"情感是人性博弈的核心工具","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已选情感影响当事人博弈时，用项目实有关系、当前目的和具体行动核对情感在本轮的作用。

311749｜{"id":"C01484","source":"7.3_情感在冲突中的使用","target":"43.1_资源争夺","type":"触发链","condition":"情感驱动资源争夺","priority":1,"effect":"情感是资源争夺的驱动力量","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】现有情感确推动同一资源的争夺时，按所选人物和实际阻碍安排做法、安全条件与候选后果。

311948｜{"id":"C01485","source":"7.3_情感在冲突中的使用","target":"43.2_信息博弈","type":"触发链","condition":"情感影响信息博弈","priority":1,"effect":"情感影响信息博弈中的策略选择","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色因已有感受改变信息策略时，依据实际知情状态和真实对象核对具体选择、所得信息及可见回应。

312147｜{"id":"C01486","source":"7.3_情感在冲突中的使用","target":"43.4_道德困境","type":"触发链","condition":"情感在道德困境中起作用","priority":1,"effect":"情感是道德困境的核心构成","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本次道德困境已经设定具体情感时，把它与真实义务、可行选择和相应代价关联起来。"""
