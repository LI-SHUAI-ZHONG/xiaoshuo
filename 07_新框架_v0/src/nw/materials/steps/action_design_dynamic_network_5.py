"""行动设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 环境、资源、信息交互及关系行动】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

357022｜{"id":"C01699","source":"8.4_关系状态_亲密","target":"86.1_合作","type":"驱动","condition":"亲密驱动合作；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.4_关系状态_亲密」经「驱动」影响「86.1_合作」（条件：亲密驱动合作）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

357667｜{"id":"C01702","source":"8.5_增益状态_专注","target":"72.1_果断","type":"放大","condition":"专注状态；且当前故事明确采用该静态关系","priority":1,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.5_增益状态_专注」经「放大」影响「72.1_果断」（条件：专注状态）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

357882｜{"id":"C01703","source":"8.5_增益状态_专注","target":"10.3_技巧","type":"放大","condition":"专注提升技巧；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「8.5_增益状态_专注」经「放大」影响「10.3_技巧」（条件：专注提升技巧）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

358097｜{"id":"C01704","source":"8.6_中毒","target":"9.2_化解","type":"约束","condition":"中毒需化解；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已设该角色面临中毒负面状态时，依据本作既有状态规则与人物现有能力核对实际可选择的化解动作。

358312｜{"id":"C01705","source":"8.6_中毒","target":"72.3_冲动","type":"触发","condition":"中毒削弱判断；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目明确当前负面状态确影响人物判断时，以已设状态、其所知及可做动作核对冲动选择及后果。

360645｜{"id":"C01716","source":"80.3_逃避","target":"83.5_逃避","type":"转化","condition":"命运逃避=环境逃避；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已设人物因处境选择逃避时，用实际目标、对手或环境限制以及现有路径核对具体做法和后果。

362994｜{"id":"C01727","source":"82.3_岔路与回撤","target":"42.6_岔路","type":"转化","condition":"岔路是命运选择；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品给角色实际岔路和回撤条件时，按角色所知、真实选项及已付成本核对所选路线。

363408｜{"id":"C01729","source":"82.3_岔路与回撤","target":"73.1_决策依据","type":"嵌套","condition":"岔路需决策；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前确有岔路需要判断时，使用当事人已取得事实、可执行选择和各自结果写明决定依据。

364467｜{"id":"C01734","source":"83.1_探索","target":"84.1_采集","type":"触发链","condition":"探索后可采集","priority":1,"effect":"探索后采集资源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有探索结果提供可采对象时，依现有角色能力、实际地点及作品规则核对可采取的采集动作。

364666｜{"id":"C01735","source":"83.1_探索","target":"84.1_采集","type":"转化","condition":"探索→采集；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选探索通往既定采集时，把真实入口、角色能取得的物件及相关限制对应到操作顺序。

364881｜{"id":"C01736","source":"83.1_探索","target":"145.1_目标","type":"绑定","condition":"探索需目标；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】探索已确立实际目标时，在候选标明要找什么、凭什么确认及遇到实际阻碍如何应对。

365311｜{"id":"C01738","source":"83.1_探索","target":"85.1_询问","type":"转化","condition":"探索→询问；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品中探索确需询问时，按可接触对象、该人真知道的内容及角色目标核对询问与结果。

365526｜{"id":"C01739","source":"83.2_利用","target":"84.2_加工","type":"触发链","condition":"利用后加工","priority":1,"effect":"利用后加工资源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色拟利用确有的资源并需要加工时，依本作工艺、工具和已知材料核对可做的处理。

365725｜{"id":"C01740","source":"83.2_利用","target":"84.2_加工","type":"转化","condition":"利用→加工；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前利用目标需用加工实现时，在候选写明实际投入、工序、限制及预期产物。

365940｜{"id":"C01741","source":"83.2_利用","target":"145.4_动作","type":"转化","condition":"利用=动作；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】要表现角色怎样利用现有对象时，以其实际能力和本作明确用途落实具体动作、应对与结果。

366155｜{"id":"C01742","source":"83.3_改造","target":"84.2_加工","type":"转化","condition":"改造涉及加工；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已有改造目标与加工条件时，以真实材料、当前对象及角色能力核对操作和所得变化。

367644｜{"id":"C01749","source":"83.6_对抗","target":"86.3_对抗","type":"转化","condition":"环境对抗=社会对抗；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作选定环境对抗或人物对抗时，按实际对象、角色能力和具体阻碍核对本轮所用动作及回应。

367859｜{"id":"C01750","source":"83.6_对抗","target":"47.2_对抗回合","type":"嵌套","condition":"对抗需回合；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前对抗采用多个回合时，把各方真实动作、可行反应和局势变化连成连续步骤。

368074｜{"id":"C01751","source":"84.1_采集","target":"27.2_资源获取","type":"嵌套链","condition":"采集是获取方式","priority":1,"effect":"采集是资源获取方式之一","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品以采集取得具体资源时，依据已知位置、可用工具和角色能力核对行动条件及所得。

368273｜{"id":"C01752","source":"84.1_采集","target":"27.2_资源获取","type":"转化","condition":"采集=获取；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已选择的采集方式，保持实际地点、对象和可见结果，为当前目标核对能取得什么。

368488｜{"id":"C01753","source":"84.1_采集","target":"84.2_加工","type":"转化","condition":"采集→加工；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】现有采集结果可供加工时，按真实材料、项目条件及操作顺序安排由获得到初步处理的候选。

368918｜{"id":"C01755","source":"84.2_加工","target":"40.1_制造","type":"嵌套链","condition":"加工是制造的一部分","priority":1,"effect":"加工是制造的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前制造需要加工时，以已定材料、可用工艺和实际角色能力核对这个步骤的输入与候选产物。

369117｜{"id":"C01756","source":"84.2_加工","target":"84.3_使用","type":"转化","condition":"加工→使用；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有加工成果可在本作使用时，依已知功能、角色许可和操作条件确认可用做法及取得结果。

369332｜{"id":"C01757","source":"84.2_加工","target":"40.1_制造","type":"嵌套","condition":"加工是制造一部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用加工属于制造过程时，按实有制品、操作顺序和前置条件核对当前工序作用。

369547｜{"id":"C01758","source":"84.3_使用","target":"145.4_动作","type":"转化","condition":"使用=动作；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色实际使用选定对象时，用现有用途、接触方式和角色能力写明具体动作及发生的结果。

370176｜{"id":"C01761","source":"84.4_交易","target":"86.5_交易","type":"转化","condition":"资源交易=社会交易；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前交换确是资源交易和社会互动时，用真实双方、各自需求和可交付条件核对本轮成交或拒绝。

371251｜{"id":"C01766","source":"85.1_询问","target":"85.2_告知","type":"触发链","condition":"询问后被告知","priority":1,"effect":"询问后获得告知","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】人物为取得本作实际信息而询问时，用双方已知事实、明确对象及答复条件核对会获得什么。

371450｜{"id":"C01767","source":"85.1_询问","target":"85.2_告知","type":"转化","condition":"询问→告知；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次询问已引出具体告知时，记录所问内容、对方实有所知和可核的答复范围。

371665｜{"id":"C01768","source":"85.1_询问","target":"43.2_信息博弈","type":"嵌套","condition":"询问是博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已选询问作为信息博弈的一环时，用双方各自所知、询问目的和可能回应核对候选行动。

371880｜{"id":"C01769","source":"85.2_告知","target":"85.3_隐瞒","type":"冲突","condition":"告知 vs 隐瞒；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，产生需要处理的状态冲突。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】情节已有告知与隐瞒之间的选择时，依人物能接触的具体事实和真实利益核对会透露多少、谁得到什么。

372724｜{"id":"C01773","source":"85.3_隐瞒","target":"85.4_欺骗","type":"演化","condition":"隐瞒→欺骗；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前人物的真实选择已由隐瞒发展为对他人给出不同解释时，以项目真实事实、角色可作行为和预定后果核对变化。

372939｜{"id":"C01774","source":"85.3_隐瞒","target":"43.2_信息博弈","type":"嵌套","condition":"隐瞒是博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场用隐瞒作为已选博弈行动时，依据该人实际知道的事实、对手立场和可见回应核对信息变化。

373154｜{"id":"C01775","source":"85.4_欺骗","target":"43.2_信息博弈","type":"嵌套","condition":"欺骗是博弈；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前已设角色在博弈中提供错误信息时，以项目内的真实事实、所选行动和其他人的实际反应核对结果。

374229｜{"id":"C01780","source":"85.6_求证","target":"85.2_告知","type":"转化","condition":"求证→告知；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已选求证促成告知时，以实际证据、可接触对象及其真实所知写明求证的动作和可得回应。

374858｜{"id":"C01783","source":"86.1_合作","target":"150.3_博弈回合","type":"嵌套","condition":"合作是博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品把合作放在一轮人物博弈中时，用实有任务、各自收益和可执行承诺核对该轮选择与结果。

375917｜{"id":"C01788","source":"86.2_竞争","target":"150.3_博弈回合","type":"嵌套","condition":"竞争是博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前竞争采用博弈回合时，用具体双方、各自所求及可选实做动作核对回应与结果。

376331｜{"id":"C01790","source":"86.3_对抗","target":"47.2_对抗回合","type":"嵌套","condition":"对抗需回合；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以本作确有的对抗场景为前置，逐轮安排双方可做动作、回应和实有局势变化。

376546｜{"id":"C01791","source":"86.3_对抗","target":"150.3_博弈回合","type":"嵌套","condition":"对抗是博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有对抗作为博弈的一轮时，按实际目标、对手能做的反应和本轮可确认结果设计行动。

377175｜{"id":"C01794","source":"86.4_同盟","target":"86.1_合作","type":"转化","condition":"同盟=合作；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目现有同盟支持某项合作时，以双方实际分工、当前共同目标及仍生效的条件选择动作。

377804｜{"id":"C01797","source":"86.5_交易","target":"84.4_交易","type":"转化","condition":"社会交易=资源交易；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前社会交易确交换某项实有资源时，用各方可交付内容、得到的对象和既定条件核对选择。

378019｜{"id":"C01798","source":"86.5_交易","target":"150.3_博弈回合","type":"嵌套","condition":"交易是博弈；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】交易已选作博弈回合时，以双方的实际需求、可接受成交条件和真实回应核对该轮结果。

379094｜{"id":"C01803","source":"9.1_状态叠加","target":"68.1_确认偏误","type":"放大","condition":"叠加放大偏差；且当前故事明确采用该静态关系","priority":2,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】根据本作已选状态叠加、当前人物所知和真实应对，核对他采用或忽略了什么证据及所选行动。

379707｜{"id":"C01806","source":"9.1_状态叠加规则","target":"68.1_确认偏误","type":"放大链","condition":"状态叠加超过3种","priority":2,"effect":"状态叠加放大认知偏差","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有原叠加条件及同一事件中的多个确证状态时，用所见事实和可选行为核对偏误实际影响的判断。

379906｜{"id":"C01807","source":"9.1_状态叠加规则","target":"72.3_决策类型_冲动","type":"放大链","condition":"状态叠加超过3种","priority":2,"effect":"状态叠加放大冲动倾向","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作确采用原叠加阈值并已满足时，以角色真实受限、可用选项与已经发生的冲动行为核对适用。"""
