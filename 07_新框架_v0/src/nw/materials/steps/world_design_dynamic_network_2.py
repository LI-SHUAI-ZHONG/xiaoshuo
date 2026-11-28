"""世界设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 资源、交易、道具与世界历史规则】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

109178｜{"id":"C00523","source":"24.1_资源类型","target":"125.1_资源库","type":"嵌套链","condition":"资源是资源库的一部分","priority":1,"effect":"资源类型是资源库的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以项目已拥有的可度量资源为前置，在资源库规则核对每类资源的实际实例、用途、取得位置和计量口径。

109377｜{"id":"C00524","source":"24.1_资源类型","target":"24.2_资源价值","type":"转化","condition":"类型决定价值；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对照本作已知资源种类、实际用途和地区供需，写明价值如何衡量及其适用范围。

109592｜{"id":"C00525","source":"24.1_资源类型","target":"24.2_资源价值层级","type":"触发链","condition":"类型决定价值","priority":1,"effect":"资源类型决定价值层级","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用价值层级时，按实有资源的用途、可替代程度和取得条件核对所属层级，保存判定依据。

109791｜{"id":"C00526","source":"24.1_资源类型","target":"25.1_货币类型","type":"触发链","condition":"资源决定货币","priority":1,"effect":"资源类型决定货币类型","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有可计价或流通的资源时，依据实际流通范围、接收方及已设兑换条件确认其中哪些充当货币。

109990｜{"id":"C00527","source":"24.1_资源类型","target":"27.2_获取方式","type":"转化","condition":"类型决定获取方式；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按资源实际类别、产地及项目已有规则记录取得途径、准入条件和需要的能力或资源。

110404｜{"id":"C00529","source":"24.1_资源类型","target":"125.8_稀缺性","type":"转化","condition":"类型影响稀缺性；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用 125.8 的稀缺性分级时，以实际资源、区域供给、需求和补充情况核对稀缺等级。

111248｜{"id":"C00533","source":"24.2_资源价值层级","target":"25.2_汇率","type":"转化","condition":"价值决定汇率；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有两种可兑换资源或货币时，用作品规定的价值口径、市场地区和已设交易条件写清汇率及适用范围。

112920｜{"id":"C00541","source":"25.1_货币类型","target":"25.2_汇率","type":"触发链","condition":"货币决定汇率","priority":1,"effect":"货币类型决定汇率","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对已采用的货币及确有兑换关系的对象给出本作的确认口径，记录兑换单位、实际流通范围和条件。

113119｜{"id":"C00542","source":"25.1_货币类型","target":"25.2_汇率","type":"转化","condition":"类型决定汇率；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已确立不同货币时，核对采用汇率的市场、时间和限制，保留已知比率或待定值。

113334｜{"id":"C00543","source":"25.1_货币类型","target":"26.1_交易类型","type":"触发链","condition":"货币决定交易类型","priority":1,"effect":"货币类型决定交易类型","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】用本作已有货币及当事人实际接受范围区分货币交易、易物或其他已设交换，注明成立条件。

113533｜{"id":"C00544","source":"25.1_货币类型","target":"26.1_交易类型","type":"转化","condition":"货币决定交易；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用货币影响交易方式时，把可用货币对应到项目的具体交易场合、接受方和通行限制。

113963｜{"id":"C00546","source":"25.2_汇率","target":"26.2_交易规则","type":"嵌套","condition":"汇率是交易规则；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在本作交易规则内记明适用的汇率、兑换时间和结算限制，给已设交换保留同一可查口径。

114178｜{"id":"C00547","source":"25.2_汇率","target":"26.2_交易规则","type":"触发链","condition":"汇率是交易规则的一部分","priority":1,"effect":"汇率是交易规则的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对项目确有的兑换型交易写明使用哪种汇率、买卖双方如何换算和当前适用的地区或时段。

114377｜{"id":"C00548","source":"25.2_汇率","target":"125.1_资源库","type":"转化","condition":"汇率是资源库部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在资源库已有货币或可兑换资源的规则中保存汇率、所涉对象与来源，供具体取得或消耗量核算。

114592｜{"id":"C00549","source":"26.1_交易类型","target":"26.2_交易规则","type":"触发链","condition":"类型决定规则","priority":1,"effect":"交易类型决定交易规则","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】交易类型已经采用时，记录哪类交易的参与资格、可交付对象和实际结算要求。

114791｜{"id":"C00550","source":"26.1_交易类型","target":"26.2_交易规则","type":"转化","condition":"类型决定规则；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对本作已有的多个交易方式分别核定条件、费用及争议处理，注明哪项规则只在相应类型适用。

115635｜{"id":"C00554","source":"26.2_交易规则","target":"26.3_交易成本","type":"触发链","condition":"规则决定成本","priority":1,"effect":"交易规则决定交易成本","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有交易规则实际产生费用时，在世界卡明确费用来源、计量口径、支付方和触发时点。

115834｜{"id":"C00555","source":"26.2_交易规则","target":"26.3_交易成本","type":"转化","condition":"规则决定成本；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据项目已有交易方式核对手续费、时间、风险等已定成本的适用情形及所涉参与者。

116049｜{"id":"C00556","source":"26.2_交易规则","target":"33.1_阶层","type":"嵌套","condition":"阶层决定交易规则；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已设阶层对交易施加限制时，按本作实际渠道、身份资格或份额核对规则何时作用及可查的例外。

117307｜{"id":"C00562","source":"27.1_资源循环","target":"27.3_稀缺性","type":"转化","condition":"循环决定稀缺性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】根据本作已设的生产、消耗和再生情况核对具体资源在哪个地点、时期出现短缺及已知补充条件。

117522｜{"id":"C00563","source":"27.1_资源循环","target":"27.3_资源稀缺性","type":"触发链","condition":"循环决定稀缺性","priority":1,"effect":"资源循环决定稀缺性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】将实际供应量、需求和资源再生速度对应到现有稀缺判据，记录同一地区与时段的变化。

118764｜{"id":"C00569","source":"27.2_资源获取方式","target":"125.15_获取方式","type":"转化","condition":"方式是资源库部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在作品实有资源的获取记录保留 125.15 所指的渠道、所需权限与成本及各渠道适用范围。

119807｜{"id":"C00574","source":"28.1_道具生命史","target":"28.2_功能边界","type":"转化","condition":"生命史决定功能边界；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据道具已知的来源、持有史和既有改造记录，核对当前功能成立的条件、限制及失效范围。

120022｜{"id":"C00575","source":"28.1_道具生命史","target":"28.2_道具功能边界","type":"触发链","condition":"生命史决定功能边界","priority":1,"effect":"道具生命史决定功能边界","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前道具的功能与生命周期有关时，把制造、交接、磨损或升级的相应事件对应到可用功能和实际边界。

120850｜{"id":"C00579","source":"28.2_功能边界","target":"28.3_代价机制","type":"转化","condition":"边界决定代价；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有道具边界及对应开销时，在规则中核对功能生效范围、成本条件、实际支付方和失效情形。

121065｜{"id":"C00580","source":"28.2_功能边界","target":"30.1_功能限定","type":"转化","condition":"边界需限定；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将道具已经确立的功能边界落实为可逐项查对的物件规则，注明真实适用对象、范围、资源或次数条件。

121495｜{"id":"C00582","source":"28.2_道具功能边界","target":"28.3_道具代价机制","type":"触发链","condition":"边界决定代价","priority":1,"effect":"功能边界决定代价机制","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用道具功能与代价的关系时，把实际开启条件、预计损失、发生时点和可用范围对应到一道具体规则。

122108｜{"id":"C00585","source":"28.3_代价机制","target":"28.4_成瘾性","type":"转化","condition":"代价决定成瘾；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作明确某类道具使用条件会形成依赖时，写清实际获得的收益、反复使用的原因及依赖的可见程度与范围。

122737｜{"id":"C00588","source":"28.3_道具代价机制","target":"28.4_道具成瘾性","type":"触发链","condition":"代价决定成瘾性","priority":2,"effect":"代价机制决定成瘾性","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对已设道具依赖机制，核对哪类代价和使用条件确会改变反复使用的选择，在世界规则保存可查的触发和限制。

127339｜{"id":"C00610","source":"29.3_道具反功能","target":"28.3_道具代价机制","type":"嵌套链","condition":"反功能是代价的一种","priority":1,"effect":"道具反功能是代价机制的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】采用反功能作为道具的一项代价时，在既有规则标明具体负面效果、发生条件、受影响方和限制。

127952｜{"id":"C00613","source":"29.4_道具进化","target":"28.1_生命史","type":"演化","condition":"进化是生命史部分；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】道具已明确发生进化时，在其生命史保留实际触发、取得或维护经过，以及已确认的功能条件变化。

128167｜{"id":"C00614","source":"29.4_道具进化","target":"28.1_道具生命史","type":"触发链","condition":"进化是生命史的一部分","priority":1,"effect":"道具进化是生命史的一部分","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】当前物件有多个已采用阶段时，用真实记录确认进化前后形态、功能和使用边界在生命史中的位置。

140603｜{"id":"C00674","source":"30.1_功能限定","target":"28.2_功能边界","type":"转化","condition":"功能限定的具体化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按本作实际道具的用途、使用范围和现有限定，核对可做什么、对谁有效以及何时会失效。

140818｜{"id":"C00675","source":"30.1_功能限定","target":"28.2_道具功能边界","type":"嵌套链","condition":"限定是边界的一部分","priority":1,"effect":"功能限定是功能边界的具体化","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】将已定功能限定填到对应的道具边界，保存实际条件、适用范围与能核实的表现。

141017｜{"id":"C00676","source":"30.1_功能限定","target":"39.6_职业限制","type":"嵌套","condition":"职业限制类似道具限制；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】采用本条类比时，对照项目已有职业条件核对实际权限和操作限制，职业规则沿用本作选定的依据。

142275｜{"id":"C00682","source":"30.3_道具制造","target":"28.1_道具生命史","type":"触发链","condition":"制造是生命史起点","priority":1,"effect":"道具制造是生命史的起点","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】依道具已给出的制造经历记下初始制造者、来源、成立条件及获得的功能，作为生命史起点。

142689｜{"id":"C00684","source":"30.3_道具制造","target":"28.1_生命史","type":"转化","condition":"制造是生命史起点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用制造是道具来源的关系时，在同一物件规则核对制成时的形态、功能、实际限制及后续持有人依据。

144162｜{"id":"C00691","source":"31.1_世界名称","target":"31.4_世界基调","type":"转化","condition":"名称影响基调；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用作品已确定的正式名称及其历史、文化或语感依据，核对它怎样呼应前置适配已经选定的世界基调。

144377｜{"id":"C00692","source":"31.1_世界名称","target":"123.19_新奇度","type":"转化","condition":"名称影响新奇度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目需要世界名称支持新奇感时，在实有名称、地理或历史中定位能提示独特规则的部分，保留既定命名理由。

144592｜{"id":"C00693","source":"31.1_世界名称","target":"129_命名术语","type":"转化","condition":"名称遵循命名规则；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依本项目已采用的命名体系，核对世界正式名、可用别称和术语关系，对应确有依据的文化或地区分布。

144807｜{"id":"C00694","source":"31.2_地理结构","target":"31.3_核心矛盾","type":"转化","condition":"地理决定矛盾；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有地形、资源与核心矛盾时，写明哪一地理条件怎样影响实际争端，给有关区域保留可查规则。

146527｜{"id":"C00702","source":"31.4_世界基调","target":"124.1_小说种类","type":"嵌套","condition":"基调暗示类型；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有本项目选定的小说种类和世界基调时，记录基调体现的本作规则、氛围或读者承诺，种类沿用前置选型。

146957｜{"id":"C00704","source":"32.1_创始期","target":"32.2_扩张期","type":"演化","condition":"创始→扩张；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品采用创始与扩张期时，以本作最早制度、已发生的扩张及实际先后写进世界历史，可查实际转换条件。

147172｜{"id":"C00705","source":"32.1_创始期","target":"34.1_先验预设","type":"转化","condition":"创始确立先验；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】某项先验规则在创始期确立时，用本作历史事实及规则作用范围记录起点、适用条件和后来怎样维持。

147602｜{"id":"C00707","source":"32.2_扩张期","target":"32.3_动荡期","type":"演化","condition":"扩张→动荡；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品已经采用扩张到动荡的转变时，对照实有拓展、资源或关系恶化的线索记录阶段变化及触发事实。

147817｜{"id":"C00708","source":"32.2_扩张期","target":"31.2_地理结构","type":"转化","condition":"扩张塑造地理；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有扩张过程影响地理格局时，核对哪些实际边界、路线或区域用途发生变化，在世界卡保留前后情况。

148032｜{"id":"C00709","source":"32.3_动荡期","target":"31.3_核心矛盾","type":"转化","condition":"动荡产生矛盾；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】动荡期已有实际利益或制度变化时，说明哪些历史事实形成项目核心矛盾及至今仍起作用的条件。

148247｜{"id":"C00710","source":"32.3_动荡期","target":"32.4_固化期","type":"演化","condition":"动荡→固化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已排定动荡过后制度固化时，以已出现的组织行动、规则改变及可回查时点记录过程。

148677｜{"id":"C00712","source":"32.4_固化期","target":"32.5_暗流期","type":"演化","condition":"固化→暗流；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用固化期和暗流期时，记录实有制度固定后的未解冲突、隐藏势力及实际时期变化依据。

148892｜{"id":"C00713","source":"32.4_固化期","target":"33.1_阶层","type":"转化","condition":"固化期固化阶层；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品设定固化期形成稳定阶层时，以已施行的资格、资源分布和实际阶层位置核对可查的历史改变。

149107｜{"id":"C00714","source":"32.4_固化期","target":"33.3_权力结构","type":"转化","condition":"固化期确立权力；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有固化期确立权力时，写明实际权力方、可支配资源和被采用的执行方式，以及当时如何形成。

149537｜{"id":"C00716","source":"32.5_暗流期","target":"32.6_裂变期","type":"演化","condition":"暗流→裂变；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有暗流转入裂变时，用实际历史事件、延续的矛盾和已发生改变的结构记录转换。

151886｜{"id":"C00727","source":"33.1_阶层划分","target":"39.1_职业","type":"转化","condition":"阶层决定职业；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作制度确实限制职业时，写出哪些阶层能进入哪些实际职业、门槛、资源条件及已定例外。

152499｜{"id":"C00730","source":"33.1_阶层划分","target":"33.2_晋升通道","type":"转化","condition":"阶层决定晋升；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】从本作已有阶层范围核对可用晋升通道、准入条件、实际成本和各渠道适用的角色。

152714｜{"id":"C00731","source":"33.1_阶层划分","target":"43.3_制度压迫","type":"触发","condition":"阶层产生压迫；且当前故事明确采用该静态关系","priority":2,"effect":"当起点条件成立时，推动终点进入下一状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有阶层差异造成制度压迫时，在世界卡具体写出执行规则、适用群体、参与方及可观察限制。

153757｜{"id":"C00736","source":"33.2_晋升通道","target":"15.1_进阶条件","type":"嵌套","condition":"晋升对应进阶；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作确有社会晋升和能力进阶的联系时，指出各自需要的条件和相互作用证据，沿用两个范围各自的制度。

154187｜{"id":"C00738","source":"33.3_权力结构","target":"33.4_执行机制","type":"转化","condition":"权力决定执行；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以现有权力方和制度规则核对谁能执行、负责哪些事项、可通过什么项目内程序以及作用范围。

【动态网络原文 · 先验、种族和构造条件、职业与制度边界】

155859｜{"id":"C00746","source":"34.1_先验预设","target":"17.1_守恒","type":"转化","condition":"先验决定物理规则；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按本项目已冻结的先验设定核对守恒适用的能量、作用边界和实际来源或去向，写入相应世界规则。

156074｜{"id":"C00747","source":"34.1_先验预设","target":"17.1_能量守恒","type":"触发链","condition":"先验决定物理规则","priority":1,"effect":"先验预设决定能量守恒","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作确立能量守恒时，说明依哪条先验规则成立、可核范围和实际例外，保留本作定下的计量口径。

156263｜{"id":"C00748","source":"34.1_先验预设","target":"34.2_不可知","type":"转化","condition":"先验决定不可知边界；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据本作已经采用的先验，明确人物可以观察的事实、已知规则及其不可知的范围。

156478｜{"id":"C00749","source":"34.1_先验预设","target":"34.2_不可知部分","type":"触发链","condition":"先验决定不可知边界","priority":1,"effect":"先验预设决定不可知边界","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】给已确认的世界预设记录实际可检验的现象及当事人仍无法知道的机制，注明哪些边界由作者确定。

156677｜{"id":"C00750","source":"34.1_先验预设","target":"18.1_能量浓度下降","type":"嵌套链","condition":"先验决定老化模式","priority":2,"effect":"先验预设决定老化模式","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已设先验约束浓度下降时，用实际地区、历史变化、可见征象和已有条件核对该世界的老化过程。

156866｜{"id":"C00751","source":"34.1_先验预设","target":"35.4_不变量","type":"转化","condition":"先验决定不变量；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在世界卡把已采用的先验及对应不变量相连，说明它在已知地点、时期和对象上的实际一致性。

162081｜{"id":"C00776","source":"35.4_不变量","target":"34.1_先验","type":"转化","condition":"不变量是先验体现；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有不变量时，用实际适用范围和可查现象说明它对应的先验规则及已知观察边界。

162710｜{"id":"C00779","source":"36.1_种族类型","target":"36.2_种族基本属性","type":"触发链","condition":"类型决定属性","priority":1,"effect":"种族类型决定基本属性","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","奇幻"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】按本作已经设定的种族及实有规则，记录被采用的基本属性、适用对象差异和作者已设例外。

162898｜{"id":"C00780","source":"36.1_种族类型","target":"36.2_种族属性","type":"转化","condition":"类型决定属性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将已存在的种族与相应属性对应到世界卡，说明这些属性在已定环境、制度或能力设计中的实际作用。

163113｜{"id":"C00781","source":"36.1_种族类型","target":"39.1_职业类型","type":"嵌套链","condition":"种族决定职业","priority":1,"effect":"种族类型决定职业类型","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","奇幻"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品确有种族规则影响职业准入时，核对具体职业、明确门槛和适用人物，并保留作者给出的例外。

163301｜{"id":"C00782","source":"36.1_种族类型","target":"124.3_类型划分","type":"嵌套","condition":"种族影响小说类型；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】前置步骤已选作品类型时，用已设种族实际在本作承担的机制和叙事作用核对与冻结的读者承诺的关系，类型沿用前置选型。

163516｜{"id":"C00783","source":"36.1_种族类型","target":"39.1_职业类型","type":"嵌套","condition":"种族决定职业；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有种族与职业的限制时，在本作职业规则写清能进入的具体岗位、已定所需能力及实际例外。

163919｜{"id":"C00785","source":"36.2_种族基本属性","target":"36.3_先天限制","type":"转化","condition":"属性决定限制；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依项目确认的种族属性及适用对象，列明具体先天限制、受影响的行动及触发条件。

164134｜{"id":"C00786","source":"36.2_种族基本属性","target":"36.3_种族先天限制","type":"触发链","condition":"属性决定限制","priority":1,"effect":"种族基本属性决定先天限制","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","奇幻"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已采用某项基本属性形成限制时，将该属性的实际作用、限制范围、已知例外和可观察结果放在同一世界规则。

164537｜{"id":"C00788","source":"36.3_种族先天限制","target":"38.3_能力边界","type":"触发链","condition":"限制决定能力边界","priority":1,"effect":"种族限制决定能力边界","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","奇幻"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】给本作实有的先天限制对应实际能力范围与条件，核对在哪个环境或使用情形会达到边界。

164725｜{"id":"C00789","source":"36.3_种族先天限制","target":"38.3_能力边界","type":"转化","condition":"限制决定能力边界；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用种族限制影响能力时，明确实际受限制的能力、对象和条件，在世界卡保留角色可据以判断的表现。

165155｜{"id":"C00791","source":"36.4_种族社会嵌入","target":"33.1_阶层","type":"嵌套","condition":"种族嵌入决定阶层；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已确定本作某个种族参与某项社会制度时，核对实际阶层资格、待遇和承担的义务，保留制度成因和例外。

165370｜{"id":"C00792","source":"36.4_种族社会嵌入","target":"33.1_阶层划分","type":"嵌套链","condition":"种族嵌入决定阶层","priority":1,"effect":"种族社会嵌入决定阶层位置","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以本作已有制度、地域和实际待遇记录特定群体所处的阶层条件及能否流动，写清其实际依据。

165784｜{"id":"C00794","source":"36.4_种族社会嵌入","target":"39.1_职业","type":"嵌套","condition":"种族嵌入决定职业；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作制度确实影响某个角色的职业选择时，写清制度、实际可接受的职业范围及准入条件。

167477｜{"id":"C00802","source":"37.1_构造类型","target":"37.2_构造决定能力上限","type":"触发链","condition":"类型决定上限","priority":1,"effect":"构造类型决定能力上限","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已定构造类型及能力限度时，按真实构造特征与适用能力核对上限口径、成立条件和已设例外。

167666｜{"id":"C00803","source":"37.1_构造类型","target":"37.2_能力上限","type":"转化","condition":"类型决定上限；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以作品当前确认的构造及能力限制为准，说明什么能力达到何种边界、怎样被观察和在哪些条件下适用。

168689｜{"id":"C00808","source":"37.2_构造决定能力上限","target":"15.1_进阶条件","type":"嵌套","condition":"构造影响进阶；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作进阶规则确实使用构造上限时，在世界规则注明适用条件、突破方式和其他并列门槛。

169523｜{"id":"C00812","source":"37.4_构造与兼容性","target":"28.2_功能边界","type":"嵌套","condition":"兼容性决定道具使用；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已定义构造兼容性及关联物件时，写明何者可以使用、在哪些条件下有效以及可观察的失败范围。

170572｜{"id":"C00817","source":"37.6_构造的老化与退化","target":"18.1_浓度下降","type":"转化","condition":"构造退化伴随浓度下降；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有构造退化和环境浓度变化时，按实际时段和部位核对各自证据及本作确认的作用关系。

172240｜{"id":"C00825","source":"38.3_能力边界定义","target":"28.2_功能边界","type":"嵌套","condition":"能力边界类似道具边界；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目需要用道具边界作类比时，用双方已有条件核对同一动作在哪种对象上可用、怎样失效，保留既定能力范围。

172455｜{"id":"C00826","source":"38.3_能力边界定义","target":"30.1_功能限定","type":"嵌套","condition":"能力边界是功能限定；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】把本作确认的具体能力边界转成可查的使用条件、作用对象和限制，引用已有设定能够验证的情况。

172670｜{"id":"C00827","source":"39.1_职业类型","target":"33.1_阶层","type":"嵌套","condition":"职业决定阶层；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作确实按职业分配阶层位置时，记录具体资格、社会待遇和适用角色，以及作品已有的例外。

172885｜{"id":"C00828","source":"39.1_职业类型","target":"33.1_阶层划分","type":"嵌套链","condition":"职业决定阶层","priority":1,"effect":"职业类型决定阶层","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】用项目中的实际职业和已采用的制度对照各方准入、可支配资源与阶层作用，保留社会位置的真实来源。

175202｜{"id":"C00839","source":"39.5_职业晋升","target":"33.2_晋升通道","type":"转化","condition":"职业晋升是通道；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目已有职业晋升路径时，在相应制度记录明确门槛、认可方式、实际资源要求及适用角色。

175831｜{"id":"C00842","source":"39.6_职业功能与限制","target":"30.1_功能限定","type":"嵌套","condition":"职业功能类似道具限定；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用本作职业的职责、权限和限制比对相应功能边界，记录完成实际任务时可以使用的工作范围和已有例外。

176261｜{"id":"C00844","source":"39.7_职业与资源获取","target":"24.1_资源类型","type":"转化","condition":"职业决定资源获取类型；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作职业确影响资源资格时，写明实际在哪些地区可取得哪些资源、需走的渠道与限制。

176906｜{"id":"C00847","source":"39.8_职业与价值积累","target":"33.2_晋升","type":"转化","condition":"积累影响晋升；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作品把职业所得作为晋升条件时，核对认可的积累类型、具体门槛和并列资格，保留真实判断依据。

182249｜{"id":"C00872","source":"40.1_制造","target":"28.1_生命史","type":"转化","condition":"制造是生命史起点；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已有道具的制造起点记录实有制作者、工艺来源、可用功能和条件，给后续生命史保留依据。

184152｜{"id":"C00881","source":"40.5_技能树结构","target":"13.1_天赋等级","type":"嵌套","condition":"技能树类似天赋等级；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作把技能树与天赋等级关联时，注明各自使用的等级口径、实际解锁条件及前置设计限定的限制。

184367｜{"id":"C00882","source":"40.5_技能树结构","target":"39.5_职业晋升","type":"嵌套","condition":"技能树决定职业晋升；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】职业晋升确要求某些技能时，用已定技能树和职业门槛写清哪些能力满足哪项资格及其他并列要求。

197688｜{"id":"C00945","source":"43.3_制度压迫","target":"33.1_阶层","type":"嵌套","condition":"压迫是阶层压迫；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有制度按阶层施加限制时，在世界卡保留执行规则、具体权力方、实际受影响对象及适用范围。

201892｜{"id":"C00965","source":"43.7_身份冲突","target":"33.1_阶层","type":"嵌套","condition":"冲突是阶层冲突；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有制度性的身份冲突时，核对实际阶层规则、受到限制的资格和项目定下的例外或适用场合。"""
