"""Interpret the authorization, missing credentials and executable decision of C00738."""
import re
from dataclasses import dataclass

from nw.materials.semantic_application import require


# A program needs an issuer and an executor. Its supporting condition must concern
# the same credential, executor, document or controlled operation as that program.
_ISSUE = re.compile(r'授权|授予|委派|委任|委托|下令|颁令|表决通过|裁定|颁行|签发|签署|签令|批示|颁发|核发|盖印批准|批准|颁布|赋予|有权签')
_PROCESS = re.compile(r'按号|验印|核印|核章|核验|核实|验章|核对|比对|查验|审验|验看|查对|复核|验签|核签|审查|凭证|凭令|持令|执行|登记|验明|逐项|照章|奉令|依令|按令')
_EXECUTOR = re.compile(r'([\u3400-\u9fff]{0,5}(?:员|吏|官|人|卫|使|长|司|署|吏员|值守者|工匠|守将|护卫|书记|守军|士兵|门房|掌柜|文书|办事处|委员会|船工|商贩|厨师|商户|学徒|库管|馆员|信差))')
_DOCUMENTS = {
    '印': r'双印|两印|印鉴|印章|印信|封印|两枚印|二枚印|一枚印|第二枚印|验印|盖印|缺印|少印|枚印|用印|签印|印齐|齐印',
    '回执': r'回执|回单|回条|收执|回签单',
    '令': r'令牌|双印令|调令|手令|通行令|急令|敕令|批令|命令书|授权令',
    '签': r'签字|签名|会签|签章|联署|签批|签署',
    '票': r'通行证|路引|许可证|凭证|通行文牒|执照|文牒|准入证|通行牌',
    '簿': r'闸簿|名册|名簿|登记簿|清册|名录',
    '授权': r'授权|许可|批文|批复',
    '案卷': r'借卷|开卷|调卷|阅卷|卷宗|调阅|档案',
}
_DOCUMENTS = {k: re.compile(v) for k, v in _DOCUMENTS.items()}
_DECISIONS = {
    '过闸': r'放行|开闸|启闸|开栅|放船|让船通行|准予通行|准其通行|准许通行|放其通行|允许通行|正常通行|放船通行',
    '阅卷': r'开卷|调阅|借阅|阅卷|开库|交卷给|交付案卷|开放案卷|准阅|开放档案|提供档案',
    '受理': r'受理|立案|核准申请|批准申请|批准办理|办理过户|完成过户',
    '准入': r'准入|放入|入城|进城|入场|进场|准许进入|放人入内|开门让行',
    '发给': r'发给|拨付|发放|交付款项|兑付|划拨|领取|支付',
    '执行': r'实施处分|执行裁决|执行处分|实施裁决|执行判决|执行命令',
}
_DECISIONS = {k: re.compile(v) for k, v in _DECISIONS.items()}
_DENIAL = re.compile(r'拒绝|拒办|不予|不准|不得|不可|不能|无法|禁止|拒发|暂扣|扣船|扣留|扣下|退件|退回|暂缓|驳回|停办|不许|免于|不肯|不放行|不让|不开放')
_GAP = re.compile(r'缺(?:少|件|失|一|任|印|回|凭|章|证|乏)|少(?:了|一|任|印|盖)|尚缺|未(?:送达|到|齐|备|签|盖|通过|获|交|见|带|呈|递|取得|出示|查验)|无(?:回执|印章|凭证|授权|证件|印信)|没有|不(?:全|齐|足|在手|完备|合格)|未能|撤销|吊销|收回|过期|失效|作废|不符|遗失|残缺|无效|撤回|欠缺')
_COMPLETE = re.compile(r'补齐|补全|补交|补回|补发|补盖|送达|收齐|集齐|备齐|到齐|齐备|齐全|核验无误|核对无误|验明无误|核验通过|核验合格|验明正身|验讫|已签|签齐|一致|确认有效|已经收到|已到|验过')
_CONDITION = re.compile(r'只有|仅|限于|才|须|应|必须|需|可凭|凭|拒|退件|退回|不得|禁止|不许|不能|无效|否则|除非|例外|失效|时|即|就|只在|超过|超出|生效|方可|一律|一概|仅限')
_UNCONFIRMED = re.compile(r'待定|待补|待核|待确认|据说|传闻|可能|尚未核实|假设|示例|仅作举例|已取消|取消了|不再采用|无关|猜测|未知')
_BYPASS = re.compile(r'无条件|一概放行|无需|不须|不用|免验|免检|不必|不核验|不经|跳过|不管|无论|无须')
_BREACH = re.compile(r'违规|违令|越权|违章|违例|违法|擅自|擅开|抗命|违背|违抗|私放|私自|冒险违|徇私|冒用')
_PENALTY = re.compile(r'追责|受罚|处罚|问责|追究|停职|免职|处分|革职|拘押|扣薪|赔偿|记过|查办|追查|留下.{0,4}(?:证据|记录)|立案调查|受审|被查')
_OFFICIAL = re.compile(r'依(?:法|规|例|令|章)|按(?:规定|规矩|章|例)|(?:制度|港规|库规|章程)(?:允许|要求|准许)|(?:依据|根据)(?:港规|库规|章程)|合规|合法|奉命|有权|无条件')
_EXCEPTION = re.compile(r'除非|例外|可免|免验|特许|特批|豁免|替代|应急|紧急|破例|代替|免于|可先行')
_HYPOTHETICAL = re.compile(r'(?:以免|为防|防止|避免|阻止|试图阻止).{0,12}$')
_NEG_END = re.compile(r'(?:不(?:敢|得|能|准|许|应|可|予|曾|再|会|肯)?|绝不|未(?:曾|能)?|无权|拒绝|禁止|阻止|防止|暂停|停止|不肯|无意|暂缓)(?:(?:立即|直接|无条件|擅自|自行|依规|当场|允许|予以|自动|再行|继续|按规定|为其|再次|轻易|对其|随意|单独|独自|擅行|当即)){0,3}$')
_PIECES = re.compile(r'[，,。；;！!？?\n]+|(?=随后|而后|接着|但却|却仍|却又|然后|否则|但是)')
_SENTENCES = re.compile(r'[。；;！!？?\n]+')

