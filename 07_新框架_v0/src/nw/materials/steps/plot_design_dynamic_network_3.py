"""剧情设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 道具与悬念、人物驱动力和历史线】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

111463｜{"id":"C00534","source":"24.2_资源价值层级","target":"43.1_资源争夺","type":"触发链","condition":"价值决定争夺激烈程度","priority":1,"effect":"资源价值决定争夺激烈程度","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有争夺双方和具体资源时，用相对价值、难以替代之处和双方各自能承担的实际代价安排争夺升级。

111662｜{"id":"C00535","source":"24.2_资源价值层级","target":"43.1_资源争夺","type":"触发","condition":"价值决定争夺烈度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用价值影响争夺烈度时，按本作实际需求和前置行动核对何时愿意继续争夺、所付成本及实际后果。

119592｜{"id":"C00573","source":"27.3_资源稀缺性","target":"125.20_稀缺性管理","type":"转化","condition":"稀缺需管理；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用稀缺性管理来推动剧情时，以具体资源缺口、角色选择和后继补给安排冲突升级或缓解。

120436｜{"id":"C00577","source":"28.1_道具生命史","target":"45.1_伏笔埋设","type":"嵌套链","condition":"生命史是伏笔来源","priority":1,"effect":"道具生命史是伏笔来源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】道具生命史已作为伏笔来源时，用已知来源、旧痕迹或交接安排读者可看到的线索，并保留后续验证位置。

120635｜{"id":"C00578","source":"28.1_道具生命史","target":"45.1_伏笔","type":"嵌套","condition":"生命史是伏笔来源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「28.1_道具生命史」经「嵌套」影响「45.1_伏笔」（条件：生命史是伏笔来源）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

122323｜{"id":"C00586","source":"28.3_代价机制","target":"44.3_爽点-代价","type":"共振","condition":"代价与爽点同步；且当前故事明确采用该静态关系","priority":1,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选段落要同时交付道具回报及代价时，用真实人物选择、发生时点和后效组织同一事件的因果。

122538｜{"id":"C00587","source":"28.3_道具代价机制","target":"44.3_爽点-代价同步","type":"触发链","condition":"代价与爽点同步","priority":1,"effect":"道具代价与爽点同步","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】道具的回报与代价已安排同步时，在已有章场核对被兑现的期待、人物实际支付以及之后仍受哪项影响。

122936｜{"id":"C00589","source":"28.4_道具成瘾性","target":"4.1_弧光","type":"演化","condition":"成瘾影响弧光；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有依赖道具的人物弧光时，用实际使用、回避或转化的选择及后果安排人物变化。

123151｜{"id":"C00590","source":"28.4_道具成瘾性","target":"4.1_弧光五阶段","type":"触发链","condition":"成瘾影响弧光","priority":2,"effect":"道具成瘾性影响弧光","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目采用弧光阶段表现对道具的依赖变化时，把具体节点落实到人物使用行为、付出的代价和可看到的后续不同。

123350｜{"id":"C00591","source":"28.4_道具成瘾性","target":"76.1_道德困境","type":"触发","condition":"成瘾产生困境；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】既有道具依赖确实形成两难时，以项目人物可接受或难以接受的选项及各自后果写出实际价值冲突。

123780｜{"id":"C00593","source":"28.5_道具记忆载体","target":"1.5_缺席者","type":"嵌套","condition":"记忆载体关联缺席者；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】道具承载项目中缺席角色的记忆时，用已定物件来源、实际知情者和出现地点安排这个人如何影响当前选择。

123995｜{"id":"C00594","source":"28.5_道具记忆载体","target":"1.5_缺席者","type":"触发链","condition":"记忆载体关联缺席者","priority":1,"effect":"道具记忆载体关联缺席者","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前道具记忆与缺席者相关时，从前文确认的关联保留谁能读到什么、何时触及以及后续可验证的事实。

124194｜{"id":"C00595","source":"28.5_道具记忆载体","target":"45.1_伏笔","type":"嵌套","condition":"记忆载体是伏笔来源；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「28.5_道具记忆载体」经「嵌套」影响「45.1_伏笔」（条件：记忆载体是伏笔来源）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

124409｜{"id":"C00596","source":"28.5_道具记忆载体","target":"45.1_伏笔埋设","type":"嵌套链","condition":"记忆载体是伏笔来源","priority":1,"effect":"道具记忆载体是伏笔来源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已把道具的记忆选为伏笔时，在已定章场安排真实的记忆痕迹与读者能辨认的部分，保留以后确认的事件。

124608｜{"id":"C00597","source":"28.5_道具记忆载体","target":"32.7_未写明的历史","type":"嵌套","condition":"记忆载体关联历史；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已有未写明历史及相应记忆物件时，安排当下可感的历史痕迹、实际披露对象与项目已经确定的保留部分。

124823｜{"id":"C00598","source":"28.6_道具象征化","target":"111.1_核心象征物","type":"触发链","condition":"道具可成为象征","priority":1,"effect":"道具成为核心象征物","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】某件道具已被选为核心象征时，用实际使用、传递或失去的前后事件建立它与作品命题的联系。

125022｜{"id":"C00599","source":"28.6_道具象征化","target":"111.1_核心象征物","type":"转化","condition":"道具可成象征；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用道具象征化时，在项目实际章场核对物件反复出现时经历的变化和人物反应，标出象征意义的形成位置。

125237｜{"id":"C00600","source":"28.6_道具象征化","target":"63.1_核心主题","type":"绑定","condition":"象征连接主题；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已定主题和道具功能时，把选定物件在关键角色选择、代价或收束中的实际作用对应到主题落点。

127538｜{"id":"C00611","source":"29.3_道具反功能","target":"143.1_不确定性","type":"触发","condition":"反功能制造不确定性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有道具反功能和使用事件时，根据其实际边界安排人物可知的风险、仍成立的多种后果和以后能核对的结果。

127753｜{"id":"C00612","source":"29.3_道具反功能","target":"143.1_不确定性","type":"触发链","condition":"反功能产生不确定性","priority":2,"effect":"道具反功能制造不确定性","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】道具的不可靠性确被用来保持悬念时，以前文可见的反功能迹象说明读者为何仍不能确定本次使用的结果。

128366｜{"id":"C00615","source":"29.4_道具进化","target":"4.1_弧光","type":"演化","condition":"道具进化伴随弧光；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已将道具进化与人物成长联系时，把实际道具变化对应到人物选择及结果，分别保留物件变化和角色弧光的证据。

129656｜{"id":"C00621","source":"3.1_尊重欲望","target":"44.1_压抑","type":"触发","condition":"长期压制；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「3.1_尊重欲望」经「触发」影响「44.1_压抑」（条件：长期压制）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

131161｜{"id":"C00628","source":"3.1_自我实现","target":"42.1_引力中心","type":"绑定","condition":"绑定主线；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「3.1_自我实现」经「绑定」影响「42.1_引力中心」（条件：绑定主线）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

132371｜{"id":"C00634","source":"3.2_执念","target":"130_核心悬念","type":"绑定","condition":"一致；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已定人物执念与核心悬念时，用具体执念、已知线索和所选事件明确两者因何相连、何时影响选择。

133016｜{"id":"C00637","source":"3.2_执念","target":"4.1_弧光","type":"演化","condition":"驱动；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知执念产生人物变化时，用已有阻力、选择和实际后果核对它在弧光各阶段的不同作用。

133231｜{"id":"C00638","source":"3.2_角色执念","target":"130_核心悬念","type":"触发链","condition":"执念与核心悬念相关","priority":1,"effect":"执念与核心悬念绑定，执念的答案即核心悬念的答案","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已经让执念与核心悬念相扣时，用实际角色追问、可辨线索和揭示事件核对两者在何处取得共同答案。

133828｜{"id":"C00641","source":"3.2_角色执念","target":"4.1_弧光五阶段","type":"触发链","condition":"执念被挑战或强化","priority":1,"effect":"执念推动弧光发展，执念的变化即弧光的变化","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】角色执念经实际事件被挑战或强化时，用当事人的具体选择和可观察差异核对它怎样推动某个已有弧光节点。

134027｜{"id":"C00642","source":"3.2_角色执念","target":"44.1_爽点三压抑","type":"共振链","condition":"执念被压抑","priority":1,"effect":"执念的压抑感在爽点释放时被一并释放","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】端点映射已核准就绪。当本项目明确采用「3.2_角色执念」经「共振链」影响「44.1_爽点三压抑」（条件：执念被压抑）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

135022｜{"id":"C00647","source":"3.3_角色野心","target":"123.4_黄金三章","type":"触发链","condition":"野心在开篇被建立","priority":2,"effect":"野心在开篇建立读者对角色成长的期待","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作采用黄金三章并在开篇确立角色野心时，把野心落实为可见目标、行动及读者能辨的成长期待。

135221｜{"id":"C00648","source":"3.3_野心","target":"154.1_主线","type":"绑定","condition":"动力；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】角色野心已是主线动力时，以具体长程目标、遭遇的实际阻力和当事人选择支撑主线的推进节点。

139178｜{"id":"C00667","source":"3.6_角色情绪管控","target":"155.1_情绪缓冲","type":"触发链","condition":"高强度情绪后","priority":2,"effect":"情绪管控需要情绪缓冲来恢复","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】高强度情节后本作采用读者情绪缓冲时，用实际情绪应对、停顿或后果安排读者消化的段落，人物恢复仍依已有状态证据。

141431｜{"id":"C00678","source":"30.2_功能边界测试","target":"44.3_爽点-代价同步","type":"触发链","condition":"突破伴随代价","priority":2,"effect":"边界突破伴随代价","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已将边界突破安排为一次回报时，用已知测试、人物选择、可见突破及实际损失定位同一事件的因果。

142060｜{"id":"C00681","source":"30.2_边界测试突破","target":"44.3_爽点-代价","type":"共振","condition":"突破伴随代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目将道具边界突破作为情节回报时，把验证条件、人物实际支付和突破结果落实到已定事件顺序。

143947｜{"id":"C00690","source":"30.5_道具失效转化","target":"44.3_爽点-代价","type":"共振","condition":"失效伴随代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品将失效与代价纳入同一段落时，用实际道具选择、功能损失和人物后继选择核对因果和读者已获的回报。

145452｜{"id":"C00697","source":"31.3_核心矛盾","target":"130_核心悬念","type":"绑定","condition":"矛盾是悬念根源；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者明确核心矛盾构成悬念来源时，用已有冲突和实际线索安排读者能发现的问题及后续回应。

145667｜{"id":"C00698","source":"31.3_核心矛盾","target":"42.1_引力中心","type":"绑定","condition":"矛盾是引力中心；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确立的核心矛盾实际牵引当前线索和人物时，在实际事件节点核对它如何影响选择和后果。

146742｜{"id":"C00703","source":"31.4_世界基调","target":"64.1_读者情绪","type":"转化","condition":"基调影响读者情绪基线；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「31.4_世界基调」经「转化」影响「64.1_读者情绪」（条件：基调影响读者情绪基线）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

147387｜{"id":"C00706","source":"32.1_创始期","target":"111.1_象征","type":"转化","condition":"创始产生象征；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已选核心象征确实源于创始期时，用项目已有的物件或事件说明其初始意义及后来何时能被读者识别。

149322｜{"id":"C00715","source":"32.5_暗流期","target":"130_核心悬念","type":"绑定","condition":"暗流期隐藏悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已定核心悬念源于暗流期时，把真实幕后事实、前文可见痕迹和后续解开问题的场合对应到事件。

149752｜{"id":"C00717","source":"32.5_暗流期","target":"42.1_引力中心","type":"绑定","condition":"暗流期是故事发生时代；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已设故事发生于暗流期时，沿本作实际时间范围把人物当前目标、所遇阻碍与时代处境接到已定引力中心。

149967｜{"id":"C00718","source":"32.5_暗流期","target":"23.1_隐蔽流","type":"嵌套","condition":"暗流期隐蔽流运作；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】暗流期确有隐蔽流运作时，用已有时间线明确幕后行为、实际知情和前段可见线索，给后续揭示留位。

150182｜{"id":"C00719","source":"32.6_裂变期","target":"31.3_核心矛盾","type":"解决","condition":"裂变解决矛盾；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并完成作用时，推动终点的问题状态收敛。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】裂变事件已承担解决项目核心矛盾时，按本作实际选择、冲突前后和受影响方核对解决范围及后效。

150397｜{"id":"C00720","source":"32.6_裂变期","target":"32.7_未写明的历史","type":"演化","condition":"裂变→未写明的历史；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作有裂变后仍仅被提及的历史时，选择现有事件可呈现的痕迹，把哪些事实能知道及仍待保留的细节分别记明。

150612｜{"id":"C00721","source":"32.6_裂变期","target":"44.6_大爽点","type":"共振","condition":"裂变期是大爽点位置；且当前故事明确采用该静态关系","priority":2,"effect":"当起点与终点同时成立时，放大双方的共同状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】裂变期已安排为大回报时，用真实前置压力、转折行动和可核结果定位角色及读者得到的回应。

150827｜{"id":"C00722","source":"32.7_未写明的历史","target":"130_核心悬念","type":"绑定","condition":"未写明的历史是悬念；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已定未写明历史与核心悬念相关时，明确前文可见痕迹、实际问题和已选回应，保留作者确认不揭示的范围。

151042｜{"id":"C00723","source":"32.7_未写明的历史","target":"45.1_伏笔","type":"嵌套","condition":"未写明的历史是伏笔来源；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「32.7_未写明的历史」经「嵌套」影响「45.1_伏笔」（条件：未写明的历史是伏笔来源）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

153558｜{"id":"C00735","source":"33.2_晋升通道","target":"4.1_弧光五阶段","type":"嵌套链","condition":"晋升决定弧光路径","priority":1,"effect":"晋升通道决定弧光路径","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目用晋升经历推进已有弧光时，将通过或未通过门槛的实际事件与角色看法、决定和行为变化对应起来。

153972｜{"id":"C00737","source":"33.2_晋升通道","target":"4.1_弧光","type":"转化","condition":"通道决定弧光路径；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已定晋升路径对角色弧光有作用时，按实际选择、付出和后果定位人物改变在哪个可见节点出现。"""
