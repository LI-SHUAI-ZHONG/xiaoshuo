"""Material catalog commands that do not open a story project."""
import argparse
from pathlib import Path

from nw.materials.catalog import build_catalog, list_catalog, show_fragment
from nw.materials.unit_catalog import index_units, list_units, refresh_fragment_units
from nw.materials.route_catalog import audit_routes, route
from nw.materials.identity_catalog import audit_identities
from nw.materials.placements import audit_placement
from nw.materials.adjudication import build_adjudications, inspect_adjudications
from nw.materials.layer_audit import audit_layers


def register_commands(commands: argparse._SubParsersAction) -> None:
    actions = commands.add_parser('materials', help='index and inspect local source material').add_subparsers(
        dest='action', required=True)
    build = actions.add_parser('build', help='index frozen inputs from a local manifest')
    build.add_argument('--source-root', required=True, type=Path)
    build.add_argument('--manifest', required=True, type=Path)
    listing = actions.add_parser('list', help='list versions or find original fragments')
    listing.add_argument('--source-id')
    listing.add_argument('--key')
    detail = actions.add_parser('index-units', help='index exact records and fields from frozen fragments')
    detail.add_argument('--source-id')
    detail.add_argument('--refresh', action='store_true', help='add newly parsed units and repair derived labels without replacing old source locations')
    detail.add_argument('--fragment-id', help='add newly recognized units to an existing frozen fragment')
    units = actions.add_parser('units', help='find record or field locations')
    units.add_argument('--source-id')
    units.add_argument('--fragment-id')
    units.add_argument('--key')
    units.add_argument('--kind')
    units.add_argument('--limit', type=int, default=100)
    units.add_argument('--offset', type=int, default=0)
    actions.add_parser('audit-routes', help='count dispositions across every indexed position')
    actions.add_parser('adjudicate', help='adjudicate complete source contracts and their candidate fields')
    recall = actions.add_parser('recall', help='inspect normal planning recall over all qualified sources')
    recall.add_argument('--text', required=True)
    recall.add_argument('--scope', choices=('book','volume','chapter','scene','replan'), default='book')
    children = actions.add_parser('type-children', help='inspect subtypes supported by the active ontology table')
    children.add_argument('--parent', required=True, help='the exact main type ID')
    layers = actions.add_parser('audit-layers', help='reconcile original sources, runtime translations and workflow effects')
    layers.add_argument('--details', action='store_true', help='include every owner and unresolved runtime position')
    semantics=actions.add_parser('audit-semantics',help='verify every original clause and build versioned step discovery')
    semantics.add_argument('--write-index',action='store_true')
    semantics.add_argument('--details-path',type=Path)
    bindings=actions.add_parser('audit-bindings',help='separate reviewed source uses from discovery candidates')
    bindings.add_argument('--details',action='store_true')
    governance=actions.add_parser('check-governance',help='execute pinned governance against explicit actual inputs')
    governance.add_argument('--inputs',required=True,type=Path)
    from nw.materials.work_knowledge import STAGES
    knowledge = actions.add_parser('work-knowledge', help='read work breakdown materials and check records')
    knowledge.add_argument('--stage', choices=tuple(STAGES), required=True)
    knowledge.add_argument('--inputs', type=Path, help='check a JSON file containing kind and records')
    decisions = actions.add_parser('decisions', help='inspect source-specific adjudications')
    decisions.add_argument('--state')
    decisions.add_argument('--profile')
    decisions.add_argument('--key', help='find source keys, native original IDs, or meanings containing this exact text')
    decisions.add_argument('--roots-only', action='store_true', help='show complete contracts rather than child fields')
    decisions.add_argument('--limit', type=int, default=50)
    decisions.add_argument('--offset', type=int, default=0)
    placement = actions.add_parser('audit-placement', help='reconcile registered files, recoveries and indexed versions')
    placement.add_argument('--manifest', type=Path)
    placement.add_argument('--supplement', type=Path)
    placement.add_argument('--source-root', type=Path, help='verify current files against their registered hashes')
    placement.add_argument('--path', help='inspect one registered repository-relative path')
    placement.add_argument('--details', action='store_true', help='include every file placement in the output')
    identities = actions.add_parser('audit-identities', help='compare network endpoints and legacy IDs')
    identities.add_argument('--legacy-aliases', required=True, type=Path)
    identities.add_argument('--dynamic-migrations', required=True, type=Path)
    dynamic = actions.add_parser('dynamic-ref', help='inspect an exact current or historically mapped dynamic edge')
    dynamic.add_argument('--id', required=True, help='current ID, or the ID in the explicit historical map')
    dynamic.add_argument('--legacy-map', type=Path, help='use the legacy ID in this migration file')
    routing = actions.add_parser('route', help='inspect a material route and its provenance')
    routing.add_argument('object_id')
    show = actions.add_parser('show', help='read a frozen fragment or unit by ID')
    show.add_argument('fragment_id')


