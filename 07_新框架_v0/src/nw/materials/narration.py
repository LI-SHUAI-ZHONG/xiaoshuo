"""Keep each disclosure tied to the scene, its audience and the known story."""
from dataclasses import asdict
import re

from nw.story_models import Fact
from nw.materials.phase_context import new_character_keys
from nw.task_models import canonical, content_sha256


POLICY = 'scene-narration-v1'
ACCESS_POLICY = 'scene-narration-v2'
EVIDENCE_POLICY = 'scene-narration-v3'
ACCESS_POLICIES = (ACCESS_POLICY, EVIDENCE_POLICY)
POLICIES = (POLICY, *ACCESS_POLICIES)
PERSONS = ('first', 'second', 'third_limited', 'third_omniscient')
MODES = ('action', 'speech', 'perception', 'thought', 'inference', 'summary', 'reenactment')
FIELDS = {'time', 'mode', 'owner', 'basis_ref', 'basis_quote', 'effect'}
ENDINGS = '。！？.!?\n'
SENTENCE_END = re.compile(f'[{re.escape(ENDINGS)}]')
CARD_BASIS_KINDS = {'background': 'history', 'history': 'history', 'rule': 'rule', 'voice': 'voice'}
SCENE_INSTRUCTION = (
    '先按场确定谁是视角人物、哪些人在场、各自为何在意此事以及谁能听见或看见。'
    '别人私下怎样想可在其人物设计中成立，若要让读者直接听到他的心声，另设由他担任pov的场景并标出切换。'
    '可从某个已知结果引起读者疑问，在适当处补述原因；未知原因可保留。'
)
WORLD_INSTRUCTION = (
    '当前设计需要在正文交代世界前史时，将有依据的既成事件及已确定的原因或后果写入相应世界卡的history，'
    '沿用本卡可见范围。rule保留一般规律。某事按制度允许发生，与它当年确已发生分别记录；'
    '后续设想、传言、未知原因都不填为史实。没有可用前史时不强设此项。'
)
_EXPRESSION_BASIS = (
    '按实际讲述次序输出guidance；每条一拍，narration含time=current/past，mode=' + '/'.join(MODES) +
    '，owner=言行者或思考者key，面向读者的叙述者概述或重述用null。basis_ref从本场narration_bases中选择，'
    '后续反应也可引beat:本场从1起的先前拍号，摘其observable，例如配角开口后主角据此改判。'
    '引用想法、推测或他人说法时完整保留其表述，能确认的是他说过或这样想过，内容是否属实另取依据。'
    'basis_quote摘取该依据原话，observable写本段将讲什么或如何体现，effect说明读者因此懂得什么或人物接下来为何反应，'
    'check指出正文中足以辨认效果的表现。按需要用一拍或多拍；没有根据的原因不要写成事实。'
    'past只回述已有前史或已接受事实；概述可先交代结果再补来由，重演可写过程，若返回现场用眼前的人、物或交流承接。'
    '公共往事可由叙述者告诉读者，不自动成为人物所知。'
)
_OTHER_POV = '另一人以其可见动作、说出的话、情绪表现呈现；对其想法的推断归当前pov。'
EXPRESSION_INSTRUCTION = _EXPRESSION_BASIS + '本场可直接呈现pov内心；belief/suspicion只支持本人当下想法或推断，保留不确定。' + _OTHER_POV
EVIDENCE_INSTRUCTION = _EXPRESSION_BASIS + '人物可据自己的疑心发言或行动；只直写pov内心，保留猜疑。' + _OTHER_POV


def _present(scene: str, body: dict) -> dict:
    bases = {}
    for field in ('goal', 'conflict', 'choice', 'entering_state', 'planned_result'):
        if value := body.get(field):
            bases[f'scene:{scene}:{field}'] = {'text': value, 'kind': 'scene'}
    return bases


