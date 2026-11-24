"""Choose the next native planning level from approved work on this branch."""
from nw.plan_hierarchy import approved_parent, parent_chain
from nw.store import Store


SCOPE_LABELS = {'book': '全书设计', 'volume': '卷纲设计', 'chapter': '章纲与场景设计',
                'scene': '场景设计', 'replan': '调整设计'}


def design_route(store: Store, branch: str, scope: str | None = None,
                 parent_id: str | None = None) -> tuple[str, str | None]:
    if scope is None:
        if parent_id is not None:
            raise ValueError('指定上级方案时请同时选择设计层级')
        if volume := approved_parent(store, 'chapter', branch):
            return 'chapter', volume
        if book := approved_parent(store, 'volume', branch):
            return 'volume', book
        return 'book', None
    if scope == 'book':
        if parent_id is not None:
            raise ValueError('全书设计没有上级方案')
        return scope, None
    if scope not in ('volume', 'chapter'):
        raise ValueError('场景通过章纲确认后的场景设计制作，请选择全书、卷纲或章纲')
    parent = approved_parent(store, scope, branch, proposal_id=parent_id)
    if parent is None:
        needed = '全书方案' if scope == 'volume' else '卷纲'
        raise ValueError(f'请先在当前分支批准{needed}')
    return scope, parent


def next_design(store: Store, branch: str) -> dict:
    scope, parent = design_route(store, branch)
    result = {'scope': scope, 'label': SCOPE_LABELS[scope]}
    if parent is not None:
        result['approved_parent'] = parent_chain(store, scope, parent, branch=branch)[-1]
    return result
