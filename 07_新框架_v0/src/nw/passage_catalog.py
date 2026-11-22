"""Evidence roles for optional scene techniques, shared by analysis and production."""

# A single short quotation can demonstrate a technique. Require two positions only
# when the relationship between two observable moments is the point of the method.
OBSERVATIONS = {
    'orientation': ('定位与现场正在进行的事', {'setting':'足以定位的时间、场地或活动'}),
    'ongoing_activity': ('焦点人物出现以前已经运转的现场', {'underway':'现场在焦点出现以前已经有人做的事'}),
    'event_start': ('由等候转为行动', {'signal':'启动者的言行', 'response':'首位响应者的行动'}),
    'spatial_cue': ('相对位置引出行动', {'position':'使观察、移动或递物成立的位置'}),
    'sensory_evidence': ('以感官细节体现现场', {'detail':'让读者产生具体感受的声音、动作或物件'}),
    'expectation_reveal': ('熟悉经验被新证据改写', {'expectation':'引出读者预期的情境', 'reveal':'修正预期的细节'}),
    'place_function': ('陈设与活动说明场所用途', {'setting':'有辨识度的陈设', 'activity':'印证其用途的活动'}),
    'rule_in_force': ('制度在当前选择中生效', {'rule':'实际适用的要求', 'decision':'知悉要求后的选择或履行'}),
    'action_completion': ('把关键行动写到完成标志', {'operation':'谁对什么实际做了什么', 'result':'让本次行动成立的结果'}),
    'object_transfer': ('交付物件与获得资格', {'delivery':'当场实际交付、经手或生效的东西'}),
    'identity_slice': ('按当前需要披露身份', {'entry':'当场足以辨认人物的称谓、动作或外貌'}),
    'authority_response': ('他人的行动体现人物地位', {'response':'能看出关系的等候、应答或服从'}),
    'dialogue_turn': ('用对白推动当场进程', {'speech':'发话的实际目的', 'response':'当场回应或状态变化'}),
    'professional_voice': ('职业观察进入人物台词', {'speech':'注意的细节、说法和发话目的'}),
    'focus_boundary': ('区分换地点、换观察对象和进入内心', {'before':'先前位置或焦点', 'after':'新地点或对象及可知边界'}),
    'qualified_claim': ('保留估计的依据和确定程度', {'claim':'原文带限定的判断，与确证的事实分开'}),
    'interpreted_motive': ('把对他人动机的解释归还给判断者', {'interpretation':'谁这样理解；当事人实际透露了多少'}),
    'pace_switch': ('从概述或省略回到具体过程', {'before':'先前的叙述速度', 'turn':'使读者再度细看的变化'}),
    'presentation_mode': ('为这一段选择概述或现场展开', {'moment':'稳定惯例被简述，或决定、发现被当场写出的具体原句'}),
    'reader_change': ('读者理解有进展', {'disclosure':'何处改变读者所知或期待；人物知情另计'}),
    'paragraph_turn': ('自然段的停顿与衔接', {'before':'停顿前的语句', 'after':'承接语句或另段展开的结果'}),
    'local_handoff': ('分清已完成、已获条件与待办', {'handoff':'已经得到什么，哪一件事尚待后文'}),
    'detail_value': ('删去一句后的具体得失', {'detail':'可比较取舍的原句及其定位、语气、感受或期待'}),
}