def _card_bases(pov: str, people: set[str], cards: list[tuple[str, str, dict]], *,
                personal_sources: bool = False) -> dict:
    bases = {}
    for key, kind, body in cards:
        public = body.get('visibility') == 'public'
        if not public and not (body.get('visibility') == 'holders' and pov in body.get('holders', [])):
            continue
        # A person's publicly visible card is also used for casting. Only the
        # viewpoint's own personal background is a source of private recollection.
        if kind == 'character':
            fields = (('background', 'want', 'need', 'voice', 'core_conflict', 'boundaries', 'behavior')
                      if key == pov else ('voice',) if key in people and public else ())
            if personal_sources and key in people:
                fields += ('independent_goal',) if key == pov else ('background', 'independent_goal')
        else:
            fields = ('rule', 'history') if kind == 'world' else ()
        for field in fields:
            if value := body.get(field):
                bases[f'card:{key}:{field}'] = {'text': value, 'kind': CARD_BASIS_KINDS.get(field, 'character'),
                                                'public': public, 'subject': key if kind == 'character' else None}
                if personal_sources and kind == 'character' and key != pov and field in ('background', 'independent_goal'):
                    bases[f'card:{key}:{field}']['speaker_private'] = True
    return bases


def scene_bases(products: dict, context: dict, scene: str | None = None) -> dict:
    scene_product = products['scene_design']['products']
    places = {scene['card']: (scene['story_order'], (chapter['index'], scene['index'], 0))
              for chapter in scene_product['chapters'] for scene in chapter['scenes']}
    cards = [(r['card_id'], r['kind'], r['body']) for r in context.get('approved_cards', [])]
    for stage in ('character_design', 'world_design'):
        cards.extend((r['key'], r['kind'], r['body']) for r in
                     products.get(stage, {}).get('products', {}).get('members', []))
    new_people = new_character_keys(products, context)
    policy = context.get('narration_policy')
    access = policy in ACCESS_POLICIES
    claims = ('fact', 'belief', 'suspicion', 'utterance', 'plan') if access else ('fact', 'belief', 'suspicion')
    from nw.materials.scene_knowledge import scoped
    from nw.materials.cast_design import entry_bases
    exact = scoped(scene_product, context)
    accepted = context.get('narration_facts', context.get('accepted_state', []))
    cast = (entry_bases(scene_product, cards, context.get('cast_previous_appearances', {}),
                        accepted, scene_facts=exact,
                        new_people=new_people if policy == EVIDENCE_POLICY else None,
                        unverified_chapters=context.get('cast_history_unverified_chapters', ()))
            if access else {})
    by_scene = {}
    for row in scene_product['members']:
        key, body = row['key'], row['body']
        if scene is not None and key != scene:
            continue
        pov = body['pov']
        bases = _present(key, body)
        people = {pov, *body.get('characters', [])}
        bases.update(_card_bases(pov, people, cards, personal_sources=policy == EVIDENCE_POLICY))
        order, disclosure = places[key]
        for index, fact in enumerate(accepted if exact is None else exact[key]):
            audience, claim = fact.get('holder'), fact.get('claim')
            if access and (audience in new_people or fact.get('entity_id') in new_people):
                # Local planning keys will acquire fresh card IDs on approval.
                continue
            speaker_source = access and audience in people and audience != pov
            if (audience not in (pov, 'READER') and not speaker_source) or claim not in claims:
                continue
            if audience == 'READER' and (claim != 'fact' or fact.get('story_order', order + 1) > order):
                continue
            if exact is None and (fact.get('story_order', order + 1) > order or
                                  tuple(fact.get('disclosure_order', disclosure)) >= disclosure):
                continue
            value = fact['value']
            bases[f'fact:{index}'] = {'text': value if isinstance(value, str) else canonical(value),
                                      'kind': 'state', 'audience': audience, 'claim': claim}
            if access:
                from nw.materials.cast_design import confirmed_identity
                bases[f'fact:{index}']['subject'] = fact.get('entity_id')
                if Fact.__dataclass_fields__.keys() <= fact.keys():
                    bases[f'fact:{index}']['state_sha256'] = content_sha256(fact)
                if name := confirmed_identity(fact):
                    bases[f'fact:{index}']['confirmed_identity'] = name
            if speaker_source:
                bases[f'fact:{index}']['speaker_private'] = True
        bases.update(cast.get(key, {}))
        by_scene[key] = bases
    return by_scene


def register_beat(bases: dict, order: int, guide: dict) -> None:
    beat = guide['narration']
    shared_here = beat['time'] == 'current' and beat['mode'] in ('speech', 'action')
    bases[f'beat:{order}'] = {'text': guide['observable'], 'kind': 'beat', 'owner': beat['owner'],
                              'shared': shared_here, 'claim': beat['mode']}
    if 'witnesses' in beat:
        bases[f'beat:{order}']['witnesses'] = beat['witnesses']


