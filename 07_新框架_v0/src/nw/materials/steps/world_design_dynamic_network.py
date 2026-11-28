"""世界设计步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = """【动态网络原文 · 能量变量、作用边界与适用条件】
每条列出连接原文行号、核心关系契约与当步执行边界。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

5294｜{"id":"C00025","source":"10.1_能量总量","target":"16.1_消耗速率","type":"约束","condition":"总量影响消耗；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已经确定能量消耗口径时，在世界规则保存总量、实际作用及比较尺度，供选中行动核对消耗。

6102｜{"id":"C00029","source":"10.1_能量总量","target":"10.5_力量公式","type":"嵌套","condition":"总量是公式变量；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有力量公式时，在世界规则给总量对应的变量、单位和适用范围。系数需有本作已有的明确设定。

6747｜{"id":"C00032","source":"10.2_能量纯度","target":"10.3_技巧","type":"放大","condition":"纯度影响技巧效果；且当前故事明确采用该静态关系","priority":1,"effect":"按该静态关系类型更新终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已用纯度影响技巧效果时，写清既定纯度范围、有效表现和适用条件，保留修习或已有效果的证据口径。

7151｜{"id":"C00034","source":"10.2_能量纯度","target":"10.5_力量公式","type":"嵌套","condition":"纯度是公式变量；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将项目已确立的纯度变量及其作用范围放进同一力量规则，保留实际口径、单位和可观察比较。

7366｜{"id":"C00035","source":"10.2_能量纯度","target":"13.3_转化效率","type":"嵌套","condition":"转化效率影响纯度；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目确实采用转化效率影响纯度时，用已定输入、转换和实际输出写明作用边界并区分两项参数。

8174｜{"id":"C00039","source":"10.3_能量运用技巧","target":"10.5_力量公式","type":"嵌套","condition":"技巧是公式变量；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】作者已经给出力量公式时，保存技巧的实际变量、测量范围及和总量、纯度共同使用的依据。

【动态网络原文 · 能量变量、转化路径和世界呈现】

9412｜{"id":"C00045","source":"10.4_天赋品质","target":"10.5_力量公式","type":"嵌套","condition":"天赋是公式变量；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作明确将天赋纳入力量核算时，须写明它通过储量上限、纯度转化率或技巧折算参与计算及适用边界，不得凭空增添无依据的独立乘数。

9627｜{"id":"C00046","source":"10.5_力量公式","target":"15.1_进阶四条件","type":"触发链","condition":"公式决定进阶条件","priority":1,"effect":"力量公式决定进阶","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有力量公式和进阶要求时，核对公式结果可以证明哪一项门槛，在世界卡同时保留其他已定进阶条件。

9816｜{"id":"C00047","source":"10.5_力量公式","target":"15.1_进阶条件","type":"约束","condition":"公式决定进阶；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在采用公式约束进阶的项目中，把实际计算口径、对应的核验条件和适用范围写入世界卡，前置不足的部分记入 unknowns。

10445｜{"id":"C00050","source":"11.1_游离态","target":"11.4_转化路径","type":"转化","condition":"游离态可转化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作允许从游离态转化时，在同一世界规则列明环境来源、已采用的摄取或提取路径和形成的状态。

10660｜{"id":"C00051","source":"11.1_游离态","target":"12.4_浓度分布","type":"转化","condition":"游离态决定浓度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】由项目已知的游离能量来源和聚散条件说明具体地点为何浓度不同，记下可使用的范围和比较依据。

10875｜{"id":"C00052","source":"11.1_游离态","target":"12.4_能量浓度分布","type":"触发链","condition":"游离态决定浓度","priority":1,"effect":"游离态决定能量浓度","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】用项目已设的游离态分布核对地点之间的能量浓度差异，保留可以观察或测量的指标及空间边界。

12087｜{"id":"C00058","source":"11.2_凝聚态","target":"11.4_转化路径","type":"转化","condition":"凝聚态可转化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按现有规则把凝聚态能进入的转化路径、所需条件和实际产出写入同一世界卡。

12302｜{"id":"C00059","source":"11.2_凝聚态","target":"24.1_资源类型","type":"嵌套链","condition":"凝聚态是资源类型","priority":1,"effect":"凝聚态是资源的一种","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有凝聚态资源的设定时，按本作采用的资源分类给它标出实际功能、取得条件和可供役使的形态。

12491｜{"id":"C00060","source":"11.2_凝聚态","target":"24.1_资源类型","type":"嵌套","condition":"凝聚态是资源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用凝聚态作为具体资源时，把实有实例的来源、储存和消耗条件写入世界卡，留给后续行动按需使用。

12706｜{"id":"C00061","source":"11.3_固化态","target":"11.4_转化路径","type":"转化","condition":"固化态可转化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作允许固化态提取或转换时，在原有规则记录启动条件、已知中间过程及实际产物，保留固化状态的持有边界。

12921｜{"id":"C00062","source":"11.3_固化态","target":"28.1_道具","type":"嵌套","condition":"固化态可作道具；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作允许固化态能量直接成器或嵌入道具时，写清结晶或封存条件、实物形态、可用功能与耗损边界。

13136｜{"id":"C00063","source":"11.3_固化态","target":"28.1_道具生命史","type":"转化链","condition":"固化态可作为道具","priority":2,"effect":"固化态转化为道具","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有由固化态制成的道具时，在相关世界或物件规则中写清来源、实际转化条件和所得用途，并保留沿用的持有或使用限制。

13325｜{"id":"C00064","source":"11.4_能量转化路径","target":"11.5_转化效率","type":"约束","condition":"路径决定效率；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】端点映射已核准就绪。当本项目明确采用「11.4_能量转化路径」经「约束」影响「11.5_转化效率」（条件：路径决定效率）时，绑定具体实体、前置证据与作用边界执行，并在同稿核验前后状态变化。

13540｜{"id":"C00065","source":"11.4_能量转化路径","target":"27.1_资源循环","type":"嵌套链","condition":"转化是资源循环的一部分","priority":1,"effect":"能量转化是资源循环的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目确有资源循环时，标出所用转化在已设循环中的实际环节，给出上游投入和下游产物去向。

13729｜{"id":"C00066","source":"11.4_能量转化路径","target":"27.1_资源循环","type":"嵌套","condition":"转化是循环环节；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用转化与资源循环的关系时，把实际转化路径接到本作既有的生产、储存、消耗或再生环节，核对前后衔接所需条件。

20391｜{"id":"C00098","source":"12.10_临界值","target":"10.1_总量","type":"转化","condition":"临界值决定总量；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用能量临界值时，在世界卡分别记录已定阈值、储备计量单位与跨越临界点的作用范围，实际增量沿用本作的来源规则。

20606｜{"id":"C00099","source":"12.10_临界值","target":"15.1_进阶条件","type":"约束","condition":"临界值是进阶条件；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已用某项临界值作为进阶门槛时，标明该门槛核对哪种实际量，在 limits 同时保留其他已定条件。

21225｜{"id":"C00102","source":"12.10_能量临界值","target":"15.1_进阶四条件","type":"触发链","condition":"临界值是进阶条件","priority":1,"effect":"临界值是进阶的条件","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】在项目已采用的进阶规则里写明临界量对应的实际门槛、测量口径和其他并列条件，留给有关事件判断哪些已满。

21414｜{"id":"C00103","source":"12.11_能量异常","target":"19.1_异常","type":"转化","condition":"能量异常是物理例外；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作确有能量异常时，在世界卡明确它使哪条已有规律在何处或何条件下失常，写清当前可观察表现及使用边界。

21629｜{"id":"C00104","source":"12.11_能量异常","target":"34.2_不可知","type":"嵌套","condition":"异常是不可知部分；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将角色能够察觉的异常事实与本轮设计确定的解释边界分别写入世界卡和 unknowns，保留尚未知道的成因。

21844｜{"id":"C00105","source":"12.1_能量守恒","target":"11.4_能量转化路径","type":"抑制链","condition":"守恒决定转化","priority":1,"effect":"能量守恒决定转化路径","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作用守恒限制转化路径时，按项目采用的计量口径核对输入、输出与转移去向，保留可用能量的约束。

22033｜{"id":"C00106","source":"12.1_能量守恒","target":"11.4_转化路径","type":"约束","condition":"守恒决定转化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用守恒和转化的静态关系时，给具体转化路径列出实际来源、有效产出和已设损耗去向，使中间步骤可逐项对账。

22248｜{"id":"C00107","source":"12.1_能量守恒","target":"17.1_守恒定律","type":"转化","condition":"守恒的物理基础；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在本作物理基础采用守恒时，列明总量核算覆盖的对象、边界及可追查的能量来源与去向。

22463｜{"id":"C00108","source":"12.1_能量守恒","target":"17.1_能量守恒定律","type":"嵌套链","condition":"始终有效","priority":1,"effect":"能量守恒的物理基础","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以本作已有的守恒定律确定适用范围及能量转移的基本口径。原边的「始终有效」在该规则所覆盖的条件下核对。

22652｜{"id":"C00109","source":"12.2_能量流动","target":"12.4_浓度分布","type":"转化","condition":"流动决定浓度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】根据已定地形、流动方向和隔离条件说明实际区域的浓度差是如何形成或持续的，在世界卡保留对应地点。

22867｜{"id":"C00110","source":"12.2_能量流动","target":"17.2_流动规律","type":"转化","condition":"流动规律；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】按本作区分开放区域的浓度梯度散逸与阵眼/聚能核牵引，在世界卡写明实际流向、阻隔屏障与适用范围，禁止无边界的绝对单向断言。

23082｜{"id":"C00111","source":"12.2_能量流动规律","target":"12.4_能量浓度分布","type":"触发链","condition":"流动决定浓度","priority":1,"effect":"能量流动决定浓度分布","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有可用的能量流动规则时，给受影响地点记录流动前后的浓度区间与已知边界，以实际环境变化核对该联系。

23271｜{"id":"C00112","source":"12.3_传导系数","target":"12.4_浓度分布","type":"转化","condition":"传导决定浓度；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作设有不同传导介质时，用介质条件、能量来源和地形说明具体地点出现的浓度差异，保留原有比较口径。

23486｜{"id":"C00113","source":"12.3_传导系数","target":"17.3_传导系数","type":"转化","condition":"传导系数；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在世界规则沿用已确认的传导参数，核对同一介质中依该参数变化的释放延迟、感知范围或吸收速度，保留已知适用条件。

23701｜{"id":"C00114","source":"12.3_能量传导系数","target":"12.4_能量浓度分布","type":"触发链","condition":"传导影响浓度","priority":2,"effect":"传导系数影响浓度","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作明确传导系数影响浓度时，以实际材料或区域比较传导差异怎样改变可观察的聚散，比较尺度采用项目已定值。

23890｜{"id":"C00115","source":"12.4_浓度分布","target":"11.1_游离态","type":"转化","condition":"浓度决定游离态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】把已有浓度分布与可感知或可吸收的游离态条件对应到具体地点，保留真实的能量来源和可用范围。

24105｜{"id":"C00116","source":"12.4_浓度分布","target":"24.1_资源","type":"转化","condition":"浓度决定资源；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已设能量浓度分布决定资源生成或富集时，在世界卡将具体地点的浓度档位与实际产出的资源种类、品级及可采范围对应。

24535｜{"id":"C00118","source":"12.4_能量浓度分布","target":"11.1_游离态","type":"触发链","condition":"浓度决定游离态","priority":1,"effect":"浓度决定游离态分布","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已设浓度条件影响游离态分布时，把各地点的浓度和游离能量实际可观察差异对应起来，采用已有机制边界。

24724｜{"id":"C00119","source":"12.4_能量浓度分布","target":"24.1_资源类型","type":"嵌套链","condition":"浓度决定资源","priority":1,"effect":"浓度决定资源分布","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有浓度地图和资源类别时，标出实际可获得资源的地点与成立条件，类别沿用本作已定口径，给后续探索明确依据。

25102｜{"id":"C00121","source":"12.5_浓度时间变化","target":"12.6_潮汐","type":"转化","condition":"时间变化产生潮汐；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用浓度时间变化形成潮汐时，在世界卡列明本作周期、可观察的浓度变化和适用时间窗。

25532｜{"id":"C00123","source":"12.5_能量浓度时间变化","target":"12.6_能量潮汐","type":"触发链","condition":"时间变化产生潮汐","priority":1,"effect":"时间变化产生能量潮汐","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】根据本作已设的时间变化证据明确何种周期构成潮汐，保留适用地点、可观察峰谷和持续时段。

26125｜{"id":"C00126","source":"12.6_能量潮汐","target":"17.6_潮汐","type":"转化","condition":"潮汐物理定义；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已有能量潮汐时，用实际周期、影响范围和确认的成因写出潮汐定义，保留已知与待确认因素。

26770｜{"id":"C00129","source":"12.7_能量感知规则","target":"12.8_能量感知范围","type":"触发链","condition":"规则决定范围","priority":1,"effect":"感知规则决定感知范围","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】在本作既有能量感知规则中登记哪些因素改变距离和精度，记明适用环境和触发条件，人物值依据人物已定能力。

27982｜{"id":"C00135","source":"12.9_能量干扰","target":"12.3_传导系数","type":"转化","condition":"干扰影响传导；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目明确干扰改变介质传导时，记录干扰出现的实际条件、受影响区域及传导变化，区分世界卡中各机制的作用范围。

28197｜{"id":"C00136","source":"12.9_能量干扰规则","target":"12.7_能量感知规则","type":"抑制链","condition":"干扰影响感知","priority":1,"effect":"干扰影响能量感知","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已确认的干扰作用于能量感知时，写明干扰来源、发生条件、影响的感知特征及本作已有的恢复边界。

31993｜{"id":"C00154","source":"123.19_世界观新奇度","target":"31.1_世界名称","type":"转化","condition":"新奇度与世界名称相关；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用本作已定地理、历史或规则核对世界正式命名，并写出名称可提示的具体新意及其实际依据。

32208｜{"id":"C00155","source":"123.19_世界观新奇度","target":"35.3_半透明","type":"转化","condition":"新奇度与半透明相关；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作确有新奇设定且采用半透明呈现时，在世界卡明确当下可理解的规则、以后才答的问题及能够辨认的迹象。

【动态网络原文 · 作品资源、命名、天赋及进阶规则】

39486｜{"id":"C00189","source":"125.1_资源库","target":"24.1_资源类型","type":"触发链","condition":"资源库包含资源","priority":1,"effect":"资源库是资源的集合","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】以作品当前已有的可度量资源建立相应记录，按实际功能和用处分清资源类别，给出可查的来源或计量依据。

40083｜{"id":"C00192","source":"129.1_命名规则","target":"31.1_世界名称","type":"嵌套链","condition":"命名规则影响世界名称","priority":2,"effect":"命名规则决定世界名称","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】现有世界需要定名时，依作者已采用的命名规则和本作文化、地理或历史，记录正式名称及其可追溯的理由。

40712｜{"id":"C00195","source":"13.1_天赋等级","target":"15.1_进阶条件","type":"约束","condition":"等级是进阶条件；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用天赋分级作为进阶门槛时，在世界卡写明相关等级、适用阶段与其他已设的进阶条件。

40927｜{"id":"C00196","source":"13.1_天赋等级","target":"33.1_阶层","type":"嵌套","condition":"等级影响阶层；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】制度确实按天赋等级分配资格时，用实际组织、资源或角色说明准入规则怎样奏效，保留已有替代条件。

43781｜{"id":"C00210","source":"13.5_占比分布","target":"33.1_阶层","type":"嵌套","condition":"分布决定阶层；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有天赋比例及阶层制度时，分别写清各档比例和制度分配资格、地位或资源的实际规则，保留二者有关的证据。

43996｜{"id":"C00211","source":"13.5_占比分布","target":"33.1_阶层划分","type":"嵌套链","condition":"天赋分布决定阶层","priority":2,"effect":"天赋分布影响阶层结构","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已把天赋分布纳入阶层设计时，用已有群体比例和制度运行的例证，核对它实际影响哪些阶层位置。

44185｜{"id":"C00212","source":"13.5_占比分布","target":"36.4_种族社会嵌入","type":"嵌套","condition":"分布决定种族地位；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据已设种族、历史和制度，核对天赋分布如何影响实际待遇或参与资格，并保留已有的群体内部差异。

50080｜{"id":"C00241","source":"14.6_结晶期","target":"15.1_进阶四条件","type":"触发链","condition":"结晶期是进阶标志","priority":1,"effect":"结晶期是进阶的标志","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作给出结晶阶段和进阶判据时，用已有现象确认它标志哪个阶段，在世界卡并列保留其余需要满足的条件。

50269｜{"id":"C00242","source":"14.6_结晶期","target":"15.1_进阶条件","type":"转化","condition":"结晶期是进阶标志；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用结晶作为进阶标志时，按本作已定的外部可见特征写清判定范围，并记录与其他进阶门槛的关系。

【动态网络原文 · 身份阶层、能量机制、资源与生态】

71757｜{"id":"C00344","source":"151.1_身份","target":"33.1_阶层划分","type":"嵌套链","condition":"身份决定阶层","priority":1,"effect":"身份决定阶层划分","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】制度已经按身份划分阶层时，在世界卡记录身份所带来的实际位置、准入或待遇，并保留作品已有的例外。

72171｜{"id":"C00346","source":"151.1_身份定义","target":"33.1_阶层","type":"嵌套","condition":"身份=阶层；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用项目已建立的制度说明何种具体身份会影响阶层资格或地位，并写清可查的作用范围。

85294｜{"id":"C00409","source":"17.1_能量守恒","target":"11.4_转化","type":"约束","condition":"守恒决定转化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作采用守恒约束转化时，在世界卡把实际路径每步的投入、转移、有效产出及损耗去向逐项对齐。

85509｜{"id":"C00410","source":"17.1_能量守恒","target":"12.1_守恒","type":"转化","condition":"守恒的物理基础；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据项目已设物理边界核对守恒适用的范围、计量对象及转化转移的条件，给相关规则注明可追查的量。

85724｜{"id":"C00411","source":"17.1_能量守恒定律","target":"11.4_能量转化路径","type":"抑制链","condition":"守恒决定转化","priority":1,"effect":"守恒定律决定转化路径","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】确认本作能量守恒定律及所覆盖的系统后，明确哪些转化路径能在已知输入和输出条件下发生、如何守恒。

85913｜{"id":"C00412","source":"17.2_流动规律","target":"12.2_流动","type":"转化","condition":"流动规律；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据本作已确认的流向、浓度差和隔离规则连接物理层与可见的流动表现，保留同一地点的观察依据。

86128｜{"id":"C00413","source":"17.2_流动规律","target":"17.4_浓度分布","type":"转化","condition":"流动决定分布；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用本作已经采用的流向和地形边界说明实际区域的浓度差如何形成、变化或保持。

86343｜{"id":"C00414","source":"17.2_能量流动规律","target":"12.4_能量浓度分布","type":"触发链","condition":"流动决定浓度","priority":1,"effect":"流动规律决定浓度分布","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已设能量流动会改变浓度时，在实际地点核对流动的范围、强弱及可查的浓度变化。

86532｜{"id":"C00415","source":"17.3_传导系数","target":"12.3_传导","type":"转化","condition":"传导系数；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】在世界规则连接物理层传导系数与实际介质中的导能表现，记录同一介质参数变化对应的传输速度、损耗或阻隔边界。

86747｜{"id":"C00416","source":"17.3_传导系数","target":"17.4_浓度分布","type":"转化","condition":"传导决定分布；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】分别记录本作已设的介质、传导参数和来源，核对不同区域实际如何聚散以及浓度比较的范围。

86962｜{"id":"C00417","source":"17.3_能量传导系数","target":"12.9_能量干扰规则","type":"触发链","condition":"传导影响干扰","priority":2,"effect":"传导系数影响干扰规则","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】项目已明确传导会影响干扰时，用实有介质、干扰来源与作用范围核对受影响的传输、感知或使用条件。

87151｜{"id":"C00418","source":"17.4_浓度分布","target":"12.4_浓度","type":"转化","condition":"浓度分布；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对照两处已采用的浓度分布规则，保留同一实际区域的浓度边界、测量口径和变化条件。

87366｜{"id":"C00419","source":"17.4_浓度分布","target":"24.1_资源","type":"转化","condition":"浓度决定资源；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】依据物理层空间浓度分布核对各区域实际形成的资源矿脉或产区边界，保留同地浓度读数与产出条件。

87581｜{"id":"C00420","source":"17.4_能量浓度空间分布","target":"24.1_资源类型","type":"嵌套链","condition":"浓度决定资源","priority":1,"effect":"空间分布决定资源分布","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】已有空间浓度和资源类别时，在具体地区记录哪些资源实际可达、哪里受限，分类仍循作品所定标准。

87770｜{"id":"C00421","source":"17.5_浓度时间变化","target":"12.5_浓度变化","type":"转化","condition":"浓度时间变化；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】将同一实际地点的浓度时间变化与已设周期和观察口径对应，明确峰谷时点或影响范围的证据。

88389｜{"id":"C00424","source":"17.6_能量潮汐","target":"12.6_潮汐","type":"转化","condition":"潮汐物理定义；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对照本作已设潮汐的原因、周期和影响尺度，把 17.6 与 12.6 在同一实际规则中的对应关系说明清楚。

88819｜{"id":"C00426","source":"18.1_能量浓度下降","target":"11.1_游离态","type":"转化","condition":"浓度下降→游离态减少；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知某地浓度正在下降时，按本作设定核对该地游离态能量的来源、可用量及其实际减少的范围。

89034｜{"id":"C00427","source":"18.1_能量浓度下降","target":"18.3_能量源衰竭","type":"演化","condition":"浓度下降→衰竭；且当前故事明确采用该静态关系","priority":2,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已采用能量源衰竭的规律时，以已有浓度记录、持续变化和明确阈值判断何种现象可作为衰竭迹象。

89249｜{"id":"C00428","source":"18.1_能量浓度下降","target":"21.4_熵增","type":"触发链","condition":"浓度下降是熵增","priority":2,"effect":"能量浓度下降是熵增的表现","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】作品采用生态熵增解释能量下降时，记录真实受影响的环境、已知变化顺序及可复查的浓度或资源征象。

89438｜{"id":"C00429","source":"18.2_资源产量减少","target":"24.3_价值动态","type":"转化","condition":"产量减少→价值上升；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有产量减少及实在的市场条件时，用实际供给、需求和替代资源核对价值怎样变化，保留时间与地区限制。

90676｜{"id":"C00435","source":"18.4_潮汐减弱","target":"12.6_潮汐","type":"演化","condition":"潮汐幅度缩小；且当前故事明确采用该静态关系","priority":1,"effect":"当起点持续或变化时，推动终点按阶段发生状态变化。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以本作已采用的潮汐规则为依据，对照实际地点的峰谷、周期和可查前后量，核对哪些范围确有减弱。

91106｜{"id":"C00437","source":"19.1_能量异常","target":"12.9_能量干扰规则","type":"触发链","condition":"异常是干扰的一种","priority":1,"effect":"能量异常是干扰规则的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有异常影响传导、能量辨识或使用时，在实际干扰规则标出异常的激活条件、范围及可观察作用。

91295｜{"id":"C00438","source":"19.1_能量异常","target":"34.2_不可知","type":"嵌套","condition":"异常是不可知；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对已经确认的异常分别保存可看见的现象、已有解释和当事人仍不可知的机制，沿用前置限定的范围。

91510｜{"id":"C00439","source":"19.1_能量异常","target":"19.3_代价","type":"绑定","condition":"异常伴随代价；且当前故事明确采用该静态关系","priority":2,"effect":"当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已经有物理例外及代价时，记清适用对象、触发、支付方和已定损失或限制，供实际选用时核对。

91725｜{"id":"C00440","source":"19.2_核心道具例外行为","target":"28.2_道具功能边界","type":"触发链","condition":"例外是边界的一部分","priority":1,"effect":"核心道具例外行为是道具功能边界的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】核心道具确有例外行为时，给物件规则标明被改变的已有规律、可实现效果、适用条件与会失效的情况。

91914｜{"id":"C00441","source":"19.2_道具例外","target":"28.2_功能边界","type":"转化","condition":"道具是例外；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已采用道具例外及其功能边界时，核对实际物件能做什么、何时有效，保留项目当前允许的次数、范围或成本条件。

92774｜{"id":"C00445","source":"19.3_例外的代价","target":"28.3_道具代价机制","type":"触发链","condition":"例外伴随代价","priority":1,"effect":"例外行为伴随代价","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】在本作确立道具例外的代价规则时，核对由谁在何时支付、哪类损失会发生及适用的物件边界。

97452｜{"id":"C00467","source":"20.1_生态系统层级","target":"24.1_资源类型","type":"嵌套","condition":"生态决定资源分布；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】以已有生态层级及实际地理为依据，写明某类资源来自哪一层、在哪些区域可获得和依赖哪些条件。

97667｜{"id":"C00468","source":"20.1_生态系统层级","target":"24.1_资源类型","type":"嵌套链","condition":"生态决定资源","priority":1,"effect":"生态系统决定资源类型","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已按生态层级划分资源时，为真实的资源实例明确所在环节、实际用途及当前获取或补充的边界。

97866｜{"id":"C00469","source":"20.1_生态系统层级","target":"31.2_地理结构","type":"嵌套","condition":"地理决定生态；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】对照已设地理、气候和可达条件，核对实际地区能形成什么生态层级，保存角色出入该区域的既有边界。

98081｜{"id":"C00470","source":"20.1_生态系统层级","target":"31.2_地理结构","type":"触发链","condition":"地理决定生态","priority":1,"effect":"地理结构决定生态系统","direction":"双向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】给已有地理结构和生态系统的关联保留可观察的地形、流向与生境依据，注明是哪个地理条件影响哪项生态分布。

99538｜{"id":"C00477","source":"20.3_资源流动路径","target":"24.1_资源类型","type":"触发链","condition":"流动路径决定资源分布","priority":1,"effect":"资源流动路径决定资源分布","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】对已有资源流动路径，记录实际产地、运输或流通方式、落点和受限制地区，分类用本作已采用的口径。

99737｜{"id":"C00478","source":"20.3_资源流动路径","target":"24.1_资源类型","type":"转化","condition":"路径决定资源分布；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】用已设流向与沿途限制核对一类资源在哪些真实地点会出现、被消耗或难以获得，保存范围依据。

99952｜{"id":"C00479","source":"20.3_资源流动路径","target":"27.1_资源循环","type":"嵌套","condition":"流动是循环环节；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，终点作为起点的一部分参与当前状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已有资源循环时，标明当前流动路径在生产、流通、储存或消耗中的实际环节及其相接条件。

100581｜{"id":"C00482","source":"20.4_资源生产-消费平衡","target":"27.1_资源循环","type":"嵌套链","condition":"平衡是循环的一部分","priority":1,"effect":"生产-消费平衡是资源循环的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已有生产和消费循环时，在同一资源规则核对真实投入、产量、消耗、回流及相应时间段。

100780｜{"id":"C00483","source":"20.4_资源生产消费平衡","target":"27.3_稀缺性","type":"转化","condition":"平衡决定稀缺性；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】已知生产与消费数量或趋势时，对实际地区和时期核对短缺、平衡或盈余，明确已有替代资源和各自口径。

101624｜{"id":"C00487","source":"21.1_均衡态","target":"31.4_世界基调","type":"转化","condition":"均衡决定基调；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】项目用已有均衡影响世界基调时，依据实有生态与社会运行规律给出可见的稳定性、日常秩序和已确认的基调。

103113｜{"id":"C00494","source":"21.3_寻找新均衡","target":"21.4_熵增","type":"触发链","condition":"寻找过程中存在熵增","priority":2,"effect":"寻找新均衡过程中存在熵增","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作已用熵增来解释寻找新均衡的过程时，记录实际阶段中的资源耗散、结构或浓度变化及其可观察条件。

103527｜{"id":"C00496","source":"21.4_熵增","target":"18.1_浓度下降","type":"转化","condition":"熵增导致浓度下降；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立并满足转化条件时，将起点状态转为终点状态。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"generated_from_static":true,"needs_review":false,"status":"derived"}
【本步用法】本作已设熵增机制会使浓度下降时，在世界卡保留实际地点、时段和适用边界，核对持续变化的证据。

103742｜{"id":"C00497","source":"21.4_熵增","target":"18.1_能量浓度下降","type":"共振链","condition":"熵增与能量下降共振","priority":2,"effect":"熵增与能量浓度下降共振","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事"],"generated_from_static":false,"needs_review":false,"status":"original"}
【本步用法】本作同时采用熵增和能量浓度下降时，用具体区域、相同观测期和既有机制核对两项变化如何相互对应。"""
