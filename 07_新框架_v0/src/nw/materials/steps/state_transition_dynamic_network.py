"""状态变化步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 关系演变及能量的前后差异】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

1450｜{"id":"C00007","source":"1.2_重要配角","target":"121.14_关系演变","type":"演化","condition":"全书变化；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有所选事件改变重要配角关系时，按当事人、前关系、实际触发和后续可见差异确认能保存哪项变化。

5105｜{"id":"C00024","source":"10.1_能量总量","target":"12.10_能量临界值","type":"触发链","condition":"能量达到临界值","priority":1,"effect":"能量总量影响临界值","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色实际能量变化达到本作已定临界条件时，对照前值、来源、阈值及可观察变化保留候选结果。

5509｜{"id":"C00026","source":"10.1_能量总量","target":"16.1_消耗速率","type":"触发链","condition":"能量被消耗","priority":1,"effect":"能量总量影响消耗速率","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】选中行动已实际消耗能量时，按本作规定的计量时间、用法与前后量核对消耗速率和剩余状态。

5698｜{"id":"C00027","source":"10.1_能量总量","target":"8.3_能量状态","type":"触发链","condition":"能量总量变化","priority":1,"effect":"能量总量决定能量状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有能量实值变化时，用来源、去向及前后余额核对能量状态是否改变。

5887｜{"id":"C00028","source":"10.1_能量总量","target":"8.3_能量状态","type":"转化","condition":"总量决定状态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用同一能量规则且所选事件改变储量时，在实有前后值上按本作阈值核对候选状态。

6317｜{"id":"C00030","source":"10.1_能量总量","target":"12.10_临界值","type":"触发","condition":"总量达到临界值；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用相应静态关系且本次确实到达阈值时，记录起因、实际能量前后、可见结果和重复核对的项目证据。

【动态网络原文 · 储备、代价、能量临界与聚能】

11683｜{"id":"C00056","source":"11.2_凝聚态","target":"10.1_总量","type":"转化","condition":"凝聚态→总量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件确有从凝聚资源提取能量时，分别核对可携资源和人物储备的前后值，记录转换后的实际去向。

11898｜{"id":"C00057","source":"11.2_凝聚态","target":"10.1_能量总量","type":"转化链","condition":"凝聚态可转化为总量","priority":1,"effect":"凝聚态转化为能量总量","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选转换动作符合本作路径时，沿用实际输入、有效产出和损耗核对能量总量候选变化，并保留后续可用额度的依据。

13944｜{"id":"C00067","source":"11.5_转化效率","target":"10.1_总量","type":"转化","condition":"效率决定总量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选动作完成转化且效率口径可查时，用投入、有效产出和去向核对储备后值，在 continuity 保留可回查的原因。

14159｜{"id":"C00068","source":"11.5_转化效率","target":"10.1_能量总量","type":"触发链","condition":"效率影响总量","priority":1,"effect":"转化效率影响能量总量","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本次实际效率会影响储备时，按项目已定规则对照转化前值、本次损耗和所得总量，保留同一单位下的变化。

18703｜{"id":"C00090","source":"118.1_代价追踪","target":"4.4_成长代价","type":"触发链","condition":"代价需要追踪","priority":1,"effect":"代价追踪是成长代价的管理","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选行动确实付出成长代价时，在 cost 和 continuity 对照实际损失、持续条件及前后状态，保留后场核对所需事实。

20821｜{"id":"C00100","source":"12.10_临界值","target":"44.3_爽点-代价","type":"共振","condition":"临界值突破伴随代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选突破行动已满足本作临界条件时，以实际前后值和可见结果核对角色付出的损失或限制，在 continuity 说明后场如何承接。

21036｜{"id":"C00101","source":"12.10_能量临界值","target":"14.6_结晶期","type":"触发链","condition":"临界值是结晶期标志","priority":1,"effect":"临界值是结晶期的标志","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已把临界值作为结晶期的标志时，在确有相应事件证据的情况下核对阈值前后、可见标志以及阶段状态的候选结果。

25721｜{"id":"C00124","source":"12.6_能量潮汐","target":"14.2_聚能期","type":"转化","condition":"潮汐影响聚能；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已选聚能行为发生在本作采用的潮汐窗口时，用实际可吸收能量及起始储备核对该动作的候选结果。

25936｜{"id":"C00125","source":"12.6_能量潮汐","target":"14.2_聚能期","type":"触发链","condition":"潮汐影响聚能","priority":2,"effect":"能量潮汐影响聚能效率","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】潮汐已按本作规则影响本次聚能效率时，用已定时段、有效吸收量和能量前后值核对进度，在 continuity 保留时窗依据。

【动态网络原文 · 能量、行动后果、立场与代价】

41709｜{"id":"C00200","source":"13.2_吸收速度","target":"10.1_总量","type":"转化","condition":"吸收决定总量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前已选吸收动作时，用实际持续时段和吸收速度核对取得量，再按本作的转化口径核对有效储备和去向。

41924｜{"id":"C00201","source":"13.2_吸收速度","target":"10.1_能量总量","type":"触发链","condition":"吸收速度决定总量","priority":1,"effect":"吸收速度决定能量总量","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本次吸收事件会改变能量总量时，对照实际单位时段、有效吸收及原有储备，给出可延续的总量候选变化。

42113｜{"id":"C00202","source":"13.2_吸收速度","target":"14.2_聚能期","type":"转化","condition":"吸收在聚能期体现；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选聚能事件中，核对角色实际从何处吸收、以什么速度持续多久，以及聚能进度在前后值和可见表现上如何体现。

42328｜{"id":"C00203","source":"13.3_转化效率","target":"10.1_总量","type":"转化","condition":"效率决定总量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次已知人物转化比例时，按实际吸收量和损耗区分有效储备前值及后值，在 continuity 保留去向依据。

42543｜{"id":"C00204","source":"13.3_转化效率","target":"10.1_能量总量","type":"触发链","condition":"效率决定总量","priority":1,"effect":"转化效率决定能量总量","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前转换动作已生效且效率口径可查时，将实际转化的有效量对应到角色新的储备，说明它为何不同于投入量。

46607｜{"id":"C00224","source":"14.2_聚能期","target":"10.1_总量","type":"转化","condition":"聚能增加总量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】上游聚能事件已有所选行动时，按实际来源、吸收量及损耗核对储备变化，在 continuity 说明后续如何沿用新值。

46822｜{"id":"C00225","source":"14.2_聚能期","target":"10.1_能量总量","type":"转化链","condition":"聚能增加总量","priority":1,"effect":"聚能期增加能量总量","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场聚能确有有效产出时，对照能量总量的前后值、可用来源和已确定的储存过程，记录实际增加量的依据。

49057｜{"id":"C00236","source":"14.4_运转期","target":"10.1_总量","type":"转化","condition":"运转期总量增长；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选运转行动且项目确有总量增长时，以循环前后的储备和已设的新增来源核对变化量，保留可查的输入与消耗。

49865｜{"id":"C00240","source":"14.5_固化期","target":"10.1_总量","type":"转化","condition":"固化期总量稳定；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选固化事件中，依据既定条件对照结构和总量。储备总量稳定时沿用原值，实际改变的属性由所选事件确认。

50484｜{"id":"C00243","source":"14.6_结晶期","target":"10.1_总量","type":"转化","condition":"结晶期总量达峰值；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】结晶质变已在所选事件成立时，分别核对能量密度和储备总量的前后差异，标记峰值需沿用本作的计量依据。

58558｜{"id":"C00281","source":"145.3_心理","target":"8.2_精神状态","type":"嵌套","condition":"心理=精神状态；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选触发确实改变精神状态时，用上游事件和实际前值核对后值，记录可观察反应及后续延续。

58773｜{"id":"C00282","source":"145.4_动作","target":"145.5_结果","type":"触发链","condition":"动作产生结果","priority":1,"effect":"动作产生结果","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场已有所选动作和具体结果时，按真实对象、触发和前后值核对动作造成的影响，并保存可观察的结果。

58972｜{"id":"C00283","source":"145.4_动作","target":"145.5_结果","type":"转化","condition":"动作→结果；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对照该场动作、所遇阻碍和实际应对，落实发生变化的属性、后续可延续的值及其可回查原因。

59832｜{"id":"C00287","source":"145.5_结果","target":"118.1_代价","type":"绑定","condition":"结果产生代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】结果确有代价时，用实际事件、支付时点和受影响对象记录成本、前后变化及之后仍须承接的限制。

61536｜{"id":"C00295","source":"147.1_他人视角","target":"5.3_情感关系","type":"触发链","condition":"他人视角影响情感","priority":1,"effect":"他人视角影响情感关系","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选事件中实际观察改变了两人的情感关系时，核对引发改变的所见、实际态度前后与下一步行为，保存延续依据。

65143｜{"id":"C00312","source":"149.2_判断","target":"149.3_立场","type":"触发链","condition":"判断决定立场","priority":1,"effect":"判断决定立场","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场判断已落实到实际表态或行动时，核对人物对明确对象的前后立场与推动变化的证据。

65342｜{"id":"C00313","source":"149.2_判断","target":"149.3_立场","type":"转化","condition":"判断→立场；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对同一所选事件核对判断在何种实际表态或行动中成立，记录前后立场、受影响的关系和后续保持条件。

65987｜{"id":"C00316","source":"149.3_立场","target":"86.6_立场确定","type":"转化","condition":"立场确定；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选站队行动实际改变关系位置时，用事件、可见表态、前后立场及所付代价核对怎样由后场承接。

67629｜{"id":"C00324","source":"15.2_进阶三阶段","target":"15.5_失败后果","type":"转化","condition":"阶段含失败后果；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前已选进阶尝试可能失败时，依本作已有规则核对失败条件、可观察后果及能由后场承接的状态差异。

68463｜{"id":"C00328","source":"15.4_突破代价","target":"118.1_代价追踪","type":"绑定","condition":"代价需追踪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场已有实际突破代价时，依所选行动和前后状态记录支付时间、真实损失及会影响后场的限制。

68893｜{"id":"C00330","source":"15.4_突破的代价类型","target":"118.1_代价追踪","type":"触发链","condition":"代价需要追踪","priority":1,"effect":"突破代价需要追踪","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已建立突破的代价类型时，把同一次实际支付的项目对象、前后变化及后场承接记入 cost 和 continuity。

69271｜{"id":"C00332","source":"15.5_突破失败","target":"8.1_受伤","type":"触发","condition":"失败→受伤；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「15.5_突破失败」经「触发」影响「8.1_受伤」（条件：失败→受伤）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

69486｜{"id":"C00333","source":"15.5_突破失败","target":"4.5_成长中断","type":"转化","condition":"失败→中断；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「15.5_突破失败」经「转化」影响「4.5_成长中断」（条件：失败→中断）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

69701｜{"id":"C00334","source":"15.5_突破失败","target":"8.2_抑郁","type":"触发","condition":"失败→抑郁；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「15.5_突破失败」经「触发」影响「8.2_抑郁」（条件：失败→抑郁）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

69916｜{"id":"C00335","source":"15.5_突破失败后果","target":"4.5_成长中断","type":"触发链","condition":"失败导致成长中断","priority":1,"effect":"突破失败导致成长中断","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有实际失败事件、且成长确因它受限时，核对角色受阻的能力或阶段、预计持续条件及能够支持该后果的行动证据。

70105｜{"id":"C00336","source":"15.5_突破失败后果","target":"8.1_身体状态","type":"触发链","condition":"失败影响身体","priority":1,"effect":"突破失败影响身体状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前失败按项目规则确实改变身体状态时，用角色前值、事件实际发生的影响和可感身体表现核对变化及后续恢复条件。

70294｜{"id":"C00337","source":"15.5_突破失败后果","target":"8.2_精神状态","type":"触发链","condition":"失败影响精神","priority":1,"effect":"突破失败影响精神状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本场失败事件已经设定精神状态后果时，用既有前值与实际言行、注意变化或其他可见证据核对改变，并记明后场承接。

【动态网络原文 · 能量消耗、恢复、透支及关系变化】

75595｜{"id":"C00362","source":"153.3_对立强度","target":"153.4_对立演变","type":"转化","condition":"强度决定演变；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件改变对立强度时，依据真实行动和前后关系记录对立如何演变，并给出后续连续性。

81224｜{"id":"C00389","source":"16.1_消耗速率","target":"10.1_总量","type":"转化","condition":"消耗决定总量变化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按本场实际耗能动作、使用时长或次数和已定消耗规则核对储备前后值，在 continuity 留下实际去向。

81439｜{"id":"C00390","source":"16.1_消耗速率","target":"10.1_能量总量","type":"触发链","condition":"消耗影响总量","priority":1,"effect":"消耗速率影响能量总量","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前确有耗能时，按已选行动的速率口径及真实时段算清总量差异，记录可观察的剩余使用边界。

81628｜{"id":"C00391","source":"16.1_消耗速率","target":"8.3_能量状态","type":"触发链","condition":"消耗影响状态","priority":1,"effect":"消耗速率影响能量状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本次实际消耗会改变能量状态时，对照角色原有能量、实际消耗和本作阈值核对候选状态。

81817｜{"id":"C00392","source":"16.1_消耗速率","target":"8.3_能量状态","type":"转化","condition":"消耗影响状态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用消耗与状态的既有关系时，把所选动作消耗的实际量与本作状态判据对应起来，保留可查前后值。

82247｜{"id":"C00394","source":"16.2_恢复方式","target":"10.1_总量","type":"转化","condition":"恢复增加总量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前已有符合规则的恢复动作时，按来源、有效恢复量和作用时段核对储备前后值，保留实际去向或余额。

82462｜{"id":"C00395","source":"16.2_恢复方式","target":"8.3_能量状态","type":"触发链","condition":"恢复影响状态","priority":1,"effect":"恢复方式影响能量状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本次恢复方式确实改变了能量状态时，用实际进度和既定状态边界核对从什么状态恢复到什么状态。

82651｜{"id":"C00396","source":"16.2_恢复方式","target":"8.3_能量状态","type":"转化","condition":"恢复影响状态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用恢复影响状态的关系时，核对本场实际恢复来源、到达的量和出现的可见变化，记清仍要延续的限制。

82866｜{"id":"C00397","source":"16.3_透支","target":"16.4_后遗症","type":"转化","condition":"透支→后遗症；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选行动确实透支且本作已给出后遗症时，依据实际透支程度、前值和所见变化记录延后出现的影响与持续条件。

83081｜{"id":"C00398","source":"16.3_透支","target":"8.1_身体状态","type":"触发","condition":"透支影响身体；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前透支符合已定身体后果条件时，核对实际动作、身体前值及可见变化，把后场应承接的身体限制写入记录。

83511｜{"id":"C00400","source":"16.3_透支规则","target":"8.1_身体状态","type":"触发链","condition":"透支影响身体","priority":1,"effect":"透支影响身体状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有透支规则及合乎条件的借用量时，对照身体初始状态和实际负荷记下可观察的身体受限及恢复条件。

83700｜{"id":"C00401","source":"16.3_透支规则","target":"8.2_精神状态","type":"触发链","condition":"透支影响精神","priority":1,"effect":"透支影响精神状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】所选透支在本作确会影响精神时，用状态前值、触发证据和之后的注意、言行或判断差异核对影响。

83889｜{"id":"C00402","source":"16.4_后遗症","target":"8.1_受伤","type":"触发","condition":"后遗症影响身体；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「16.4_后遗症」经「触发」影响「8.1_受伤」（条件：后遗症影响身体）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

84319｜{"id":"C00404","source":"16.4_透支后遗症","target":"8.1_身体状态","type":"触发链","condition":"后遗症影响身体","priority":1,"effect":"透支后遗症影响身体状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前确有透支后遗症时，对照角色身体前值和可见表现核对何时开始限制行动，保留具体的持续或恢复条件。

84508｜{"id":"C00405","source":"16.4_透支后遗症","target":"8.2_精神状态","type":"触发链","condition":"后遗症影响精神","priority":1,"effect":"透支后遗症影响精神状态","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有透支后对精神的影响时，用已选触发和之后真实言行核对注意、判断或情绪的前后差异，在后场沿用。

88604｜{"id":"C00425","source":"17.6_能量潮汐","target":"14.2_聚能期","type":"转化","condition":"潮汐影响聚能；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实际聚能安排落在本作潮汐时段时，按所选吸收动作、可用能量与已定口径核对储备前后值和可见进度。

92344｜{"id":"C00443","source":"19.3_例外代价","target":"118.1_代价追踪","type":"绑定","condition":"代价需追踪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场异常被实际采用且发生支付时，按付出前后值、所选动作和受影响者记下成本及后场须承接的限制。

96807｜{"id":"C00464","source":"2.6_角色状态","target":"9.1_状态叠加","type":"约束","condition":"叠加规则；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】多项状态在同一事件中并存时，沿用既定叠加条件核对有效状态、实际前后变化和继续影响的限制。

102898｜{"id":"C00493","source":"21.3_寻找新均衡","target":"22.1_势力互动","type":"转化","condition":"新均衡伴随势力重组；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选重组事件已造成势力关系变化时，对照实际对象、前关系、触发动作和关系后值记录新的成立条件。

105818｜{"id":"C00507","source":"22.2_势力间张力","target":"153.1_对立","type":"转化","condition":"张力转化为对立；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件让势力张力变成明确对立时，核对原关系、实际行动和新的对立证据，保留后续关系状态的边界。

【动态网络原文 · 资源得失、道具前后状态及人物变化】

110834｜{"id":"C00531","source":"24.2_资源价值层级","target":"24.3_价值动态","type":"演化","condition":"层级动态变化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件改变实际资源的价值层级时，记录前后价值、实有成交或供需依据以及会持续的影响。

111049｜{"id":"C00532","source":"24.2_资源价值层级","target":"24.3_资源价值动态变化","type":"触发链","condition":"层级决定变化幅度","priority":1,"effect":"价值层级决定价值变化幅度","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已定价值分级及波动口径时，用实际事件、时间段和前后数值核对变化幅度及归因。

111877｜{"id":"C00536","source":"24.3_资源价值动态","target":"27.3_稀缺性","type":"转化","condition":"价值变化影响稀缺性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本次市场事件影响实际可得性时，分别核对价值与可取得数量的前后变化，记录使两项发生关联的具体条件。

112092｜{"id":"C00537","source":"24.3_资源价值动态","target":"125.10_价值波动","type":"转化","condition":"价值动态是资源库部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】沿用 125.10 的价值波动条目，在现有记录保存所选事件引起的实际前后价格、比较时点及真实依据。

112522｜{"id":"C00539","source":"24.3_资源价值动态变化","target":"27.3_资源稀缺性","type":"触发链","condition":"价值变化影响稀缺性","priority":1,"effect":"价值动态变化影响稀缺性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】按实际成交、库存和需求的前后证据核对价值波动是否影响资源可得性，保留各项所用口径。

116264｜{"id":"C00557","source":"26.3_交易成本","target":"125.6_获取成本","type":"转化","condition":"交易成本是获取成本；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选交易实际付出取得成本时，用支付条件、实际金额或资源和前后变化记录取得结果，沿用 125.6 的获取成本条目。

117721｜{"id":"C00564","source":"27.1_资源循环","target":"125.4_变化追踪","type":"绑定","condition":"循环需追踪；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】资源在所选事件中实际进入、转移或消耗时，按 125.4 的变化追踪用途对账实际对象、起止值与去向。

120221｜{"id":"C00576","source":"28.1_道具生命史","target":"30.5_失效转化","type":"转化","condition":"生命史终点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选事件确使道具失效或转化时，按物件前值、触发和可见结果记录旧功能的去向及此后状态。

121893｜{"id":"C00584","source":"28.3_代价机制","target":"118.1_代价追踪","type":"绑定","condition":"代价需追踪；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色所选道具动作付出代价时，依据所选动作、实际支付时点及受影响的前后值记录损失和下一场须承接的限制。

123565｜{"id":"C00592","source":"28.4_道具成瘾性","target":"8.2_精神状态","type":"触发","condition":"成瘾影响精神；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】当前设定的道具依赖确使人物精神状态变化时，用选中触发、前后值和可见反应保留变化及持续条件。

125866｜{"id":"C00603","source":"29.1_道具与角色交互","target":"7.4_身体反应","type":"转化","condition":"交互产生身体反应；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】所选道具交互确实引发身体影响时，核对实际操作、人物前值、身体反应与持续限制。

127124｜{"id":"C00609","source":"29.3_道具反功能","target":"28.3_代价机制","type":"转化","condition":"反功能是代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本场所选使用确实发生反功能时，核对触发、物件和人物前后值，把实际损失及还会影响的动作范围记入记录。

130086｜{"id":"C00623","source":"3.1_生理欲望","target":"8.1_饥饿","type":"触发","condition":"未满足；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「3.1_生理欲望」经「触发」影响「8.1_饥饿」（条件：未满足）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

131774｜{"id":"C00631","source":"3.1_角色欲望_生理需求","target":"8.1_身体状态","type":"触发链","condition":"生理需求未被满足","priority":1,"effect":"未被满足的生理需求驱动角色行动","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「3.1_角色欲望_生理需求」经「触发链」影响「8.1_身体状态」（条件：生理需求未被满足）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

134425｜{"id":"C00644","source":"3.3_角色野心","target":"151.1_身份","type":"转化链","condition":"野心达成","priority":1,"effect":"野心的达成导致身份变化","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已选事件确实使人物实现野心且改变身份时，用实有资格、关系或社会位置的前后值核对持续影响。

138748｜{"id":"C00665","source":"3.6_情绪管控","target":"8.2_精神状态","type":"转化","condition":"影响；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】实际情绪管控动作会改变精神状态时，利用所选策略、精神前值和具体反应核对后值及持续条件。

139576｜{"id":"C00669","source":"3.6_角色情绪管控","target":"8.2_精神状态","type":"触发链","condition":"情绪管控策略被激活","priority":2,"effect":"情绪管控策略影响精神状态稳定性","direction":"双向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】处置策略在所选事件中已有实际结果时，用精神状态前值和可观察反应核对稳定性变化及以后限制。

141232｜{"id":"C00677","source":"30.2_功能边界测试","target":"29.4_道具进化","type":"触发链","condition":"测试是进化方式","priority":1,"effect":"边界测试是道具进化方式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本次道具边界测试已有选定结果时，按实际触发、前功能和新的可用表现核对是否产生阶段变化及代价。

141630｜{"id":"C00679","source":"30.2_边界测试突破","target":"29.4_道具进化","type":"转化","condition":"测试是进化的方式；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选边界测试使道具进化时，对照测试动作、原限制和可查结果写清前后功能及下一场可用范围。

142904｜{"id":"C00685","source":"30.4_道具维护与升级","target":"29.4_道具进化","type":"触发链","condition":"维护是进化方式","priority":1,"effect":"道具维护与升级是进化方式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】选中维护或升级确会改变道具时，以实际操作、物件前值和可见结果核对新阶段及持续的限制。

143103｜{"id":"C00686","source":"30.4_道具维护升级","target":"29.4_道具进化","type":"转化","condition":"维护升级是进化方式；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目采用维护升级促成进化时，按本场实际材料、代价和操作结果记录功能前后、能否继续使用及恢复条件。

143533｜{"id":"C00688","source":"30.5_道具失效与转化","target":"28.1_道具生命史","type":"触发链","condition":"失效是生命史终点","priority":1,"effect":"道具失效与转化是生命史的终点","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】道具已在所选事件中失效或转化时，记录原功能终止的条件、物件在此后的去向和仍然可观察的状态。

143732｜{"id":"C00689","source":"30.5_道具失效转化","target":"28.1_生命史","type":"转化","condition":"失效是生命史终点；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据项目确认的功能终点，对照物件、所选事件和新状态核对哪些效果消失或变为另一种用途。"""
