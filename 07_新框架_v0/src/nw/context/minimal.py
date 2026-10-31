"""Minimal author context, with explicitly scoped character entries."""
import json
from nw.context.base import ContextItem, ContextPackage, package

class MinimalProvider:
    name = 'minimal'

    def build(self, project: dict, scene: dict) -> ContextPackage:
        items = []
        brief = project.get('brief')
        if brief:
            items.append(ContextItem('brief', json.dumps(brief, ensure_ascii=False), '最新作者需求'))
        card = json.loads(scene['card_json'])
        searchable = json.dumps(card, ensure_ascii=False)
        for entry in project.get('bible', []):
            if entry['kind'] == 'character' and entry['name'] not in searchable:
                continue
            items.append(ContextItem(f"bible:{entry['kind']}:{entry['name']}",
                                     json.dumps(entry, ensure_ascii=False),
                                     '场景卡提及人物' if entry['kind'] == 'character' else '项目通用设定/文风/禁忌'))
        items.append(ContextItem('scene:' + scene['id'], json.dumps(scene, ensure_ascii=False), '当前场景卡'))
        if project.get('previous'):
            items.append(ContextItem('previous:' + project['previous']['scene_id'],
                                     project['previous']['text'], '上一场景已接受正文末尾（最多1200字符）'))
        return package(items)
