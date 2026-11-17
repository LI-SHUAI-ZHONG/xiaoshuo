"""Require source comprehension and a working method before story generation."""
from nw.task_models import _text

POLICY='source-driven-work-v2'
FUNCTIONS={
    'book':['reader_experience','plot_design','foreshadowing','character_design','world_design'],
    'detail':['action_design','emotion_design','information_design','scene_progression','expression'],
}
STUDY_PROMPT='''[MATERIAL_WORK] 你在执行小说创作前的资料研读与工作安排。只输出JSON，顶层严格为
status、tasks、requests、understanding、work_plan。status为retrieve或ready。本阶段不能先生成小说方案。
按需求及required_functions逐项判断实际功能，主动发现需要设计的内容：读者情绪是读者体验和信息安排，
不是人物的身体情绪。动作要有目标、阻碍、连续应对与结果；伏笔要设计埋设、遮蔽、唤醒、回收及作用。
tasks每项含id、function、role(design/write/review)、required(布尔)、reason、deliverable；
可以新增所需功能，不适用项明确具体原因。不要因需求未说“写动作”就不设计人物实际如何行动。
初始资料不够，requests可批量返回{action:search,query:功能或来源名,cursor:0}或{action:read,id:确切来源ID}；
search返回可继续翻页的结果，read返回原义和运用层。沿related_sources继续读取依赖；不受五张方法卡限制。
understanding每项含source_id、quotes(原文精确引句数组)、meaning、operation、inputs、outputs、limits、check。
必须真正阅读原文并说清怎样干活，不能用资料名充当理解。运用层用于理解操作，冲突及旧授权不继承。
template是需项目实例化的方法；不得自动生成completed事件、不得把评分999修成新评分。
缺定义和空库可导航但不当完整方法；缺端点的边不证明编号等同，去读关联方法后提出本项目候选关系。
ready时requests为空，work_plan逐适用task含task_id、source_ids、steps(操作步骤数组)、output、check。
只用实际已读且有原义操作的资料。计划应规定模型随后必须交出的项目产物和实际使用位置，不能只登记用途。
没有相关资料就继续检索或明确停止，不能假称资料支持未写出的原义。'''


def functions_for(scope: str) -> list[str]:
    return list(FUNCTIONS['book' if scope=='book' else 'detail'])


def _require(ok: bool,message: str) -> None:
    if not ok:raise ValueError('MATERIAL_WORK: '+message)


def validate_study(result: dict,sources: list[dict],scope: str,demand: str) -> None:
    _require(isinstance(result,dict) and set(result)=={'status','tasks','requests','understanding','work_plan'},'invalid study envelope')
    _require(result['status'] in {'retrieve','ready'} and all(isinstance(result[k],list) for k in
             ('tasks','requests','understanding','work_plan')),'invalid study phase')
    for request in result['requests']:
        _require(isinstance(request,dict),'invalid source request')
        if request.get('action')=='search':
            _require(set(request)<={'action','query','cursor'} and _text(request.get('query'))
                     and type(request.get('cursor',0)) is int and request.get('cursor',0)>=0,'invalid search request')
        else:
            _require(set(request)=={'action','id'} and request['action']=='read' and _text(request['id']),'invalid read request')
    if result['status']=='retrieve':
        _require(bool(result['requests']),'retrieve must request actual source work');return
    _require(not result['requests'],'ready cannot hide outstanding source requests')
    tasks={}
    for task in result['tasks']:
        _require(isinstance(task,dict) and set(task)=={'id','function','role','required','reason','deliverable'}
                 and all(_text(task[k]) for k in ('id','function','reason','deliverable'))
                 and _text(task['role']) and task['role'] in {'design','write','review'} and type(task['required']) is bool
                 and task['id'] not in tasks,'invalid or duplicate design task')
        tasks[task['id']]=task
    functions={task['function'] for task in tasks.values()}
    _require(set(functions_for(scope))<=functions,'missing functional applicability decisions')
    cues={'动作':'action_design','伏笔':'foreshadowing','读者情绪':'reader_experience','情绪描写':'emotion_design'}
    for cue,function in cues.items():
        if cue in demand:
            _require(any(t['function']==function and t['required'] for t in tasks.values()),'explicit task was omitted: '+cue)
    available={row['source']['id']:row for row in sources};understood=set()
    for row in result['understanding']:
        _require(isinstance(row,dict) and set(row)=={'source_id','quotes','meaning','operation','inputs','outputs','limits','check'}
                 and all(_text(row[k]) for k in ('source_id','meaning','operation','inputs','outputs','limits','check'))
                 and row['source_id'] in available and row['source_id'] not in understood,'unread or duplicate source interpretation')
        source=available[row['source_id']]
        _require(source['use_mode']=='project_method' and isinstance(row['quotes'],list) and bool(row['quotes'])
                 and all(_text(q) and len(''.join(q.split()))>=8 and q in source['original_text']
                         for q in row['quotes']),'interpretation needs actual original method passages')
        understood.add(row['source_id'])
    wanted={key for key,task in tasks.items() if task['required']};seen=set()
    _require(bool(wanted),'no actual source-driven work was planned')
    for plan in result['work_plan']:
        _require(isinstance(plan,dict) and set(plan)=={'task_id','source_ids','steps','output','check'}
                 and _text(plan['task_id']) and plan['task_id'] in wanted-seen
                 and isinstance(plan['source_ids'],list) and bool(plan['source_ids'])
                 and all(_text(i) and i in understood for i in plan['source_ids'])
                 and isinstance(plan['steps'],list) and bool(plan['steps']) and all(_text(s) for s in plan['steps'])
                 and _text(plan['output']) and _text(plan['check']),'every actual task needs read sources and working steps')
        seen.add(plan['task_id'])
    _require(seen==wanted,'missing concrete method work plan')


def compact_session(session: dict) -> dict:
    if session.get('policy') in {'artifact-stage-binding-v3','artifact-stage-binding-v4'}:
        return {key:session[key] for key in ('id','scope','policy','stages','candidates')}
    return {key:session[key] for key in ('id','scope','policy','result')}
