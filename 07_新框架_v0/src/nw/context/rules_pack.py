"""Small hand-selected JSON rules only; never reads original source libraries."""
import json
from pathlib import Path
from nw.context.base import ContextItem, ContextPackage, package
from nw.context.minimal import MinimalProvider

RULES = Path(__file__).resolve().parents[3] / 'fixtures' / 'rules'

class RulesPackProvider:
    name = 'rules_pack'

    def build(self, project: dict, scene: dict) -> ContextPackage:
        items = MinimalProvider().build(project, scene).items
        tags = json.loads(scene['card_json']).get('tags', [])
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            raise ValueError('Scene tags must be a list of strings')
        for path in sorted(RULES.glob('*.json')):
            for rule in json.loads(path.read_text(encoding='utf-8')):
                matches = sorted(set(tags) & set(rule['tags']))
                if matches:
                    items.append(ContextItem('rule:' + rule['id'], rule['text'],
                                             '匹配场景标签：' + '、'.join(matches)))
        return package(items)
