"""Persisted six-node inputs and outputs."""
from dataclasses import asdict
import json

from nw.generation import encode
from nw.store import Store

NODE_IDS = ('N1', 'N2', 'N3', 'N4', 'N5', 'N6')


class NodeStore:
    def __init__(self, store: Store, scene_id: str) -> None:
        self.store, self.scene_id = store, scene_id

    def author_input(self, node: str) -> dict:
        if node == 'N1':
            return {'brief': asdict(self.store.briefs()[-1])}
        if node == 'N2':
            entries = {(b.kind, b.name): b for b in self.store.bible()}
            return {'bible': [asdict(b) for b in entries.values()]}
        scene = self.store.get('scene', self.scene_id)
        return {'chapter': asdict(self.store.get('chapter', scene.chapter_id)), 'scene': asdict(scene)}

    def create(self, settings: dict, notes: list[dict]) -> None:
        if not notes or any(not isinstance(n, dict) or set(n) != {'kind', 'text'}
                            or n['kind'] not in ('character_state', 'foreshadow', 'fact')
                            or not isinstance(n['text'], str) or not n['text'].strip() for n in notes):
            raise ValueError('Provide nonempty author state notes: [{kind, text}]')
        if not self.store.briefs():
            raise ValueError('Record an author brief before starting the flow')
        scene = self.store.get('scene', self.scene_id)
        entries = {(b.kind, b.name): b for b in self.store.bible()}
        inputs = {'N1': {'brief': asdict(self.store.briefs()[-1])},
                  'N2': {'bible': [asdict(b) for b in entries.values()]},
                  'N3': {'chapter': asdict(self.store.get('chapter', scene.chapter_id)), 'scene': asdict(scene)},
                  'N4': {'sources': ['N1', 'N2', 'N3']},
                  'N5': {'source': 'N4'}, 'N6': {'notes': notes}}
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            if self.store.connection.execute('SELECT 1 FROM flow_meta WHERE scene_id=?', (self.scene_id,)).fetchone():
                raise ValueError('Flow already exists; use flow resume')
            self.store.connection.execute('INSERT INTO flow_meta VALUES (?,?,?)', (self.scene_id, encode(settings), encode(notes)))
            for node in NODE_IDS:
                self.store.connection.execute('INSERT INTO flow_nodes VALUES (?,?,?,?,?)',
                    (self.scene_id, node, 'PLANNED', encode(inputs[node]), '{}'))

    def check_settings(self, settings: dict) -> None:
        row = self.store.connection.execute('SELECT settings_json FROM flow_meta WHERE scene_id=?', (self.scene_id,)).fetchone()
        if row is None:
            raise ValueError('Flow does not exist; use flow run')
        original = json.loads(row[0])
        original.setdefault('context', 'minimal')  # Pre-M4 flows keep their saved N4 package.
        if original != settings:
            raise ValueError('Resume requires the original provider, model, parameters and endpoint')

    def get(self, node: str) -> dict:
        row = self.store.connection.execute('SELECT status,input_json,output_json FROM flow_nodes WHERE scene_id=? AND node=?',
                                           (self.scene_id, node)).fetchone()
        if row is None:
            raise ValueError('Flow node does not exist')
        return {'node': node, 'status': row[0], 'input': json.loads(row[1]), 'output': json.loads(row[2])}

    def save(self, node: str, status: str, output: dict, inputs: dict | None = None) -> None:
        with self.store.connection:
            self.save_in_transaction(node, status, output, inputs)

    def save_in_transaction(self, node: str, status: str, output: dict, inputs: dict | None = None) -> None:
        if inputs is None:
            inputs = self.get(node)['input']
        self.store.connection.execute("UPDATE flow_nodes SET status=?,input_json=?,output_json=? WHERE scene_id=? AND node=? AND status!='DONE'",
                                      (status, encode(inputs), encode(output), self.scene_id, node))
