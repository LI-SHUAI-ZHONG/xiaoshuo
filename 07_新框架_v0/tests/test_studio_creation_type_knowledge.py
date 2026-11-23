"""Production keeps the type knowledge selected at project creation."""
from pathlib import Path
import json

from nw.studio.library import LibraryService
from nw.task_models import canonical


def test_frozen_type_knowledge_survives_an_editorial_update(tmp_path: Path) -> None:
    from nw.materials.author_references import author_stage_input
    from nw.studio.api import StudioService
    from nw.studio.kb import freeze_type_knowledge
    from nw.studio.production import ProductionService

    workspace = tmp_path / 'workspace'
    studio = StudioService(workspace, config_path=tmp_path / 'missing.toml')
    library = LibraryService(studio.workspace)
    types = ['GENRE_XUANHUAN', 'SUB_XUANHUAN_01']
    library.save_type(types[0], {'definition': '以自行设计的力量体系驱动人物成长',
                                 'includes': ['能力须影响选择'], 'excludes': ['直接沿用原作设定'],
                                 'features': ['代价兑现'], 'examples': ['给能力设限'],
                                 'counterexamples': ['代价只在设定表出现']})

    production = ProductionService(studio, library)
    created = production.create({'title': '照界录', 'idea': '藏书人调查法术代价', 'genre_ids': types})
    assert created['run']['status'] == 'CONFIG_REQUIRED'
    library.save_type(types[0], {'version': 1, 'definition': '新定义', 'features': ['新知识']})
    reopened = LibraryService(studio.workspace)
    production = ProductionService(studio, reopened)
    novel = production.db.get(created['novel']['id'])
    saved = novel['wizard']['creation_plan']['types']
    with production.open_store(novel) as store:
        request = json.loads(store.connection.execute(
            'SELECT request_json FROM novel_jobs WHERE id=?', (novel['job_id'],)).fetchone()[0])

    assert [row['id'] for row in saved] == types
    assert saved[0]['origin'] == 'editorial' and saved[0]['version'] == 1
    assert saved[0]['definition'] == '以自行设计的力量体系驱动人物成长'
    assert saved[0]['excludes'] == ['直接沿用原作设定']
    assert saved[0]['features'] == ['代价兑现']
    assert saved[0]['examples'] == ['给能力设限']
    assert saved[0]['counterexamples'] == ['代价只在设定表出现']
    assert saved[0]['source_ref'] == {'file': 'type_selection_genres.py', 'original_line': 3103}
    assert saved[1]['origin'] == 'workflow' and saved[1]['version'] == 0
    assert saved[1]['source_ref'] == {
        'file': 'type_selection_xuanhuan_subgenres.py', 'original_line': 3908,
    }
    for stage in ('type_selection', 'type_adaptation'):
        packet = author_stage_input(request, stage)['creation_plan']
        assert packet['types'] == saved
    assert 'creation_plan' not in author_stage_input(request, 'plot_design')
    current = freeze_type_knowledge(reopened, types)
    assert current[0]['version'] == 2 and current[0]['definition'] == '新定义'
    assert current[0]['sha256'] != saved[0]['sha256']
    assert current[1]['sha256'] == saved[1]['sha256']


def test_type_knowledge_excerpt_keeps_evidence_and_marks_omitted_content(tmp_path: Path) -> None:
    from nw.studio.kb import freeze_type_knowledge, project_type_knowledge

    library = LibraryService(tmp_path / 'workspace')
    types = ['GENRE_XUANHUAN']
    library.save_type(types[0], {
        'definition': '界' * 10000,
        'includes': [str(idx) + '长' * 990 for idx in range(100)],
        'excludes': ['本类型排除任意具名原作人物'],
        'examples': ['例' * 800],
    })
    frozen = freeze_type_knowledge(library, types)
    row, = project_type_knowledge(frozen)

    assert len(canonical(row)) < 10_000
    assert row['source_ref'] == frozen[0]['source_ref']
    assert row['sha256'] == frozen[0]['sha256']
    assert row['excludes'] == ['本类型排除任意具名原作人物']
    assert set(row['excerpt_limits']) == {'definition', 'includes', 'examples'}
    assert len(frozen[0]['definition']) == 10000
    assert len(frozen[0]['includes']) == 100
