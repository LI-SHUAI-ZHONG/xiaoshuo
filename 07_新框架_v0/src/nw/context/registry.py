"""Named providers shared by write, flow and experiments."""
from dataclasses import asdict
from nw.context.base import ContextProvider
from nw.context.minimal import MinimalProvider
from nw.context.rules_pack import RulesPackProvider
from nw.store import Store

_PROVIDERS: dict[str, ContextProvider] = {}

def register(provider: ContextProvider) -> None:
    if not provider.name or provider.name in _PROVIDERS:
        raise ValueError('Context provider name is empty or already registered')
    _PROVIDERS[provider.name] = provider

def get_provider(name: str) -> ContextProvider:
    if name not in _PROVIDERS:
        raise ValueError(f'Unknown context provider: {name}')
    return _PROVIDERS[name]

def build_context(store: Store, scene_id: str, name: str = 'minimal',
                  confirmed: dict | None = None) -> dict:
    scene = store.get('scene', scene_id)
    entries = {(b.kind, b.name): asdict(b) for b in store.bible()}
    project = {'brief': asdict(store.briefs()[-1]) if store.briefs() else None,
               'bible': list(entries.values())}
    if confirmed is not None:
        project.update(confirmed)
    chapters = {c.id: c.index for c in store.list('chapter')}
    preceding = sorted((s for s in store.list('scene')
                        if (chapters[s.chapter_id], s.index) < (chapters[scene.chapter_id], scene.index)),
                       key=lambda s: (chapters[s.chapter_id], s.index))
    if preceding:
        accepted = store.accepted(preceding[-1].id)
        if accepted:
            project['previous'] = {'scene_id': preceding[-1].id,
                                   'text': store.get('draft', accepted.draft_id).text[-1200:]}
    return asdict(get_provider(name).build(project, project.get('scene', asdict(scene))))

register(MinimalProvider())
register(RulesPackProvider())
