"""Reviews pinned to a source version and one exact source position."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Review:
    file_sha256: str
    sha256: str
    profile: str
    meaning: str
    boundary: str
    evidence_required: str
    related: tuple[str, ...] = ()
    can_offer_for_design: bool = True


_LIBRARY = '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed'
_TYPES = 'aa0ac0359d8fb51d35a95f76cc29a652bab7dbfdbdf283a3fcf7acedefb4e582'
_CONVERSION = '85855cb19f02ca62643cb379eb6f34391f5394f48079f2fc9d438dded03f1c96'
_SELECTION = 'f4cfa62ab501ccdd5d077332e1f2144d6632a0875c3da4f1a6a341267452d715'
_GENRE_ONTOLOGY = 'f5902fbda992ec7c8a4a374b4b7fc03d823481d4e408936dd42c802044509eff'
_GENRE_MAIN = 'ef56420eaa6f6800ba8d8828d612ef9b8ca59956381bd52083dc1d904d332902'
_OTHERWORLD = 'f691a0d16efc176a5b8ecd08a1d67d7efa0dcc00d2969680cebdf18fe01c836e'
_STATIC = 'ad92fcb188673021350876bbdb2e759a1988f5832363abe53dce2d84cced74a9'
_DYNAMIC = 'bdde74478e04bda4f879c25d3629049613195b94b8976bde3fd306d661be60ea'
_EXECUTION = 'f2e7725e845dcc349cb54df79992a411bbd034197fb811b287e8066993a04ef8'
CHARACTER_EDITOR = 'cf229c363f41b71b98e8ab1e1826df1f8694d4607870c9f396a39d9cb83cd0ad'

_REVIEWS = {
    CHARACTER_EDITOR: Review(
        _EXECUTION, '9b02f796a78d5f140c06e1721a2c734ac5b6b0bc5ae6a88ab36d98571d7c427f', 'character_editor',
        '对照人物设定检查核心属性、能力边界、行为和角色声音。',
        '适用于本场出场且已经获批的人物，以分支当前人物卡替代旧储备库路径。',
        '人物卡版本、当前稿中的动作或台词、涉及的设定及有无偏离的理由。'),
    _CONVERSION: Review(
        _LIBRARY,'13e638eb6f40d8bf5b21b41ccea29c7626474e5af122db650f138dd6b02828b2',
        'material_conversion','板块用途映射到设计参数和可写表现。','只处理已选用、直接支撑当前任务的板块。',
        '每一项在场景设计中给出参数、正文表现及可检验点。',(_SELECTION,)),
    '3e53d0d96b4cf65c8aabd63fd85b8dc7218ff6112f09dec6a01bfee5bf2a95fd': Review(
        _LIBRARY,'b253b042c4bec59ac6b68548754a37bbcbd06623a6967944db12ddd2ea4ffbdf',
        'material_conversion','先确定章节或场景，再把相关板块转化为可查的清单。','相关性不明的板块留待选配。',
        '设计中能定位每项参数、预期表现和验证点。',(_CONVERSION,_SELECTION)),
    _SELECTION: Review(
        _LIBRARY,'fb0374e66cfed9dc8a5b66dc160d94d83ec9e53e980d53a3d9546eb486e0eab4',
        'material_selection','先定章场功能，再选板块，最终精确到必需子项。','板块命中不等于具体子项已选。',
        '清单保留功能、匹配理由、子项定位和未采用原因。'),
    'bfc45fe9c88aa379b22006eb1d52596e0b6c370348036575e794d782c2bfedf9': Review(
        _LIBRARY,'13d4bd01f140528b7b51a8cce379d57fecfc54e448aec0aa2e0ffda310f2c83f',
        'editor','比较各章叙述句式、用词和叙述距离。','适用范围是叙述语言；同条目身体信号指令进入冲突处置。',
        '至少两处冻结稿叙述段落、语体对照和判断理由。'),
    _GENRE_ONTOLOGY: Review(
        _TYPES,'2c49791300e78a485ce2d0029ef12e9ecebfa1dea48c8b512fc86801abe5ad4f',
        'type_identity','类型本体记录将力量体系、等级成长和超自然世界观列为核心特征。',
        '来源引用为空，且同 ID 主类型表更强调力量体系的自由度。采用前明确所选描述及项目范围。',
        '类型契约记录选用的版本、类型承诺和具体卷章兑现方式。',(_GENRE_MAIN,)),
    _GENRE_MAIN: Review(
        _TYPES,'f60a792de4385414aebf7e4495f92773eae55a51506a6e063e141a3cab2d8351',
        'type_identity','主类型记录强调架空世界、超自然力量和可自定义的力量体系。',
        '名称与类型本体共用 ID，定义、别名和排除条件须按各自来源审查。',
        '列明选用定义、排除条件和作者确认的项目类型契约。',(_GENRE_ONTOLOGY,)),
    _OTHERWORLD: Review(
        _TYPES,'df386c7bd0b519d63122c7881b6814637757c0340d2eb7e2f7518015fc999c71',
        'type_identity','异界玄幻以主角来到截然不同的世界细化玄幻。',
        '采用须能说明两个世界的区别；项目不能从类型条目推定穿越机制。',
        '作者确认主副层级与异界差异，并安排读者可观察的兑现。',(_GENRE_MAIN,)),
    'fd02114a073db1c56fab32128e51860a0c02425222aebc60c638c1b815077e96': Review(
        'e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0',
        'a8d268ecbe1aea2f7b65c0004e8e5d2f5819706b0384ad5d4b7b3862aef08766','type_link',
        'TSC_003064 为异界玄幻到玄幻的定向细化关系，与子类型原件的 parent_id 一致。',
        '仅用于主类型与子类型的契约边界。触发、选择和代价须由项目设计并经作者确认。',
        '采用的两个来源、子类型细化承诺及设计证据。',(_OTHERWORLD,_GENRE_MAIN,_GENRE_ONTOLOGY)),
    'c30a411b2ef04835c8ed477d7090b3276002490e0a9950c86a529adf1624928e': Review(
        'e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0',
        '61d3ec4030af8310f6f97556dbe89b5ff7475a3c1e4d7083dbaffc0a1b38540b','type_link',
        '仙侠、成长机制与线性结构的候选记录，列出候选效果及连续性约束。',
        '组成类型只有仙侠，触发条件 ID 与失败分支为空。适用性待定，不能据此确认第二类型或状态变化。',
        '选型记录、触发证据、因果约束和独立验证结果。', can_offer_for_design=False),
    _STATIC: Review(
        '0a415d8d38642b352521abc15650f93e1fda10f1c3b4225f2c17cab70c89d197',
        '81334bc8f50a0d907eee9f9089f143c28300213d7a6cd6391b1b74186d584c9b','static_binding',
        '主角与核心悬念之间是主线绑定关系。','资料标签须分别绑定到项目中的人物和悬念，确认主线范围。',
        '两端项目 ID、主线范围、行动受限点和采用证据。',(_DYNAMIC,)),
    _DYNAMIC: Review(
        'd6093b82fe6e072bdff7300fadcf175112b988d319c6b836f5d5b881b5282cc6',
        '243f5cd3f755b755232e189a8f9f20117c4b137449627a8fde9c95fa6494b1cc','dynamic_binding',
        '从静态绑定推导出终点状态可能随起点变化。','先采用相应静态边；当前效果是通用表述，仍须给出具体人物选择、代价和后果。',
        '前置静态关系、可观察触发、接受稿的前后状态与相关人物所知。',(_STATIC,)),
    '7ed02b4096e9293ad391dc98bc5ff122c9410ae5fc8b309e385e3314e5cfadeb': Review(
        '9b7ea71e53613a453fe71fa0a862411f65f22328a38ee7b97db7fd5bab7be759',
        'd2a26d80cd509f0ae48031460ddfe46af990b086a8e8886e5c5b881469855bf8','anchor',
        'M1.1 是道具完整状态的物质锚点。','原条件为道具未被使用或未被损坏。实际物件和可见时机由场景绑定。',
        '可定位到该物件的段落，核对观察者、道具前状态和动作证据。'),
}


def source_review(row: dict, profile: str) -> Review | None:
    review = _REVIEWS.get(row['id'])
    if review is not None and (row['file_sha256'],row['sha256'],profile)==(
        review.file_sha256,review.sha256,review.profile
    ):
        return review
    return None
