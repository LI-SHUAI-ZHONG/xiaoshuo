"""人物设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 人物分类与配角职责】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

4675｜{"id":"C00022","source":"1.8_角色分类体系","target":"124.1_小说种类","type":"约束","condition":"类型决定分类；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本轮实际选型及本人物在该类型中的叙事职责。执行：根据本书实际分工注明此人揭示、阻挠或推动什么。核验：在剧情中找到其独有职责导致的一项选择。

4890｜{"id":"C00023","source":"1.8_角色分类体系","target":"144.1_配角级别","type":"转化","condition":"功能分类；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：具体配角、参与层次、关系位置和剧情职责。执行：由已设计的参与程度与对主线的影响说明配角层级。核验：核对该人的出场作用与关系距离是否支持这一分级。

【动态网络原文 · 天赋层级、能力边界和反派依据】

8604｜{"id":"C00041","source":"10.4_天赋品质","target":"13.1_等级","type":"转化","condition":"天赋决定等级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：天赋品质与等级的本书规则，此人的品质表现和分级结果。执行：用可观察表现说明本人的天赋等级及可执行能力。核验：同一表现按世界卡的分级条件检验，行动不得超出本级。

8819｜{"id":"C00042","source":"10.4_天赋品质","target":"13.1_等级划分","type":"触发链","condition":"天赋决定等级","priority":1,"effect":"天赋品质决定等级","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作者已经设定天赋分级时，对照采用的等级条目和人物品质核对分类结果，记录适用的层级及其判断条件。

9008｜{"id":"C00043","source":"10.4_天赋品质","target":"13.4_上限瓶颈","type":"触发链","condition":"天赋决定上限","priority":1,"effect":"天赋品质决定上限","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作明确用天赋限制能力上限时，写明该人物受限的成长维度、能达到的程度和实际瓶颈表现。

9197｜{"id":"C00044","source":"10.4_天赋品质","target":"13.4_上限瓶颈","type":"转化","condition":"天赋决定上限；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：天赋限制成长的世界规则和本人的具体天赋、受限维度。执行：在本人的能力限制中写出哪项成长受到何种瓶颈。核验：核对选择受阻是否来自这个已定义的天赋上限。

11064｜{"id":"C00053","source":"11.1_游离态","target":"13.2_吸收速度","type":"约束","condition":"游离态影响吸收；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：游离态对吸收的环境规则、此人单位时间的吸收能力。执行：为同一人物记录适用环境、吸收速率及环境变化下的边界。核验：以相同时间及环境口径判断行动是否可行。

11279｜{"id":"C00054","source":"11.1_游离态","target":"13.2_吸收速度","type":"触发链","condition":"游离态影响吸收速度","priority":2,"effect":"游离态浓度影响吸收速度","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】浓度确实影响本角色的吸收速度时，以同一时间口径比较已定环境中的实际吸收能力，并保留人物已有的适用限制。

14348｜{"id":"C00069","source":"11.5_转化效率","target":"13.3_转化效率","type":"嵌套","condition":"效率是天赋维度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：路径转化效率与个人天赋指标的联系，两种计量各自的依据。执行：从该路径的效率定位个人吸收后能进入储备的比例。核验：核对路径损耗、个人入储比例及各自分母。

26340｜{"id":"C00127","source":"12.7_能量感知","target":"67.1_感知","type":"转化","condition":"能量感知是感知的一部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：能量感知的世界机制、本人的感知对象、精度与失效条件。执行：给本人的感知能力指定能辨认的信号、误差或有效范围。核验：场内只能获得此人真正有能力辨认的信息。

26959｜{"id":"C00130","source":"12.7_能量感知规则","target":"67.1_感知","type":"嵌套链","condition":"能量感知是感知的一部分","priority":2,"effect":"能量感知属于感知范畴","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有能量感知机制时，结合角色的实际感知能力记录能辨识的能量特征及所用感官，写明与其他感知方式的分工。

32853｜{"id":"C00158","source":"123.20_反派设计","target":"1.6_反派","type":"转化","condition":"反派设计=反派；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本书对立角色、其独立目标和能实际调用的手段。执行：用反派自己的目的和能力设计其对抗选择及阻力。核验：即使不知主角计划，其行动仍有本人的理由与手段。

【动态网络原文 · 天赋、能力、配角职责及人格外化】

40282｜{"id":"C00193","source":"13.1_天赋等级","target":"13.2_吸收速度","type":"转化","condition":"等级决定吸收；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：天赋分级与吸收速度的世界规则、人物等级与同环境表现。执行：从该人的实际等级推到给定环境和时间中的吸收速度。核验：比较行动耗时须采用同一环境与计量单位。

40497｜{"id":"C00194","source":"13.1_天赋等级","target":"13.4_上限瓶颈","type":"转化","condition":"等级决定上限；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：世界等级与成长瓶颈的对应、本人等级及受限方向。执行：以实际等级限定本次成长能达到的边界。核验：突破边界时应有本书已成立的突破前置。

41142｜{"id":"C00197","source":"13.1_等级划分","target":"13.2_吸收速度","type":"触发链","condition":"等级决定吸收速度","priority":1,"effect":"等级决定吸收速度","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作规定等级影响吸收速度时，按已有分级口径核对实际人物在什么环境、以什么速度吸收，以及该判断的比较依据。

41331｜{"id":"C00198","source":"13.1_等级划分","target":"13.4_上限瓶颈","type":"触发链","condition":"等级决定上限","priority":1,"effect":"等级决定上限瓶颈","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】把本作已确认分级与角色成长限制对应起来，说明哪项能力达到瓶颈及角色能够观察到的实际表现。

42732｜{"id":"C00205","source":"13.3_转化效率","target":"11.5_转化效率","type":"嵌套","condition":"效率是天赋维度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：个人入储效率的依据、本书对应路径的损耗口径。执行：从本人的入储比例反查该条转化路径，分别记录两种指标。核验：不因角色比率而把整条路径写成同一个效率。

42947｜{"id":"C00206","source":"13.4_上限瓶颈","target":"10.4_天赋","type":"转化","condition":"上限决定天赋；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：实际瓶颈、可观测表现、天赋规则及训练或环境的其他解释。执行：把一次受阻作为天赋判断的线索，保留其他成因。核验：剧情不能仅凭受阻就断定其天赋等级。

43566｜{"id":"C00209","source":"13.4_上限瓶颈","target":"38.2_能力上限","type":"转化","condition":"上限决定能力上限；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本人的具体能力、已知操作上限与突破条件。执行：把瓶颈换算为该项行动当前能达到的边界。核验：选择超限操作前，应在当前条件中找到已满足的突破依据。

45395｜{"id":"C00218","source":"14.1_感知期","target":"12.7_能量感知规则","type":"触发链","condition":"感知期体现能量感知","priority":1,"effect":"感知期体现能量感知能力","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作有感知期且角色已出现首次感知时，按世界规则核对能辨识的具体特征、当前能力范围和仍不具备的分辨精度。

56010｜{"id":"C00269","source":"144.1_配角级别","target":"121.1_配角定义","type":"转化","condition":"级别定义配角；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：配角分级、实际参与深度和在本书的剧情功能。执行：根据已设计的层级和具体参与工作定义配角角色。核验：检查分级所声称的参与程度是否在剧情中兑现。

56225｜{"id":"C00270","source":"144.1_配角级别","target":"1.2_重要配角","type":"嵌套","condition":"级别决定分类；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：重要配角、与主角的实际联系、独立目标及剧情影响。执行：让重要配角以自己的目标影响决策和主线。核验：找出由该配角主动选择造成的后果。

57284｜{"id":"C00275","source":"145.1_目标","target":"3.1_欲望","type":"嵌套","condition":"欲望决定目标；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：同一人物的深层欲望、当前所求和处境。执行：将深层需要指向此刻能选择的具体目标。核验：核对关键选择怎样服务该人物的需要和眼前目标。

60676｜{"id":"C00291","source":"146.1_人格外化","target":"146.2_三层外化","type":"转化","condition":"外化分三层；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：同一人物在社交、日常和压力下的三层外在表现。执行：分开设计有意识的社会面貌、自发习惯与受压反应。核验：本场触发条件与所展示层次一致。

60891｜{"id":"C00292","source":"146.2_三层外化","target":"146.3_行为映射","type":"转化","condition":"三层影响映射；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：已设计的三层人格、可复现的行为和情境。执行：从人格层次映射到不同情境下能看见的具体行为。核验：核对人物在何种场合切换动作或语言。

【动态网络原文 · 角色身份、性格、能力及前状态】

71956｜{"id":"C00345","source":"151.1_身份定义","target":"151.2_三层身份","type":"转化","condition":"身份分三层；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：同一角色的表层、隐藏和被动身份以及可知范围。执行：分开记录不同身份以何条件暴露、被谁获知。核验：未获知隐藏身份的角色不能据其行动。

72386｜{"id":"C00347","source":"151.1_身份定义","target":"151.3_身份功能","type":"转化","condition":"身份有功能；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物实际身份和该身份赋予的权限、资源或义务。执行：将身份作用落实为该人可承担的一项行动和限制。核验：逐项核对行动授权和其适用范围。

94012｜{"id":"C00451","source":"2.1_角色外貌","target":"151.1_身份","type":"嵌套","condition":"外貌暗示身份；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物身份、外在标记及可见和可披露的边界。执行：用一处有来历的装束或标记提示身份并限定推断范围。核验：观察者可以看见线索，所知程度符合其视角。

95302｜{"id":"C00457","source":"2.4_角色性格","target":"146.1_人格外化","type":"转化","condition":"性格需外化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：该人的性格特点、具体行为及其触发场合。执行：把性格转写成可重复识别的言语、动作或习惯。核验：在相符的情境中找到该特点的可见表现。

95732｜{"id":"C00459","source":"2.4_角色性格","target":"70.1_坚韧","type":"嵌套","condition":"性格决定意志；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：已有坚韧特质、压力条件及本人实际的坚持方式。执行：用受压时仍继续的行为呈现意志及其代价。核验：核对压力、坚持选择与维持条件。

95947｜{"id":"C00460","source":"2.5_角色能力","target":"10.1_能量总量","type":"转化","condition":"能力决定能量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：能量总量机制、该人的能力与初始储量。执行：核对其能力如何决定初始能量储备和可动用边界。核验：行动与后续状态变化须能从同一初始储量承接。

96162｜{"id":"C00461","source":"2.5_角色能力","target":"14.1_感知期","type":"绑定","condition":"能力决定成长阶段；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本书感知期的判据、本人的感知表现与不能执行的操作。执行：按本人的可观察能力定位其当前感知阶段。核验：状态仍在感知期时不提前使用后阶段能力。

96377｜{"id":"C00462","source":"2.6_角色状态","target":"8.1_身体状态","type":"转化","condition":"状态包含身体；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本人冻结的初始身体状态、可见症状与当时适用条件。执行：将身体条件和相应限制作为该人物的初始状态候选。核验：在受限动作和状态变化中核对同人的真实前值。

96592｜{"id":"C00463","source":"2.6_角色状态","target":"8.2_精神状态","type":"转化","condition":"状态包含精神；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本人冻结的初始精神状态、触发和行为表现。执行：以已设计的触发与反应说明注意、判断或情绪的前值。核验：不能把观察到的他人反应直接写成其内心事实。

【动态网络原文 · 欲望待核、野心、责任与阶层身份】

128581｜{"id":"C00616","source":"3.1_安全欲望","target":"70.5_执着","type":"触发","condition":"缺失；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物缺失的具体安全保障、受威胁处境及由此触发的执着行为。执行：由安全感缺失定位该角色反复守住的人、物或退路。核验：核对其执着举动是否紧扣同一处安全缺失与代价。

129011｜{"id":"C00618","source":"3.1_安全欲望","target":"5.6_权力敏感","type":"嵌套","condition":"激活；且当前故事明确采用该静态关系","priority":3,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物的自保需要、对上下级或掌控权的警觉表现及触发场合。执行：把安全需要落实为对指令、越权或地位变动的试探与防备。核验：核对关系互动中的警觉反应是否源于自保边界受触动。

129226｜{"id":"C00619","source":"3.1_尊重欲望","target":"151.1_身份","type":"转化","condition":"被轻视；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物渴望被认可的尊严诉求、遭受轻视的经历及争取的身份位置。执行：将受轻视后的尊严需要转化为争取或维护特定身份的选择。核验：核对剧情中的身份争夺是否回应此前被轻视的具体处境。

130946｜{"id":"C00627","source":"3.1_自我实现","target":"3.3_野心","type":"转化","condition":"强烈；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物强烈的自我证明或志业追求、由此形成的具体野心目标。执行：把实现自身价值的强烈愿望落实为可检验的进取目标与代价。核验：核对野心指向的成果是否体现此人想证明的核心能力或理想。

135436｜{"id":"C00649","source":"3.3_野心","target":"33.2_晋升","type":"驱动","condition":"有路径；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本人晋升野心、可行的制度通道及当前门槛。执行：从本人想获得的位置出发，让角色选择是否争取该机会。核验：核对人物的争取是否满足通道资格。

135866｜{"id":"C00651","source":"3.4_角色责任","target":"145.1_目标","type":"触发链","condition":"责任转化为具体目标","priority":1,"effect":"责任驱动目标设定","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】根据已明定的责任对象及范围，在人物卡将承担的责任对应到该角色实际想完成的目标。

136662｜{"id":"C00655","source":"3.4_责任","target":"74.5_义务","type":"触发","condition":"激活；且当前故事明确采用该静态关系","priority":1,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本人已接受的责任、承诺对象及义务被触发的条件。执行：给特定对象的责任指定会启动哪项义务。核验：剧情中的义务须有同一承诺和触发事件。

151472｜{"id":"C00725","source":"33.1_阶层划分","target":"151.1_身份","type":"嵌套链","condition":"阶层决定身份","priority":1,"effect":"阶层划分决定身份","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已有明确阶层及相应身份时，按真实角色、制度资格和当前待遇核对人物身份的具体表现。

151671｜{"id":"C00726","source":"33.1_阶层划分","target":"151.1_身份","type":"转化","condition":"阶层决定身份；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本书阶层制度、人物当前阶层及实际身份权限。执行：将该人的阶层位置落实到特定场合的身份资格。核验：只在制度允许的地域或关系中兑现资格。

153144｜{"id":"C00733","source":"33.2_晋升通道","target":"3.3_角色野心","type":"触发链","condition":"晋升激发野心","priority":1,"effect":"晋升通道激发野心","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作实际晋升机会激起角色野心时，用当前身份和具体通道核对他想达成的变化、已有动机和实际成本。

153343｜{"id":"C00734","source":"33.2_晋升通道","target":"3.3_野心","type":"驱动","condition":"通道激发野心；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：可用晋升通道和门槛、此人由此被激发的目标。执行：从实际机会追到人物野心的方向与选择。核验：通道关闭时须重新核对由它激发的行动。

【动态网络原文 · 种族条件、构造承受力和职业身份】

163731｜{"id":"C00784","source":"36.2_种族基本属性","target":"13.1_等级划分","type":"嵌套链","condition":"种族属性决定天赋等级","priority":1,"effect":"种族属性决定天赋等级","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","奇幻"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已规定某项种族属性影响天赋等级时，用实际人物的设定及可查表现核对采用的等级和边界。

164322｜{"id":"C00787","source":"36.2_种族基本属性","target":"13.1_天赋等级","type":"嵌套","condition":"种族属性决定天赋；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：虚构种族的天赋规则、个体特征和本人等级的依据。执行：依据本书规则和本人的实际表现核对该个体的天赋等级。核验：群体设定与个人观察必须同时支持能力设计。

164940｜{"id":"C00790","source":"36.3_种族先天限制","target":"37.3_承受力","type":"嵌套","condition":"限制决定承受力；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：种族先天限制、本人的构造与所承受的具体负荷。执行：在同一人物的能力中记录可承受范围及过载表现。核验：核对负荷、条件与该人的受限反应。

165569｜{"id":"C00793","source":"36.4_种族社会嵌入","target":"151.1_身份","type":"嵌套","condition":"种族嵌入决定身份；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本书种族在社会中的位置、人物归属和行动许可。执行：把人物的社会嵌入落实为旁人可辨的身份和实际资格。核验：他人对身份的反应须有可知依据。

167881｜{"id":"C00804","source":"37.1_构造类型","target":"37.3_承受力","type":"转化","condition":"类型决定承受力；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本人的构造类型、本书负荷规则与可见失效条件。执行：据实际构造核对这名角色承受的负荷与上限。核验：超载后果须作用于指定角色及相同构造。

168096｜{"id":"C00805","source":"37.1_构造类型","target":"37.3_构造决定承受力","type":"触发链","condition":"类型决定承受力","priority":1,"effect":"构造类型决定承受力","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】按该角色实有构造和本作已定负荷条件核对其能承受的量、时长及失去作用时的具体限制。

168285｜{"id":"C00806","source":"37.2_构造决定能力上限","target":"13.1_等级划分","type":"嵌套链","condition":"构造决定天赋等级","priority":1,"effect":"构造决定天赋等级","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用构造影响等级的设定时，用人物实际构造及现有评定依据核对可判定的等级，保留其他已知因素。

173084｜{"id":"C00829","source":"39.1_职业类型","target":"39.2_职业与身份关系","type":"触发链","condition":"类型决定身份","priority":1,"effect":"职业类型决定身份","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色已有明确职业时，核对这一职业实际影响的身份、资格和外人可知范围，记下现有设定依据。

173283｜{"id":"C00830","source":"39.1_职业类型","target":"39.2_职业身份","type":"转化","condition":"职业决定身份；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：当前职业类别、任职制度与该人的身份功能。执行：从工作类别追到任职身份带来的活动范围。核验：履职行动须落在本书认可的任职权限以内。

173713｜{"id":"C00832","source":"39.2_职业与身份","target":"151.1_身份","type":"转化","condition":"职业决定身份；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：职业形成身份的本书制度、角色职务与具体资格。执行：把职业身份在局部社会的地位和限制写进人物卡。核验：身份判断依赖本人的真实职务和相应制度。

174143｜{"id":"C00834","source":"39.2_职业与身份关系","target":"151.1_身份","type":"嵌套链","condition":"职业决定身份","priority":1,"effect":"职业决定身份","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对已有职业的人物记录身份实际如何被认出、随职责任务生效的资格以及要对谁披露。

174342｜{"id":"C00835","source":"39.3_职业与能力","target":"2.5_角色能力","type":"嵌套","condition":"职业需要能力；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：岗位真实要求、该人的任职身份与同一人的能力和限制。执行：以世界卡中的工作要求核对该人物能做的事、凭据与短板。核验：按同一角色、岗位和能力限制核验能否采取行动。

178825｜{"id":"C00856","source":"4.1_弧光起点","target":"145.1_目标","type":"转化","condition":"影响目标；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物出场时的认知局限或初始缺陷、由该起点限定的当前目标。执行：用弧光起点的既有偏见或伤痕限定角色开局时追求的目标。核验：核对初始目标如何受限于起点认知，并在后续受阻时暴露局限。

183093｜{"id":"C00876","source":"40.3_技能学习条件","target":"14.1_感知期","type":"嵌套","condition":"技能学习是成长阶段；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本书技能学习与感知期的关联、当前人物的学习条件。执行：记录实际学习对象、观察训练前置和当前可学范围。核验：在进入下一学习阶段前核对感知期条件。

【动态网络原文 · 角色责任及说话风格别名待核】

241576｜{"id":"C01153","source":"5.1_亲缘关系","target":"3.4_责任","type":"驱动","condition":"亲缘激活责任；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：已冻结的亲缘关系双方、该人物对这一亲人的实际承诺。执行：将对该名亲人的承诺关联到责任对象与行动边界。核验：查明关系双方、承诺对象和履责行动指向同一人。

259206｜{"id":"C01235","source":"57.5_说话风格","target":"2.4_角色性格","type":"转化","condition":"风格决定性格；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物固定的用词句式或停顿习惯、与之互证的性格特征。执行：通过可辨认的说话方式外化角色性格，禁止脱离语态贴性格标签。核验：核对台词句式、口癖或停顿是否稳定体现同一性格侧面。

【动态网络原文 · 复合情感渴望分项待核】

273689｜{"id":"C01304","source":"6.2_复合情感_渴望","target":"3.1_欲望","type":"驱动","condition":"渴望驱动欲望；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：由多重情绪交织形成的复合渴望、被其持续驱动的深层欲望。执行：写清哪几种具体情绪叠加成渴望，并推动角色的深层诉求。核验：核对情境触发的复合情绪如何强化或唤醒该人物的核心欲望。

273904｜{"id":"C01305","source":"6.2_复合情感_渴望","target":"3.1_角色欲望","type":"共振链","condition":"渴望与欲望方向一致","priority":1,"effect":"渴望放大欲望的驱动强度","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「6.2_复合情感_渴望」经「共振链」影响「3.1_角色欲望」（条件：渴望与欲望方向一致）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

【动态网络原文 · 意志、责任与价值的角色依据】

319384｜{"id":"C01521","source":"70.2_坚定","target":"3.2_执念","type":"共振","condition":"坚定强化执念；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：此人已明确的执念对象、坚定态度与干扰条件。执行：用面对干扰时的具体坚持解释其执念。核验：找出换取眼前好处也不能放弃的目标及代价。

320674｜{"id":"C01527","source":"70.5_执着","target":"3.2_执念","type":"共振","condition":"执着强化执念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：同一执念对象、反复持续的行为及其适用情境。执行：以实际反复投入说明执着怎样加强该执念。核验：核对每次坚持是否仍针对同一个目标。

321733｜{"id":"C01532","source":"71.1_意志强度","target":"70.1_坚韧","type":"转化","condition":"强度决定坚韧；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本书意志强度的计量口径、本人受压表现和恢复条件。执行：对照项目量表和角色行为说明承压与恢复的范围。核验：人物不能由形容词直接换算成未设定的分数。

328963｜{"id":"C01566","source":"74.2_善恶","target":"75.5_美德","type":"转化","condition":"善=美德；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本人的善恶判断、要践行的具体美德和已设计行为。执行：以该人物的取舍呈现实际践行的美德。核验：一个善恶标签不能代替人物对具体事件的选择。

329393｜{"id":"C01568","source":"74.3_正义","target":"33.1_阶层","type":"嵌套","condition":"正义感源于阶层；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：本书阶层环境、该人物的亲历及其正义判断。执行：由此人的具体待遇和经历解释其正义观。核验：不能从阶层标签直接推定所有人的价值判断。

330253｜{"id":"C01572","source":"74.5_责任","target":"145.1_目标","type":"触发链","condition":"责任驱动目标","priority":1,"effect":"责任驱动目标设定","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色的责任对象和承诺已定时，把责任对应到实际人物目标和能识别其作用的选择。

330452｜{"id":"C01573","source":"74.5_责任","target":"3.4_责任","type":"驱动","condition":"责任感驱动行动；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，为终点状态变化提供驱动力。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：该人的责任对象、本人接受的承诺和实际履责行动。执行：把内在责任感落实为针对特定对象的行为动机。核验：核对承诺、所选行动与受益或受损对象。

333000｜{"id":"C01585","source":"75.4_义务","target":"74.5_责任","type":"转化","condition":"义务=责任；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：该人的义务来源、责任对象和已经承担的具体承诺。执行：区分外在义务与内在责任，并指出两者相接的承诺。核验：检查外在依据和本人作出的选择都有证据。

358742｜{"id":"C01707","source":"80.1_抗争","target":"3.2_执念","type":"共振","condition":"执念驱动抗争；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前提：人物明确的执念对象、面对压迫或既定困局时的抗争行动。执行：让执念与反抗行动彼此强化，写明每次抗争付出的代价与不退底线。核验：核对抗争对象是否直指阻碍执念的压迫源，且反抗加深执念。

358957｜{"id":"C01708","source":"80.1_抗争","target":"3.2_角色执念","type":"共振链","condition":"抗争与执念共振","priority":1,"effect":"抗争与执念共振","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「80.1_抗争」经「共振链」影响「3.2_角色执念」（条件：抗争与执念共振）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。"""