def dispatch(workspace: Path, args: argparse.Namespace) -> dict:
    if args.action == 'dynamic-ref':
        from nw.materials.dynamic_refs import dynamic_reference
        return dynamic_reference(workspace, args.id, args.legacy_map)
    if args.action == 'type-children':
        from nw.materials.type_hierarchy import type_children
        return type_children(workspace, args.parent)
    if args.action == 'work-knowledge':
        import json
        from nw.materials.work_knowledge import work_knowledge

        inputs = json.loads(args.inputs.read_text(encoding='utf-8-sig')) if args.inputs else None
        if args.inputs and inputs is None:
            raise ValueError('WORK_KNOWLEDGE: inputs require kind and records')
        return work_knowledge(workspace, args.stage, inputs)
    if args.action=='audit-bindings':
        from nw.materials.binding_reviews import audit_bindings
        return audit_bindings(workspace,details=args.details)
    if args.action=='audit-semantics':
        from nw.materials.semantic_catalog import audit_semantic_sources
        return audit_semantic_sources(workspace,write_index=args.write_index,details_path=args.details_path)
    if args.action=='check-governance':
        import json
        from nw.materials.dynamic_refs import current_rule_proofs
        from nw.materials.governance_runtime import load_governance
        from nw.materials.governance_checks import evaluate_governance
        runtime=load_governance(workspace)
        if runtime is None:raise ValueError('MATERIAL_GOVERNANCE: exact governance source is absent')
        inputs=json.loads(args.inputs.read_text(encoding='utf-8-sig'))
        return evaluate_governance(runtime['contract'],inputs,current_rules=current_rule_proofs(workspace,inputs))
    if args.action == 'recall':
        from nw.materials.recall import recall_materials
        materials, report = recall_materials(workspace, args.text, scope=args.scope)
        return {'report': report, 'materials': materials}
    if args.action == 'build':
        return build_catalog(workspace, args.source_root, args.manifest)
    if args.action == 'list':
        return list_catalog(workspace, args.source_id, args.key)
    if args.action == 'index-units':
        if args.fragment_id:
            if args.source_id:
                raise ValueError('Choose either source-id or fragment-id')
            return refresh_fragment_units(workspace, args.fragment_id)
        return index_units(workspace, args.source_id, refresh=args.refresh)
    if args.action == 'units':
        return list_units(workspace, source_id=args.source_id, fragment_id=args.fragment_id,
                          key=args.key, kind=args.kind, limit=args.limit, offset=args.offset)
    if args.action == 'audit-routes':
        return audit_routes(workspace)
    if args.action == 'adjudicate':
        return build_adjudications(workspace)
    if args.action == 'audit-layers':
        return audit_layers(workspace, details=args.details)
    if args.action == 'decisions':
        return inspect_adjudications(workspace, state=args.state, profile=args.profile,
                                     key=args.key, roots_only=args.roots_only, limit=args.limit, offset=args.offset)
    if args.action == 'audit-placement':
        folder = workspace / 'materials'
        baseline = args.manifest or folder / '资料来源与版本登记_F0.json'
        supplement = args.supplement or folder / '资料来源补充_F2.json'
        return audit_placement(workspace, baseline, supplement=supplement if args.supplement or supplement.is_file() else None,
                               source_root=args.source_root, path=args.path, details=args.details)
    if args.action == 'audit-identities':
        return audit_identities(workspace, args.legacy_aliases, args.dynamic_migrations)
    if args.action == 'route':
        return route(workspace, args.object_id)
    return show_fragment(workspace, args.fragment_id)
