# Content-layer implementation entry points

The skeleton ends at audited technical contracts. A later content phase may enter only through the
following public boundaries:

1. Add versioned provider adapters behind Model, Tool, extraction, verification, or multimodal ports;
   keep Fake/Null providers as the default and add an ADR before changing trust or data flow.
2. Add formal prompt metadata through the Agent descriptor contract; never embed credentials or let
   prompt text grant permissions.
3. Implement creative-domain behavior through Novel, World, Character, Creator, Consistency, and
   Quality application services; do not read another module's private tables.
4. Add content schemas as forward-only migrations with workspace/project ownership, provenance,
   retention, audit, export, and recovery coverage.
5. Add one opt-in content fixture in a separate test package. Keep the Stage 23 technical fixture
   unchanged so the skeleton gate remains content-free and deterministic.
6. Promote a parked extension only after its manifest criteria, permission review, failure behavior,
   observability, cost budget, and human approval path are tested.

Before any content implementation begins, create the phase plan and ADRs, define data licensing and
deletion rules, and decide which acceptance evidence is allowed to leave a local/CI runner. No Stage
23 CI step pushes images, deploys infrastructure, uploads project evidence, or calls a real model.
