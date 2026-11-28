"""道具交互、制作与资源流向的原始动态连接。"""

MATERIAL = """## 物件操作与真实结果的接续

使用本场选中事件、实际前值、人物动作和验证结果，核对本场哪些性质、持有、数量或权限发生了变化。

### C00601
125452｜{"id":"C00601","source":"29.1_道具与角色交互","target":"52.3_触觉描写","type":"触发链","condition":"交互通过触觉呈现","priority":1,"effect":"道具交互通过触觉描写呈现","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"表达层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"29.1_道具与角色交互","original_target":"52.3_触觉描写","normalized_source":"29.1_道具与角色交互","normalized_target":"52.3_触觉描写","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】沿本场已选道具接触动作核对实际触感与原前值，角色可感反应须来自本作已有条件。触感只用于表现时沿现有表达安排，实际状态变化仍需对应事件。
### C00605
126296｜{"id":"C00605","source":"29.1_道具与角色交互","target":"7.4_情感与身体反应","type":"触发链","condition":"交互产生身体反应","priority":2,"effect":"道具交互产生身体反应","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"引擎层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"29.1_道具与角色交互","original_target":"7.4_情感与身体反应","normalized_source":"29.1_道具与角色交互","normalized_target":"7.4_情感与身体反应","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】以本场真实接触为触发，对照实际原前值记录可确认的身体或情感反应，当前视角能知的范围及变化延续各有依据。
### C00608
126925｜{"id":"C00608","source":"29.2_道具与环境交互","target":"83.1_探索","type":"触发链","condition":"交互驱动探索","priority":2,"effect":"道具与环境交互驱动探索","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"交互层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"29.2_道具与环境交互","original_target":"83.1_探索","normalized_source":"29.2_道具与环境交互","normalized_target":"83.1_探索","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】按已选环境交互核对具体开路、受阻或发现及事件原前值。探索行为只沿人物真实能到达的路径，新的资源或所知须由实际接触确认。
### C00682
142275｜{"id":"C00682","source":"30.3_道具制造","target":"28.1_道具生命史","type":"触发链","condition":"制造是生命史起点","priority":1,"effect":"道具制造是生命史的起点","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"30.3_道具制造","original_target":"28.1_道具生命史","normalized_source":"30.3_道具制造","normalized_target":"28.1_道具生命史","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】只有所选工序实际形成本作物件时，以原材料前值、制造动作和成品结果记录其首次形成，未完成的工序保留中间状态。
### C00685
142904｜{"id":"C00685","source":"30.4_道具维护与升级","target":"29.4_道具进化","type":"触发链","condition":"维护是进化方式","priority":1,"effect":"道具维护与升级是进化方式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"30.4_道具维护与升级","original_target":"29.4_道具进化","normalized_source":"30.4_道具维护与升级","normalized_target":"29.4_道具进化","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】依原物前值和已选维护改动记录恢复或新增的实际部分，新增功能有独立验证。纯保养的结果按实际恢复范围处理。
### C00688
143533｜{"id":"C00688","source":"30.5_道具失效与转化","target":"28.1_道具生命史","type":"触发链","condition":"失效是生命史终点","priority":1,"effect":"道具失效与转化是生命史的终点","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"30.5_道具失效与转化","original_target":"28.1_道具生命史","normalized_source":"30.5_道具失效与转化","normalized_target":"28.1_道具生命史","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】本场所选失效或转化确已终止原物用途时，对照原状态、终止动作及余留物登记后果，可恢复的限制依本作既有条件保留。
### C00870
181835｜{"id":"C00870","source":"40.1_制造","target":"30.3_道具制造","type":"嵌套链","condition":"制造是道具来源","priority":1,"effect":"制造是道具的来源","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"40.1_制造","original_target":"30.3_道具制造","normalized_source":"40.1_制造","normalized_target":"30.3_道具制造","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】所选工序真正形成道具或中间物时，把原材料前值、实际制作及可检验结果对应，状态只记录本场已完成范围。
### C00874
182679｜{"id":"C00874","source":"40.2_制作","target":"40.3_技能学习条件","type":"触发链","condition":"制作需要技能","priority":1,"effect":"制作需要技能学习","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"生成层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"40.2_制作","original_target":"40.3_技能学习条件","normalized_source":"40.2_制作","normalized_target":"40.3_技能学习条件","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】按本场已选制作事件核对人物原技能、真实训练或操作、实际完成的检验及能力前后，已有技能用于制作和新技能学成各按证据记录。
### C01751
368074｜{"id":"C01751","source":"84.1_采集","target":"27.2_资源获取","type":"嵌套链","condition":"采集是获取方式","priority":1,"effect":"采集是资源获取方式之一","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"交互层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"84.1_采集","original_target":"27.2_资源获取","normalized_source":"84.1_采集","normalized_target":"27.2_资源获取","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】所选采集动作确已取得资源时，以原地点与可得范围为前值，核对真实所得、耗费及取得后归属，未取到的部分依当前结果。
### C01755
368918｜{"id":"C01755","source":"84.2_加工","target":"40.1_制造","type":"嵌套链","condition":"加工是制造的一部分","priority":1,"effect":"加工是制造的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"交互层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"84.2_加工","original_target":"40.1_制造","normalized_source":"84.2_加工","normalized_target":"40.1_制造","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】已选加工属于当前制造时，以材料实际原值、处理动作和所得中间物记录本场变化，整体成品是否完成另按检验条件核对。
### C01760
369977｜{"id":"C01760","source":"84.4_交易","target":"26.1_交易类型","type":"嵌套链","condition":"交易是类型","priority":1,"effect":"交易是交易类型的一种","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"交互层","target_layer":"生成层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"84.4_交易","original_target":"26.1_交易类型","normalized_source":"84.4_交易","normalized_target":"26.1_交易类型","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】已选交易真有交出或收到的资源时，用双方实际前值、交付与结算方式核对变化，归入已有交易类型的说明依本作规则。

## 物件操作动态连接结束"""
