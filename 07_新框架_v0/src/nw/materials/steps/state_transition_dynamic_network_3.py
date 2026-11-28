"""状态变化步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 意志、代价、身体精神、知情与状态追踪】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

318325｜{"id":"C01516","source":"70.1_坚韧","target":"8.1_疲惫","type":"抑制","condition":"坚韧≥7；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，降低终点状态的强度或可见性。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「70.1_坚韧」经「抑制」影响「8.1_疲惫」（条件：坚韧≥7）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

318540｜{"id":"C01517","source":"70.1_坚韧","target":"8.1_饥饿","type":"抑制","condition":"坚韧≥7；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，降低终点状态的强度或可见性。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「70.1_坚韧」经「抑制」影响「8.1_饥饿」（条件：坚韧≥7）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

318970｜{"id":"C01519","source":"70.1_坚韧","target":"8.1_身体状态","type":"抑制链","condition":"坚韧高时抑制负面状态影响","priority":2,"effect":"坚韧抑制身体状态负面影响","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品已确认坚韧能改变所选负面状态的实际影响时，对照身体前值、边界和可观察行动核对变化程度及持续条件。

319814｜{"id":"C01523","source":"70.3_软弱","target":"4.5_成长中断","type":"转化","condition":"软弱导致停滞；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前事件已使人物成长停滞时，依具体受阻事项、前后值及可见行动核对中断开始和可继续条件。

320029｜{"id":"C01524","source":"70.3_软弱","target":"8.2_焦虑","type":"放大","condition":"软弱+压力；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「70.3_软弱」经「放大」影响「8.2_焦虑」（条件：软弱+压力）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

320459｜{"id":"C01526","source":"70.4_动摇","target":"8.2_焦虑","type":"转化","condition":"动摇导致焦虑；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「70.4_动摇」经「转化」影响「8.2_焦虑」（条件：动摇导致焦虑）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

321104｜{"id":"C01529","source":"70.7_忍耐","target":"8.1_疲惫","type":"抑制","condition":"忍耐激活；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，降低终点状态的强度或可见性。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「70.7_忍耐」经「抑制」影响「8.1_疲惫」（条件：忍耐激活）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

321319｜{"id":"C01530","source":"70.7_忍耐","target":"8.1_饥饿","type":"抑制","condition":"忍耐激活；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，降低终点状态的强度或可见性。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「70.7_忍耐」经「抑制」影响「8.1_饥饿」（条件：忍耐激活）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

321948｜{"id":"C01533","source":"71.1_意志强度","target":"71.2_意志韧性","type":"转化","condition":"强度影响韧性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有事件影响意志韧性时，用角色当时强度、实际触发及行为前后差异核对续写所需状态。

323636｜{"id":"C01541","source":"72.3_冲动决策","target":"118.1_代价","type":"绑定","condition":"冲动产生代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】冲动决定已实际付出代价时，用前值、所选动作及可查损失记录改变和后续限制。

326614｜{"id":"C01555","source":"73.3_决策成本","target":"8.2_焦虑","type":"转化","condition":"高成本引发焦虑；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「73.3_决策成本」经「转化」影响「8.2_焦虑」（条件：高成本引发焦虑）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

326829｜{"id":"C01556","source":"73.3_决策成本","target":"118.1_代价","type":"转化","condition":"决策成本是代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当人物实际承担决策成本时，在本作所定尺度记录发生时间、实有损失、受影响对象及其后续作用。

332355｜{"id":"C01582","source":"75.2_利他","target":"5.8_情感债务","type":"转化","condition":"利他产生债务；且当前故事明确采用该静态关系","priority":3,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色实际帮助他人且本作确认形成情感债务时，用双方、具体行为和关系前后值记录关系变化。

333430｜{"id":"C01587","source":"76.1_道德困境","target":"118.1_代价","type":"绑定","condition":"困境产生代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前两难已产生实际支付时，记录谁承担何种损失、发生时点、可见前后值及后续影响。

334935｜{"id":"C01594","source":"76.3_困境不可逆","target":"118.1_代价","type":"绑定","condition":"不可逆产生代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前困境已造成不可回撤的损失时，对照原状态、所选动作和已发生后果记录支付及持续影响。

335150｜{"id":"C01595","source":"76.6_代价追踪","target":"118.1_代价","type":"绑定","condition":"道德代价需追踪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选判断确有持续道德代价时，以实际事件和受影响者记录何时支付、失去什么及以后须承接哪一状态。

335580｜{"id":"C01597","source":"76.7_道德灰度","target":"149.3_立场","type":"触发链","condition":"灰度影响立场","priority":1,"effect":"道德灰度影响立场","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】道德灰度确在当前事件改变人物立场时，以真实对象、具体判断与可看到的前后行为记录变化。

337714｜{"id":"C01607","source":"77.1_时间紧迫","target":"8.2_焦虑","type":"触发","condition":"紧迫引发焦虑；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「77.1_时间紧迫」经「触发」影响「8.2_焦虑」（条件：紧迫引发焦虑）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

338988｜{"id":"C01613","source":"77.3_时间漫长","target":"8.2_精神状态","type":"转化","condition":"漫长影响精神；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已设漫长感改变人物精神状态时，依具体经历、前值及可查反应记录范围和延续。

339203｜{"id":"C01614","source":"77.3_漫长","target":"8.2_精神状态","type":"触发链","condition":"漫长状态","priority":2,"effect":"漫长感影响精神状态","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前漫长体验确有精神影响时，按本作时间、状态前后与可观察行为核对改变。

339832｜{"id":"C01617","source":"77.5_时间停滞","target":"69.4_心智模型破裂","type":"触发","condition":"停滞触发模型破裂；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有停滞经历冲击人物原有理解时，用实有触发、旧判断和后来可见行为核对模型变化。

342611｜{"id":"C01630","source":"8.1_受伤","target":"10.1_能量流失","type":"转化","condition":"持续失血；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_受伤」经「转化」影响「10.1_能量流失」（条件：持续失血）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

342826｜{"id":"C01631","source":"8.1_受伤","target":"8.6_负面状态","type":"触发","condition":"伤口未处理；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_受伤」经「触发」影响「8.6_负面状态」（条件：伤口未处理）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

343686｜{"id":"C01635","source":"8.1_疲惫","target":"8.2_精神萎靡","type":"触发","condition":"≥8小时；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疲惫」经「触发」影响「8.2_精神萎靡」（条件：≥8小时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

344546｜{"id":"C01639","source":"8.1_疾病","target":"8.2_精神萎靡","type":"触发","condition":"疾病状态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_疾病」经「触发」影响「8.2_精神萎靡」（条件：疾病状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

345191｜{"id":"C01642","source":"8.1_身体状态_饥饿","target":"145.3_心理","type":"触发链","condition":"饥饿持续≥12小时","priority":1,"effect":"心理状态扭曲，自我控制能力下降","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「触发链」影响「145.3_心理」（条件：饥饿持续≥12小时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

346385｜{"id":"C01648","source":"8.1_身体状态_饥饿","target":"9.1_状态叠加","type":"放大链","condition":"饥饿+疲惫+焦虑同时存在","priority":1,"effect":"决策能力严重受损，状态过载风险","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「放大链」影响「9.1_状态叠加」（条件：饥饿+疲惫+焦虑同时存在）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

347380｜{"id":"C01653","source":"8.1_身体状态_饥饿","target":"70.1_坚韧","type":"抑制链","condition":"饥饿程度≤2级且角色意志强度≥7","priority":2,"effect":"饥饿的决策影响被坚韧意志减弱","direction":"双向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「抑制链」影响「70.1_坚韧」（条件：饥饿程度≤2级且角色意志强度≥7）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

347778｜{"id":"C01655","source":"8.1_身体状态_饥饿","target":"8.2_精神状态_焦虑","type":"触发链","condition":"饥饿持续≥4小时","priority":2,"effect":"焦虑加剧，信息处理能力下降","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_身体状态_饥饿」经「触发链」影响「8.2_精神状态_焦虑」（条件：饥饿持续≥4小时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

349267｜{"id":"C01662","source":"8.1_饥饿","target":"8.2_焦虑","type":"触发","condition":"饥饿≥6小时；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「触发」影响「8.2_焦虑」（条件：饥饿≥6小时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

349912｜{"id":"C01665","source":"8.1_饥饿","target":"70.1_坚韧","type":"抑制","condition":"坚韧≥7；且当前故事明确采用该静态关系","priority":4,"effect":"当起点成立时，降低终点状态的强度或可见性。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.1_饥饿」经「抑制」影响「70.1_坚韧」（条件：坚韧≥7）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

350557｜{"id":"C01668","source":"8.2_亢奋","target":"8.1_能量消耗","type":"转化","condition":"亢奋消耗能量；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_亢奋」经「转化」影响「8.1_能量消耗」（条件：亢奋消耗能量）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

350772｜{"id":"C01669","source":"8.2_恐惧","target":"70.4_动摇","type":"触发","condition":"恐惧源可见；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_恐惧」经「触发」影响「70.4_动摇」（条件：恐惧源可见）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

352492｜{"id":"C01677","source":"8.2_抑郁","target":"4.5_成长中断","type":"触发","condition":"抑郁导致停滞；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_抑郁」经「触发」影响「4.5_成长中断」（条件：抑郁导致停滞）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

353567｜{"id":"C01682","source":"8.2_焦虑","target":"73.3_决策成本","type":"转化","condition":"持续；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_焦虑」经「转化」影响「73.3_决策成本」（条件：持续）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

354379｜{"id":"C01686","source":"8.2_精神状态_焦虑","target":"8.1_身体状态","type":"触发链","condition":"焦虑持续≥24小时","priority":1,"effect":"焦虑导致身体状态恶化，形成身心负循环","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.2_精神状态_焦虑」经「触发链」影响「8.1_身体状态」（条件：焦虑持续≥24小时）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

355406｜{"id":"C01691","source":"8.3_能量匮乏","target":"16.3_透支","type":"触发","condition":"能量<20%；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量匮乏」经「触发」影响「16.3_透支」（条件：能量<20%）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

355836｜{"id":"C01693","source":"8.3_能量匮乏","target":"8.1_疲惫","type":"触发","condition":"能量匮乏导致疲惫；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量匮乏」经「触发」影响「8.1_疲惫」（条件：能量匮乏导致疲惫）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

356051｜{"id":"C01694","source":"8.3_能量状态_充盈","target":"8.5_增益状态","type":"触发链","condition":"能量高于90%","priority":2,"effect":"能量充盈转化为增益状态，能力发挥提升","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量状态_充盈」经「触发链」影响「8.5_增益状态」（条件：能量高于90%）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

356240｜{"id":"C01695","source":"8.3_能量状态_耗尽","target":"16.3_透支规则","type":"转化链","condition":"能量低于5%","priority":1,"effect":"能量耗尽触发透支状态，进入危险阈值","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量状态_耗尽」经「转化链」影响「16.3_透支规则」（条件：能量低于5%）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

356429｜{"id":"C01696","source":"8.3_能量状态_耗尽","target":"8.1_身体状态_疲惫","type":"触发链","condition":"能量低于10%","priority":1,"effect":"能量耗尽导致身体疲惫，行动能力下降","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量状态_耗尽」经「触发链」影响「8.1_身体状态_疲惫」（条件：能量低于10%）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

356618｜{"id":"C01697","source":"8.3_能量状态_耗尽","target":"8.2_精神状态_焦虑","type":"触发链","condition":"能量低于10%且处于危险环境","priority":2,"effect":"能量耗尽触发焦虑，担心无法应对威胁","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.3_能量状态_耗尽」经「触发链」影响「8.2_精神状态_焦虑」（条件：能量低于10%且处于危险环境）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

357237｜{"id":"C01700","source":"8.4_关系状态_紧张","target":"5.9_信任光谱","type":"转化","condition":"紧张→信任下降；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.4_关系状态_紧张」经「转化」影响「5.9_信任光谱」（条件：紧张→信任下降）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

358527｜{"id":"C01706","source":"8.6_中毒","target":"8.1_受伤","type":"触发","condition":"中毒→受伤；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.6_中毒」经「触发」影响「8.1_受伤」（条件：中毒→受伤）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

360215｜{"id":"C01714","source":"80.2_接受","target":"69.2_心智模型更新","type":"转化","condition":"接受=认知更新；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色确接受某项本作事实时，用原理解、实际触发与后来可辨决定核对心智模型前后如何改变。

360860｜{"id":"C01717","source":"80.3_逃避","target":"8.2_恐惧","type":"转化","condition":"逃避源于恐惧；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「80.3_逃避」经「转化」影响「8.2_恐惧」（条件：逃避源于恐惧）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

366585｜{"id":"C01744","source":"83.4_适应","target":"8.1_身体状态","type":"转化","condition":"适应影响身体；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有适应行为实际改变身体状态时，用本作条件、真实动作及前后值核对改变及延续。

367015｜{"id":"C01746","source":"83.5_逃避","target":"8.1_身体状态","type":"转化","condition":"逃避影响身体；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定逃避确使身体状态发生变化时，以实际动作、环境和可见前后值记录后果。

367230｜{"id":"C01747","source":"83.5_逃避","target":"8.1_身体状态","type":"触发链","condition":"逃避行为","priority":2,"effect":"逃避影响身体状态","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已设逃避动作产生身体影响时，依据所选路径、实际负荷和前后反应确认变化及其持续条件。

367429｜{"id":"C01748","source":"83.5_逃避","target":"8.2_精神状态","type":"转化","condition":"逃避影响精神；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场逃避确改变人物精神状态时，用真实触发、前值与其后来可辨行为核对差异。

369762｜{"id":"C01759","source":"84.3_使用","target":"122.9_代价绑定","type":"绑定","condition":"使用有代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】一次使用已产生代价时，用本作物件、所选动作及前后值记录实际支付、持续限制和后场承接。

370821｜{"id":"C01764","source":"84.5_存储","target":"125.1_资源库","type":"转化","condition":"存储是资源库；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前资源确实被存入某处时，记录具体对象、可查数量、存储前后、实际位置及有权取用的人。

372095｜{"id":"C01770","source":"85.2_告知","target":"5.7_信息不对称","type":"转化","condition":"告知减少不对称；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实际告知减少特定两人信息差时，用已经交付的内容及获知者前后值核对变化。

372310｜{"id":"C01771","source":"85.3_隐瞒","target":"5.7_信息不对称","type":"触发链","condition":"隐瞒制造不对称","priority":1,"effect":"隐瞒制造信息不对称","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】某人隐瞒已确实维持或加大信息差时，按具体事实、实际双方和可查来源记录谁现在知道什么。

372509｜{"id":"C01772","source":"85.3_隐瞒","target":"5.7_信息不对称","type":"转化","condition":"隐瞒制造不对称；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作所选隐瞒已产生信息不对称时，记录实际未透露内容、相关角色前后知识及其持续条件。

373369｜{"id":"C01776","source":"85.4_欺骗","target":"5.7_信息不对称","type":"转化","condition":"欺骗制造不对称；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选定情节确使人物获得错误理解时，在状态里区分所述内容、所信解释及可回查的真实事实。

374444｜{"id":"C01781","source":"86.1_合作","target":"5.3_情感关系","type":"触发链","condition":"合作影响情感","priority":1,"effect":"合作影响情感关系","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】实际合作影响情感关系时，用既有双方、具体共同动作及前后表现确认变化。

375073｜{"id":"C01784","source":"86.1_合作","target":"5.3_情感关系","type":"转化","condition":"合作影响关系；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】选择的合作事件确改变关系时，依据前值、实际完成动作和各自结果核对后值及继续条件。

376976｜{"id":"C01793","source":"86.4_同盟","target":"5.3_情感关系","type":"触发链","condition":"同盟影响情感","priority":1,"effect":"同盟影响情感关系","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已形成同盟确影响人物情感关系时，用真实承诺、可见行动与情感关系前后值核对变化。

377390｜{"id":"C01795","source":"86.4_同盟","target":"5.3_情感关系","type":"转化","condition":"同盟影响关系；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选同盟事件确改变情感关系时，核对双方既有态度、所付代价、可见表现和后续承接。

378234｜{"id":"C01799","source":"86.6_立场确定","target":"5.11_立场","type":"转化","condition":"确定立场；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色已经通过可见行动确定立场时，对照前值、实际对象与表态或行为记录后值和持续边界。

378664｜{"id":"C01801","source":"9.1_状态叠加","target":"8.1_身体状态","type":"约束","condition":"叠加规则适用；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用身体状态叠加且实际并存时，按各状态前值、同时发生的限制和后果核对身体变化。

378879｜{"id":"C01802","source":"9.1_状态叠加","target":"8.2_精神状态","type":"约束","condition":"叠加规则适用；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前多个精神状态有实际证据时，以原有触发和选定事件记录仍生效的限制、范围和前后反应。

379309｜{"id":"C01804","source":"9.1_状态叠加规则","target":"8.1_身体状态","type":"触发链","condition":"多个状态同时存在","priority":1,"effect":"状态叠加影响身体状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】若项目已给实际身体状态同时发生的证据，核对各自触发、实际症状或行为限制及变化结果。

379508｜{"id":"C01805","source":"9.1_状态叠加规则","target":"8.2_精神状态","type":"触发链","condition":"多个状态同时存在","priority":1,"effect":"状态叠加影响精神状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作出现多项已确立精神状态时，用具体表现、前后值和所选触发核对并存及持续影响。

380535｜{"id":"C01810","source":"9.2_状态化解规则","target":"8.6_中毒_负面状态","type":"触发链","condition":"负面状态存在","priority":1,"effect":"负面状态需要被化解","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】情节已有负面状态实际化解时，按本作已确认的状态值与所选事件核对发生条件、前后差异及仍存限制。

380933｜{"id":"C01812","source":"9.2_状态化解规则","target":"9.3_状态自然变化规则","type":"嵌套链","condition":"化解可以通过自然变化","priority":2,"effect":"自然变化是化解的一种方式","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作明确某项状态会随具体时间自然减弱时，按已有时间、前后状态与可见反应核对化解持续。

381132｜{"id":"C01813","source":"9.2_状态化解规则","target":"9.4_状态事件触发变化","type":"嵌套链","condition":"化解可以通过事件触发","priority":2,"effect":"事件触发是化解的一种方式","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选事件使实际状态化解时，用具体触发、已证前后变化及后续可用行动记录结果。

381331｜{"id":"C01814","source":"9.3_状态自然变化","target":"8.1_身体状态","type":"演化","condition":"随时间变化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】有实际身体状态随故事时间变化时，以时间标记、初始值和已出现表现核对不同时点的状态。

381960｜{"id":"C01817","source":"9.4_事件触发状态变化","target":"8.1_身体状态","type":"转化","condition":"事件→状态变化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前选定事件已改变身体状态时，按实际对象、触发、前值与可查反应确定后值。

382390｜{"id":"C01819","source":"9.4_状态事件触发变化","target":"8.1_身体状态","type":"触发链","condition":"事件触发身体状态变化","priority":1,"effect":"事件触发身体状态变化","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目现有事件引出身体变化时，使用真实行动、触发与可查反应确认前后及延续。

382589｜{"id":"C01820","source":"9.4_状态事件触发变化","target":"8.2_精神状态","type":"触发链","condition":"事件触发精神状态变化","priority":1,"effect":"事件触发精神状态变化","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】所选事件确影响角色精神状态时，用前值、因果与可辨言行记录实际变化和可续写范围。

382987｜{"id":"C01822","source":"9.5_状态追踪","target":"118.1_代价追踪","type":"转化","condition":"状态追踪类似代价追踪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本条用于从已接受的前后值和段落中查找实际代价证据。原附通用状态转化仅作追溯，代价发生依据本场实际选择和结果。

383417｜{"id":"C01824","source":"9.5_状态追踪表","target":"118.1_代价追踪","type":"触发链","condition":"状态需要被追踪","priority":2,"effect":"状态追踪是代价追踪的一部分","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】采用本作已设状态追踪时，把已证状态、实际触发、前后值和支付记录对应到同一事件，供下游核对延续。"""