def verify_scene_facts(required: set[str], current: list[Fact]) -> list[Fact]:
    matched = {sha: fact for fact in current if (sha := content_sha256(asdict(fact))) in required}
    if required - matched.keys():
        raise ValueError('MATERIAL_PRECONDITION: 表达所依的角色所知、读者获知或原稿证据已经变化，需按当前分支重设')
    return list(matched.values())


def _source_sentence(source: str, quote: str) -> tuple[str, int]:
    start = source.index(quote)
    left = 1 + max(source.rfind(delimiter, 0, start) for delimiter in ENDINGS)
    right = SENTENCE_END.search(source, start + len(quote))
    return source[left:right.end() if right else len(source)], start - left


def validate_beat(beat: dict, body: dict, bases: dict, *, access: bool = False) -> None:
    def require(condition: bool, reason: str) -> None:
        if not condition:
            raise ValueError('MATERIAL_STAGE: 叙述节拍' + reason)

    require(isinstance(beat, dict) and FIELDS <= set(beat) and
            not set(beat) - FIELDS - ({'witnesses'} if access else set()), '缺少归属、时序、前置引文或实际作用')
    time, mode, owner = beat['time'], beat['mode'], beat['owner']
    pov = body['pov']
    if access:
        present = {pov, *body.get('characters', [])}
        if time == 'current' and mode in ('action', 'speech'):
            witnesses = beat.get('witnesses')
            require(isinstance(witnesses, list) and all(isinstance(key, str) and key in present and key != owner
                    for key in witnesses) and len(set(witnesses)) == len(witnesses),
                    '须列出确实看见行动或听见话的在场者，排除行动者本人')
            require(owner == pov or pov in witnesses, '视角人物没有看见或听见另一人的这拍言行；应改从实际见证者的视角叙述')
        else:
            require(beat.get('witnesses', []) == [], '私人想法、回忆和旁白没有现场见证者')
    require(time in ('current', 'past') and mode in MODES, '使用了未知时序或手法')
    require(isinstance(beat['effect'], str) and bool(beat['effect'].strip()), '缺少披露或行动效果')
    if mode in ('perception', 'thought', 'inference'):
        require(owner == pov, '直接感知、想法或推断必须属于本场视角人物')
    elif mode in ('speech', 'action'):
        require(owner in (pov, *body.get('characters', [])), '没有指定本场实际发言或行动者')
    else:
        require(owner is None or owner == pov, '回顾或概述只能由叙述者或本场视角人物承担')
    require(mode != 'reenactment' or time == 'past', '重演需要已经发生的经历')
    ref, quote = beat['basis_ref'], beat['basis_quote']
    require(isinstance(ref, str) and ref in bases, '没有本场可用的前置依据')
    basis = bases[ref]
    require(isinstance(quote, str) and bool(quote.strip()) and quote in basis['text'], '前置引文与所指事实不符')
    if access and basis['kind'] == 'scene' and ref.endswith(':planned_result'):
        require(mode not in ('perception', 'inference', 'thought'), '预定场尾结果不能单独作为人物已经察觉或知晓的依据')
    if time == 'past':
        require(basis['kind'] in ('history', 'state'), '回顾需要已发生的前史；不能把一般规则、计划或人物性格当成已发生的事件')
        if quote != basis['text']:
            from nw.materials.world_history import factual_history_claim
            sentence, start = _source_sentence(basis['text'], quote)
            require(factual_history_claim(sentence, start, start + len(quote)), '前史引文丢失了原句中的否定、传言或未决条件')
    if basis['kind'] == 'state':
        require(basis['audience'] == ('READER' if owner is None else owner), '将读者或人物私有事实交给了其他人')
        if basis.get('speaker_private'):
            require(time == 'current' and mode in ('speech', 'action'), '他人先前所知只可支持此人自己的现场发言或可见行动')
        elif basis['claim'] != 'fact':
            allowed = ('thought', 'inference', 'speech', 'action') if access else ('thought','inference')
            require(owner == pov and time == 'current' and mode in allowed,
                    '说法、打算与猜测只可解释本人当下的判断或言行，不能写成事实')
        if access and basis['claim'] != 'fact':
            require(quote == basis['text'], '须保留人物说法、意图或猜测的完整依据与归属')
    if basis['kind'] == 'voice':
        require(mode == 'speech' and owner == basis['subject'], '声线依据必须落到对应人物自己的台词')
    if basis.get('speaker_private') and basis['kind'] in ('history', 'character'):
        require(time == 'current' and mode in ('speech', 'action') and owner == basis['subject'],
                '只能让该人物以自己的私有经历或目的为据说话、行动')
        return
    if basis['kind'] == 'character':
        require(owner == pov, '视角人物的欲望、冲突或底线不能当作他人所知')
    if basis['kind'] in ('rule','history'):
        require(owner is not None or basis['public'], '叙述者不能向读者直接公开私密卡内容')
        require(not basis['subject'] or owner in (pov, None), '他人不能直接取得视角人物的私人经历')
        require(basis['public'] or owner == pov, '持有人专属设定不能交给其他人')
        if basis['public'] and basis['subject'] is None and owner is not None:
            require(mode in ('action','speech'), '不能只凭公共世界设定替人物补出亲历、判断或已知；须有本人的记忆、所见或所闻')
            require(not (access and basis['kind'] == 'history' and mode == 'speech'),
                    '公共前史不能单独证明发言人知道此事，请从其已知事实或实际获知途径交代')
    if basis['kind'] == 'beat' and owner is not None and not basis['shared']:
        require(owner == basis['owner'], '不能把只讲给读者或只属另一人的内容当成人物此刻的所知')
    if basis['kind'] == 'beat' and 'witnesses' in basis and owner is not None:
        require(owner == basis['owner'] or owner in basis['witnesses'], '后续反应者没有见证所引的前拍')
    if basis['kind'] == 'beat' and basis['claim'] in ('thought','inference','speech','perception'):
        require(quote == basis['text'], '须完整保留前拍话语、感知或推测的归属，不能摘成事实')
        require(mode not in ('summary','reenactment'), '人物的感知、推断或发言不能作为证实其内容的叙述依据')