def _keys(patterns: dict, text: str) -> set[str]:
    return {k for k, pattern in patterns.items() if pattern.search(text)}

def _specific_shared(left: str, right: str) -> bool:
    """Share a named project detail, not punctuation or a stock logical connective."""
    def grams(s: str) -> set[str]:
        return {part[i:i+3] for part in re.findall(r'[\u3400-\u9fff]+', s) for i in range(len(part)-2)}
    return bool((grams(left) & grams(right)) - {'按规定', '的规定', '必须由', '无条件', '仅限于', '不得在', '制度规', '度规定'})

def _project_detail(source: str, text: str) -> bool:
    # The bare decision (for example “拒绝放行”) is shared by many institutions.
    scrub = re.compile(r'规定|制度|办事人员|执行人员|审批程序|拒绝|依法|流程|应当|按规定|依规|必须|' +
                       '|'.join(p.pattern for p in _DECISIONS.values()))
    source, text = scrub.sub(' ', source), scrub.sub(' ', text)
    return bool(_keys(_DOCUMENTS, source) & _keys(_DOCUMENTS, text) or _specific_shared(source, text))


def _linked(rule: str, condition: str) -> bool:
    return bool(_keys(_DOCUMENTS, rule) & _keys(_DOCUMENTS, condition)
                or _keys(_DECISIONS, rule) & _keys(_DECISIONS, condition)
                or _specific_shared(rule, condition))

def eligible(key: str, rule: str, limit: str, *, full_rule: str | None = None, full_limits: str | None = None) -> bool:
    if key != 'C00738' or not all(isinstance(x, str) and x.strip() for x in (rule, limit)):
        return False
    if (full_rule is not None and rule not in full_rule) or (full_limits is not None and limit not in full_limits):
        return False
    if _UNCONFIRMED.search(rule) or _UNCONFIRMED.search(limit):
        return False
    issue = next((match for match in _ISSUE.finditer(rule)
                  if not re.search(r'(?:无权|不曾|并未|不得|不能|严禁|不会|无须|拒绝|不再)(?:为其|自行|私自|再次)?$',
                                   rule[:match.start()])), None)
    if not issue or len(re.findall(r'[\u3400-\u9fff]', rule[:issue.start()])) < 2:
        return False
    program = rule[issue.end():]
    if not (_EXECUTOR.search(program) and (_PROCESS.search(program) or _keys(_DECISIONS, program))):
        return False
    first, *rest = _PIECES.split(rule)
    if rest and _ISSUE.search(first):
        execution = '，'.join(rest)
        refers_to_order = re.search(r'据此|照此|依令|按令|奉令|奉命|接令|按该|凭此|持此|收到授权|按号验|验令', execution)
        if not (_keys(_DOCUMENTS, first) & _keys(_DOCUMENTS, execution)
                or _keys(_DECISIONS, first) & _keys(_DECISIONS, execution) or refers_to_order
                or (issue[0] in ('授权','授予','委派','委任','委托') and _EXECUTOR.search(first[issue.end():]))):
            return False
    shares_process = bool(_keys(_DOCUMENTS, rule) & _keys(_DOCUMENTS, limit)
                          or _keys(_DECISIONS, rule) & _keys(_DECISIONS, limit)
                          or (_PROCESS.search(limit) or _DENIAL.search(limit)) and _specific_shared(rule, limit))
    return bool((_CONDITION.search(limit) or _GAP.search(limit)) and shares_process)


