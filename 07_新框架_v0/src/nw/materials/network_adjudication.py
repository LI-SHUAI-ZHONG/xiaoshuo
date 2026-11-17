"""Evaluate complete baseline network edges against their pinned source identities."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from nw.task_models import _text

_READY = {'current_heading', 'current_subheading', 'reviewed_alias', 'reviewed_component'}


def source_ref(row: dict) -> dict:
    return {key: row[key] for key in ('id', 'source_id', 'path', 'file_sha256', 'sha256',
                                      'byte_start', 'byte_end', 'line_start', 'line_end')}


class NetworkAdjudicator:
    def __init__(self, connection: sqlite3.Connection, workspace: Path) -> None:
        self.db = connection
        self.decisions = {}
        self.edges = {}
        self.static = defaultdict(list)
        for row in self.db.execute("""
                SELECT f.id,f.payload,f.sha256,s.family FROM fragments f JOIN sources s ON s.id=f.source_id
                WHERE s.layer='baseline' AND s.family IN ('static','dynamic') AND f.kind='network_edge'
                """):
            raw = row['payload']
            if sha256(raw).hexdigest() != row['sha256']:
                raise ValueError(f"Material fragment hash mismatch: {row['id']}")
            data = json.loads(raw)
            data.pop('运行层升级', None)
            self.edges[row['id']] = (row['family'], data)
            if row['family'] == 'static':
                self.static[data.get('source'), data.get('target'), data.get('type')].append(row['id'])
        self.endpoints = defaultdict(list)
        report = workspace / 'materials' / 'F2_网络身份对账.json'
        if report.is_file():
            document = json.loads(report.read_text(encoding='utf-8-sig'))
            for endpoint in document['endpoints']:
                for edge in endpoint['edge_references']:
                    self.endpoints[edge['fragment_id']].append((edge, endpoint))

    def review(self, row: dict) -> dict | None:
        if row['layer'] != 'baseline' or row['family'] not in {'static', 'dynamic'}:
            return None
        ident = row['fragment_id']
        if ident not in self.edges:
            return None
        if ident not in self.decisions:
            root = dict(self.db.execute("""
                SELECT f.id,f.source_id,s.path,s.file_sha256,f.sha256,f.byte_start,f.byte_end,
                       f.line_start,f.line_end FROM fragments f JOIN sources s ON s.id=f.source_id WHERE f.id=?
                """, (ident,)).fetchone())
            self.decisions[ident] = self._edge(root)
        result = self.decisions[ident]
        if row['id'] != ident:
            return {**result, 'state': 'context', 'can_offer_for_design': False, 'owner_id': ident,
                    'meaning': '该字段随完整网络边一起核对适用条件、依赖和证据。'}
        return result

    def _edge(self, root: dict) -> dict:
        family, data = self.edges[root['id']]
        missing = [key for key in ('source', 'target', 'type', 'condition') if not _text(data.get(key))]
        identities, conflicts = [], []
        references = [source_ref(root)]
        for edge, endpoint in self.endpoints[root['id']]:
            if edge['sha256'] != root['sha256'] or edge['file_sha256'] != root['file_sha256']:
                conflicts.append('endpoint_report_version')
                continue
            source = endpoint.get('review')
            locations = [source['location']] if source and source.get('location') else [
                ref for ref in endpoint['locations'] if ref['layer'] == 'baseline']
            if endpoint['status'] not in _READY or not locations:
                missing.append(f"endpoint:{edge['side']}:{endpoint['label']}:{endpoint['status']}")
            else:
                for ref in locations:
                    actual = self.db.execute('SELECT source_id,byte_start,byte_end,payload FROM fragments WHERE id=?',
                                             (ref['fragment_id'],)).fetchone()
                    left = ref['byte_start'] - actual['byte_start'] if actual else -1
                    right = ref['byte_end'] - actual['byte_start'] if actual else -1
                    if (actual is None or actual['source_id'] != ref['source_id']
                            or not 0 <= left < right <= len(actual['payload'])
                            or sha256(actual['payload'][left:right]).hexdigest() != ref['sha256']):
                        conflicts.append(f"endpoint_source:{endpoint['label']}")
                    else:
                        references.append({'id': ref['fragment_id'], **ref})
                identities.append({'side': edge['side'], 'label': endpoint['label'], 'locations': locations,
                                   'original': [self._definition(ref) for ref in locations]})
        if {item['side'] for item in identities} != {'source', 'target'}:
            missing.append('two_verified_endpoint_definitions')
        related = []
        if family == 'dynamic':
            if not _text(data.get('effect')):
                missing.append('effect')
            if data.get('needs_review'):
                conflicts.append('source_explicitly_requires_review')
            if data.get('generated_from_static'):
                related = self.static[data.get('source'), data.get('target'), data.get('type')]
                if len(related) != 1:
                    missing.append('unique_upstream_static_edge')
        ready = not missing and not conflicts
        profile = 'static_relation' if family == 'static' else 'dynamic_relation'
        contract = {
            'source': data.get('source'), 'target': data.get('target'), 'relation': data.get('type'),
            'condition': data.get('condition'), 'effect': data.get('effect'),
            'valid_types': data.get('valid_types', []),
            'generated_from_static': bool(data.get('generated_from_static')),
            'identities': identities,
        }
        return {
            'state': 'design_ready' if ready else 'blocked', 'can_offer_for_design': ready, 'profile': profile,
            'meaning': f"{data.get('source')} 经 {data.get('type')} 关系连接 {data.get('target')}。",
            'boundary': '本项提供资料概念间的关系。项目采用须明确双方实体、源条件成立证据及具体行动后果。',
            'evidence_required': ('两个项目实体、关系范围、原条件和行动限制的设计及正文证据。'
                                  if family == 'static' else
                                  '前状态、触发、行动、代价、失败分支、后状态及知情边界，全部绑定同稿证据。'),
            'source_refs': references, 'conditions': [data['condition']] if _text(data.get('condition')) else [],
            'missing': sorted(set(missing)), 'conflicts': sorted(set(conflicts)),
            'related': related, 'contract': contract,
        }

    def _definition(self, ref: dict) -> dict:
        original = self.db.execute('SELECT byte_start,payload FROM fragments WHERE id=?',
                                   (ref['fragment_id'],)).fetchone()
        if original is None:
            return {'ref': ref, 'text': ''}
        left, right = ref['byte_start'] - original['byte_start'], ref['byte_end'] - original['byte_start']
        data = original['payload'][left:right] if 0 <= left < right <= len(original['payload']) else b''
        return {'ref': ref, 'text': data.decode('utf-8')}