def scene_check(guide: dict, index: int, order: int, pov: str, ids: dict, basis: dict,
                person: str | None = None, *, evidence_policy: bool = False) -> dict:
    beat = guide['narration']
    owner = beat['owner']
    observable = {'pov': ids.get(pov, pov), 'time': beat['time'], 'mode': beat['mode'],
                  'owner': ids.get(owner, owner), 'basis_quote': beat['basis_quote'],
                  'audience': 'reader_only' if owner is None else 'scene_pov', 'basis_claim': basis.get('claim', basis['kind']),
                  'observable': guide['observable'], 'effect': beat['effect']}
    if beat['time'] == 'past' and beat['basis_quote'] != basis['text']:
        observable['basis_sentence'] = _source_sentence(basis['text'], beat['basis_quote'])[0]
    if person:
        observable['narrative_person'] = person
        observable['witnesses'] = [ids.get(key, key) for key in beat.get('witnesses', [])]
    if basis['kind'] in ('cast_entry', 'cast_reveal'):
        observable['cast_subject'] = ids.get(basis['subject'], basis['subject'])
    from nw.materials.cast_design import reader_aside
    if reader_aside(guide, basis):
        observable['reader_identity'] = basis['confirmed_identity']
        observable['cast_subject'] = ids.get(basis['subject'], basis['subject'])
    check = guide['check']
    if basis.get('speaker_private'):
        # The expression designer and reviewer retain the confidential source.
        # The writer only needs the portion the actor actually says or does.
        observable.pop('basis_quote')
        if evidence_policy:
            observable.pop('effect')
            check = '写出这名人物实际说出的话或做出的动作，以及在场者能察觉的影响。'
    return {'id': f'work:narration:{guide["scene"]}:{index}', 'profile': 'method_work',
            'binding': {'observable': canonical(observable), 'check': check},
            'method_artifact': guide, 'narration_order': order, **({'narrative_person': person} if person else {}),
            **({'reported_only': beat['mode'] in ('speech', 'thought', 'inference')} if evidence_policy else {}),
            **({'narration_state_sha256': basis['state_sha256']} if 'state_sha256' in basis else {}),
            'evidence_required': '引用本场实际文字核对讲述次序、信息归属、前因与读者所得。'}