def _exception_matches(limit: str, text: str, missing: set[str]) -> bool:
    """The actual alternative credential/authorizing contingency must appear on both sides."""
    for sentence in _SENTENCES.split(limit):
        if not _EXCEPTION.search(sentence):
            continue
        clauses = _PIECES.split(sentence)
        mandatory = {k for part in clauses if re.search(r'仍须|仍需|仍应|不得免|不可免|照常核验|仍要查验', part)
                     for k in _keys(_DOCUMENTS, part)}
        if mandatory & missing:
            continue
        for clause in clauses:
            if not _EXCEPTION.search(clause):
                continue
            waiver = re.search(r'(?:免交|免验|免除|代替|替代|豁免)([^，。；;]{1,18})', clause)
            if waiver and (waived := _keys(_DOCUMENTS, waiver[1])) and not missing <= waived:
                continue
            generic = set(re.findall(r'(?:应急|紧急|特许|替代|豁免|特批)[\u3400-\u9fff]{1,5}?(?:手令|通行令|令|证|函|票|单|签|章|印|许可)', clause))
            markers = set()
            for condition in re.findall(r'(?:除非|若持有|凭|持有|出示|持|如遇|发生)([\u3400-\u9fff]{2,16}?)(?:时|方可|可先|可免|可以|得以|即可|者|$)',clause):
                if not _GAP.search(condition):
                    markers.add(condition)
            for mark in markers or generic:
                credential = re.escape(mark)
                for part in _PIECES.split(text):
                    if not re.search(r'(?:持有|持|出示|取得|获发|奉|收到|携|凭|带来|递交|如遇|发生|已启动)[了着的]?' + credential, part):
                        continue
                    if re.search(r'(?:无|没有|未能|尚未|未|伪造|冒用|无效|作废|未持|尚待|必须|除非|倘若|只有|若|企图|假设).{0,9}' + credential, part):
                        continue
                    if not re.search(credential + r'.{0,4}(?:已被收回|并未到手|过期|已作废|失效|系伪造)', text):
                        return True
    return False


@dataclass(frozen=True)
class _Program:
    rule: str
    limit: str
    aftermath: str

    @property
    def decisions(self) -> set[str]:
        return _keys(_DECISIONS,self.rule + self.limit)

    def related(self, text: str) -> bool:
        return _linked(self.rule + self.limit, text)


def _program(row: dict) -> _Program:
    rule, limit = row.get('excerpts', ())[:2]
    # Additional clauses, particularly narrow exceptions, remain on the frozen world card.
    card_fields = [e['value'] for e in row.get('evidence', row.get('prerequisites', []))
                   if e['ref'].endswith(('/body/rule', '/body/limits')) and isinstance(e['value'], str)]
    clauses = [clause for text in card_fields for clause in _SENTENCES.split(text)
               if _EXCEPTION.search(clause) and _linked(rule + limit, clause) and not _UNCONFIRMED.search(clause)]
    return _Program(rule, '。'.join(dict.fromkeys([limit, *clauses])), row.get('authority_aftermath') or '')


def project_limit(row: dict) -> str:
    """Keep grounded exceptions from the complete world card in the writer's limit."""
    return _program(row).limit


