"""计划、取舍、时机和实际成本的动态原边。"""

MATERIAL = r"""## 决定及其后续实际影响

按本场实际前值、已选事件和动作核对所知、选择或行动窗口怎样改变，实际支付与预期结果各按证据。

### C00388
81025｜{"id":"C00388","source":"159.1_事前计划","target":"145.2_想法","type":"嵌套链","condition":"计划是想法","priority":1,"effect":"事前计划是想法的一部分","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"表达层","target_layer":"执行层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"159.1_事前计划","original_target":"145.2_想法","normalized_source":"159.1_事前计划","normalized_target":"145.2_想法","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】本场计划已实际形成、被披露或因准备而改变人物所知时，以原前值核对角色新增的具体预期和行动条件，计划与实际执行各按证据。

### C01545
324496｜{"id":"C01545","source":"72.5_冒险","target":"43.6_时间压力","type":"触发链","condition":"时间压力下","priority":2,"effect":"冒险决策增加时间压力","direction":"双向","strength":"中","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"引擎层","target_layer":"组织层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"72.5_冒险","original_target":"43.6_时间压力","normalized_source":"72.5_冒险","normalized_target":"43.6_时间压力","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】核对原边所指冒险选择、当场时限和实有动作，只有实际行动改变剩余时间或可行动窗口时记录相应变化，人物感觉紧迫的范围另按证据。

### C01550
325555｜{"id":"C01550","source":"73.1_决策依据","target":"149.1_权衡","type":"嵌套链","condition":"依据决定权衡","priority":1,"effect":"决策依据决定权衡方式","direction":"单向","strength":"强","valid_types":["玄幻","仙侠","都市","科幻","悬疑","言情","历史","军事","游戏","体育","灵异","同人","二次元","耽美","轻小说"],"source_layer":"引擎层","target_layer":"执行层","generated_from_static":false,"needs_review":false,"status":"original"}
【追溯原值】{"original_source":"73.1_决策依据","original_target":"149.1_权衡","normalized_source":"73.1_决策依据","normalized_target":"149.1_权衡","field_source":{"source":"动态网络.txt 原始连接记录"}}
【本步用法】依本场实际前值和人物当时所知，把可用依据对应到具体权衡，状态变化由已选行动、披露或可核新知支持。

## 决策动态原边结束
"""