def _punishment(breach: str, afterward: str) -> bool:
    """A bystander's unrelated penalty cannot justify the staff member's breach."""
    marker = _BREACH.search(breach)
    if not marker:
        return False
    source = re.sub(r'仍然|仍|却|竟然|竟|一时|故意|居然|决定|竟敢|胆敢|再次|已经|公然|径直', '', breach[:marker.start()])
    actor = re.split(r'[，,。；;：:]|(?<=时)|(?<=后)', source)[-1]
    actors = {a[0] for a in _EXECUTOR.finditer(actor)}
    if actor:
        actors.add(actor)
    penalty = _PENALTY.search(afterward)
    if not penalty or re.search(r'未被|没有|不会|可能|险些|否则|免于|逃过|免予|或许|另案|无关|并未|本应|本该|本会|假如', afterward[:penalty.start()]):
        return False
    before = afterward[:penalty.start()]
    cause = re.search(r'因此|因而|为此|因(?:私放|擅自|此举|违令|越权|擅开)|此举(?:导致|使)|事后|随后被|故被|以致|结果被|由此|随即|当场被|(?:导致|使)(?:他|她|其)被', before)
    if not cause and not before.startswith(('被','遭','受到')):
        return False
    if re.search(r'他人|旁人|另外|别人|另一(?:人|名)|其余人员', before):
        return False
    subject = before[:cause.start()] if cause else ''
    # Cover both “船工因此被罚” and “因此船工被罚”.
    subject += re.split('受到|遭到|被|遭|面临', before[cause.end():], maxsplit=1)[0] if cause else ''
    subject = re.sub(r'^\[FAKE\]\s*|事后|因此|于是|随后|他|她|其本人|其|本人|该人', '', subject).strip()
    if not subject:
        return True
    if marker := _BREACH.search(subject):
        subject = subject[:marker.start()]
    return any(who in subject or subject == who for who in actors if who)


def _check(program: _Program, text: str, *, compulsory: bool) -> None:
    scoped = _project_detail(program.rule + program.limit, text) if compulsory else program.related(text)
    if not scoped:
        if compulsory:
            require(False, '制度授权落点未保留本程序的凭据、执行者或可核对结果')
        return
    docs = _keys(_DOCUMENTS, program.rule + program.limit)
    decisions = program.decisions
    missing = set()
    pieces = [p for p in _PIECES.split(text) if p]
    for index, piece in enumerate(pieces):
        for part in re.split(r'[、]|或者|或是|或(?=缺|无|未|少)', piece):
            named = docs & _keys(_DOCUMENTS, part)
            if _GAP.search(part):
                if named:
                    missing.update(named)
                elif re.search(r'缺件|手续不齐|缺少凭据|缺少证件', part):
                    missing.add('手续')
            elif _COMPLETE.search(part) and not re.search(r'等候|等到|等着|待|正在催|须先|必须先|尚需|盼|伪造|假称|如果|若能', part):
                missing.difference_update(named)
                if re.search(r'(?:手续|全部凭据|所有凭据|全套材料)(?:已经|已)?(?:补齐|齐备|齐全)', part):
                    missing.clear()
        for family in decisions:
            for outcome in _DECISIONS[family].finditer(piece):
                prefix = piece[:outcome.start()]
                # Recording or investigating a permit decision does not execute it a second time.
                nominal = re.match(r'案|记录|经过|原委|一事|所需的文书', piece[outcome.end():])
                if nominal or _NEG_END.search(prefix) or _HYPOTHETICAL.search(prefix):
                    continue
                if not missing and not _BYPASS.search(piece):
                    continue
                if _exception_matches(program.limit, '，'.join(pieces[:index + 1]), missing):
                    for duty in ('登记', '留痕', '复核', '补验', '补签', '上报'):
                        if duty in program.limit:
                            require(not re.search(r'(?:免于|免除|不用|无须|无需|不必|拒绝|毋须|不予)(?:事后|另行|再)?' + duty, text),
                                    '制度授权的明示例外仍须保留本程序的后续义务')
                    continue
                breach_context = piece if _BREACH.search(piece) or not index else pieces[index-1] + '，' + piece
                aftermath = [*pieces[index:index+3], *filter(None, _PIECES.split(program.aftermath))]
                linked_penalty = any(_punishment(breach_context, part) for part in aftermath)
                if _BREACH.search(breach_context) and linked_penalty and not _OFFICIAL.search(prefix):
                    continue
                detail = '、'.join(sorted(missing)) if missing else '被省略的必要程序'
                require(False, f'制度授权的实际结果与冻结条件相反。尚待核实{detail}，本次却依规“{outcome[0]}”。')
    if compulsory:
        require(bool(_keys(_DECISIONS, text) & decisions or _PROCESS.search(text) or _DENIAL.search(text) or _BREACH.search(text)),
                '制度授权采用须写出本程序如何办理、拒绝或处理违规')


def validate_use(row: dict, text: str, *, operation: str, stage: str) -> None:
    """Validate the recorded field itself; an acknowledgement cannot cancel an opposite outcome."""
    program = _program(row)
    _check(program, text, compulsory=True)
    if operation != text:
        _check(program, operation, compulsory=False)


def check_conflict(row: dict, text: str, *, stage: str) -> None:
    """Check other actual outcomes only when the text explicitly addresses this frozen program."""
    if isinstance(text, str) and text:
        _check(_program(row), text, compulsory=False)
