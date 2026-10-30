/*
 * Build a non-destructive, hash-locked mapping from the largest absorbed
 * material backup. The source files remain untouched.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const U = (...codes) => String.fromCharCode(...codes);
const DOC = U(0x6587, 0x6863);
const MERGE = U(0x5408, 0x5e76, 0x5347, 0x7ea7);
const START = U(0x5f00, 0x59cb);
const END = U(0x7ed3, 0x675f);
const CLASSIFIED = U(0x5206, 0x7c7b, 0x5347, 0x7ea7, 0x8d44, 0x6599);
const RAW = U(0x539f, 0x6837, 0x642c, 0x5165, 0x5347, 0x7ea7, 0x8d44, 0x6599);
const STRICT = U(0x4e25, 0x683c, 0x5347, 0x7ea7, 0x8bb0, 0x5f55, 0x539f, 0x6837, 0x642c, 0x5165);
const JSON_MARKER = U(0x539f, 0x59cb, 0x5347, 0x7ea7, 0x5185, 0x5bb9, 0x28, 0x4a, 0x53, 0x4f, 0x4e, 0x29);

const PROJECT_ROOT = process.cwd();
const mergeRoot = path.join(PROJECT_ROOT, DOC, MERGE);
const selectedBatch = 'material-absorption-20260818T054129Z';
const batchName = fs.readdirSync(mergeRoot, { withFileTypes: true })
  .find((item) => item.isDirectory() && item.name === selectedBatch)?.name;

if (!batchName) {
  throw new Error(`Selected absorption batch does not exist: ${selectedBatch}`);
}

const batchRoot = path.join(mergeRoot, batchName);
const backupName = fs.readdirSync(batchRoot, { withFileTypes: true })
  .find((item) => item.isDirectory())?.name;
if (!backupName) {
  throw new Error('The absorption batch has no material backup directory.');
}

const backupRoot = path.join(batchRoot, backupName);
const defaultOutputName = 'runtime-upgrade-precision-20260819-01';
const outputName = process.argv[2] || defaultOutputName;
const outputRoot = path.resolve(mergeRoot, outputName);
if (fs.existsSync(outputRoot)) {
  throw new Error(`Output already exists and will not be overwritten: ${outputRoot}`);
}

const blockTypes = [
  { layer: 'classified_upgrade', start: `===== ${CLASSIFIED}${START} =====`, end: `===== ${CLASSIFIED}${END} =====` },
  { layer: 'raw_upgrade', start: `===== ${RAW}${START} =====`, end: `===== ${RAW}${END} =====` },
  { layer: 'strict_upgrade', start: `===== ${STRICT}${START} =====`, end: `===== ${STRICT}${END} =====` },
];

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function lineValue(body, label) {
  const at = body.indexOf(label);
  if (at < 0) return null;
  const lineEnd = body.indexOf('\n', at);
  return body.slice(at + label.length, lineEnd < 0 ? body.length : lineEnd).trim() || null;
}

function findJsonObjects(body) {
  const parsed = [];
  for (let start = body.indexOf('{'); start >= 0; start = body.indexOf('{', start + 1)) {
    let depth = 0;
    let quoted = false;
    let escaped = false;
    let completeAt = -1;
    for (let index = start; index < body.length; index += 1) {
      const char = body[index];
      if (quoted) {
        if (escaped) escaped = false;
        else if (char === '\\') escaped = true;
        else if (char === '"') quoted = false;
        continue;
      }
      if (char === '"') quoted = true;
      else if (char === '{') depth += 1;
      else if (char === '}') {
        depth -= 1;
        if (depth === 0) {
          completeAt = index;
          break;
        }
      }
    }
    if (completeAt < 0) continue;
    try {
      const value = JSON.parse(body.slice(start, completeAt + 1));
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        parsed.push(value);
        start = completeAt;
      }
    } catch {
      // Keep scanning: prose blocks may contain JSON-like fragments.
    }
  }
  return parsed;
}

function extractBlocks(text) {
  const blocks = [];
  let cursor = 0;
  while (cursor < text.length) {
    let selected = null;
    for (const type of blockTypes) {
      const offset = text.indexOf(type.start, cursor);
      if (offset >= 0 && (!selected || offset < selected.offset)) {
        selected = { ...type, offset };
      }
    }
    if (!selected) break;
    const contentStart = selected.offset + selected.start.length;
    const contentEnd = text.indexOf(selected.end, contentStart);
    if (contentEnd < 0) {
      blocks.push({ ...selected, content: text.slice(contentStart), closed: false });
      break;
    }
    blocks.push({ ...selected, content: text.slice(contentStart, contentEnd), closed: true });
    cursor = contentEnd + selected.end.length;
  }
  return blocks;
}

function classify(payload) {
  const changes = Array.isArray(payload.changes) ? payload.changes : [];
  const hasFieldChanges = changes.some((change) => change && typeof change.field_path === 'string');
  const hasOverlay = typeof payload.field_path === 'string' && Object.hasOwn(payload, 'candidate_value');
  const hasOriginal = typeof payload.original_object_id === 'string' || typeof payload.target_object_id === 'string';
  const hasBinding = typeof payload.binding_id === 'string' || (Array.isArray(payload.binding_ids) && payload.binding_ids.length > 0);
  if (hasFieldChanges && hasOriginal) return 'object_field_patch';
  if (hasFieldChanges) return 'unbound_field_patch';
  if (hasOverlay) return 'semantic_overlay';
  if (hasOriginal) return 'object_mapping_only';
  if (hasBinding) return 'binding_or_runtime_audit';
  return 'runtime_or_audit_record';
}

function safeValue(value) {
  if (value === undefined) return null;
  return value;
}

function compactRecord(file, index, block, payload, sourceMeta) {
  const changes = Array.isArray(payload.changes) ? payload.changes : [];
  const className = classify(payload);
  const writebackAllowed = payload.writeback_allowed === true;
  const pending = /pending|review|quarantined/i.test(String(payload.status || payload.review_status || ''));
  const needsValueMatch = className === 'object_field_patch';
  const patchFields = changes
    .filter((change) => change && typeof change.field_path === 'string')
    .map((change) => ({
      field_path: change.field_path,
      operation: safeValue(change.operation),
      before: safeValue(change.before),
      after: safeValue(change.after),
      reason: safeValue(change.reason),
    }));
  const recordId = `${file}:${String(index).padStart(6, '0')}`;
  return {
    record_id: recordId,
    material_file: file,
    embedded_layer: block.layer,
    block_closed: block.closed,
    source: sourceMeta.source,
    source_sha256: sourceMeta.source_sha256,
    upgrade_method: sourceMeta.upgrade_method || safeValue(payload.upgrade_method),
    source_kind: safeValue(payload.source_kind),
    schema_version: safeValue(payload.schema_version),
    status: safeValue(payload.status),
    review_status: safeValue(payload.review_status),
    upgrade_id: safeValue(payload.upgrade_id),
    strict_upgrade_ids: safeValue(payload.strict_upgrade_ids),
    binding_id: safeValue(payload.binding_id),
    binding_ids: safeValue(payload.binding_ids),
    source_id: safeValue(payload.source_id),
    source_file: safeValue(payload.source_file),
    original_object_id: safeValue(payload.original_object_id),
    target_object_id: safeValue(payload.target_object_id),
    field_path: safeValue(payload.field_path),
    semantic_key: safeValue(payload.semantic_key),
    resolution: safeValue(payload.resolution),
    candidate_value: safeValue(payload.candidate_value),
    classification: className,
    patch_fields: patchFields,
    exact_object_locator: safeValue(payload.original_object_id || payload.target_object_id),
    has_before_snapshot: payload.before !== undefined,
    baseline_object_sha256: safeValue(payload.before_sha256 || payload.baseline_object_sha256),
    writeback_allowed: writebackAllowed,
    automatic_writeback_status: writebackAllowed && !pending && patchFields.length > 0
      ? 'requires_current_value_verification'
      : 'blocked_by_source_contract',
    blocking_reason: writebackAllowed && !pending && patchFields.length > 0
      ? null
      : safeValue(payload.writeback_allowed === false
        ? 'source_explicitly_disallows_writeback'
        : pending
          ? 'record_is_pending_or_requires_review'
          : patchFields.length === 0
            ? 'record_has_no_field_level_replacement'
            : 'record_has_no_writeback_authorization'),
    payload_sha256: sha256(JSON.stringify(payload)),
  };
}

function appendJsonl(handle, row) {
  fs.writeSync(handle, `${JSON.stringify(row)}\n`);
}

fs.mkdirSync(outputRoot, { recursive: false });
const registryHandle = fs.openSync(path.join(outputRoot, 'runtime-layer-register.jsonl'), 'w');
const preciseHandle = fs.openSync(path.join(outputRoot, 'precise-upgrade-map.jsonl'), 'w');
const blockedHandle = fs.openSync(path.join(outputRoot, 'blocked-or-incomplete-upgrades.jsonl'), 'w');

const catalog = [];
const totals = {
  main_files: 0,
  runtime_blocks: 0,
  parsed_payloads: 0,
  object_field_patches: 0,
  semantic_overlays: 0,
  object_mapping_only: 0,
  binding_or_runtime_audit: 0,
  runtime_or_audit_record: 0,
  unique_precise_entries: 0,
  duplicate_precise_instances: 0,
  auto_writeback_candidates: 0,
  blocked_or_incomplete: 0,
};
const preciseSeen = new Set();

try {
  const materialFiles = fs.readdirSync(backupRoot, { withFileTypes: true })
    .filter((item) => item.isFile())
    .map((item) => item.name)
    .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));

  for (const file of materialFiles) {
    const filePath = path.join(backupRoot, file);
    const bytes = fs.readFileSync(filePath);
    const text = bytes.toString('utf8');
    const blocks = extractBlocks(text);
    const firstBlockOffset = blocks.length ? blocks[0].offset : text.length;
    const mainBytes = Buffer.from(text.slice(0, firstBlockOffset), 'utf8');
    const fileCatalog = {
      material_file: file,
      source_path: path.relative(PROJECT_ROOT, filePath).replaceAll('\\', '/'),
      total_bytes: bytes.length,
      source_sha256: sha256(bytes),
      main_material_bytes: mainBytes.length,
      main_material_sha256: sha256(mainBytes),
      embedded_runtime_start_char: firstBlockOffset,
      embedded_runtime_block_count: blocks.length,
      parsed_payload_count: 0,
    };
    let recordIndex = 0;
    for (const block of blocks) {
      const sourceMeta = {
        source: lineValue(block.content, `${U(0x6765, 0x6e90)}: `) || lineValue(block.content, `${U(0x539f, 0x59cb, 0x6765, 0x6e90)}: `),
        source_sha256: lineValue(block.content, `${U(0x6765, 0x6e90, 0x53, 0x48, 0x41, 0x32, 0x35, 0x36)}: `) || lineValue(block.content, `${U(0x6765, 0x6e90, 0x53, 0x48, 0x41, 0x32, 0x35, 0x36)}: `),
        upgrade_method: lineValue(block.content, `${U(0x5347, 0x7ea7, 0x65b9, 0x6cd5)}: `),
      };
      for (const payload of findJsonObjects(block.content)) {
        recordIndex += 1;
        fileCatalog.parsed_payload_count += 1;
        totals.parsed_payloads += 1;
        const record = compactRecord(file, recordIndex, block, payload, sourceMeta);
        totals[`${record.classification}s`] = totals[`${record.classification}s`] || 0;
        appendJsonl(registryHandle, record);
        if (record.classification === 'object_field_patch' || record.classification === 'semantic_overlay') {
          const uniqueKey = record.classification === 'semantic_overlay'
            ? `overlay:${record.semantic_key || record.payload_sha256}`
            : `patch:${record.payload_sha256}`;
          if (!preciseSeen.has(uniqueKey)) {
            preciseSeen.add(uniqueKey);
            appendJsonl(preciseHandle, record);
            totals.unique_precise_entries += 1;
          } else {
            totals.duplicate_precise_instances += 1;
          }
        }
        if (record.automatic_writeback_status !== 'requires_current_value_verification') {
          appendJsonl(blockedHandle, record);
          totals.blocked_or_incomplete += 1;
        } else {
          totals.auto_writeback_candidates += 1;
        }
        if (record.classification === 'object_field_patch') totals.object_field_patches += 1;
        else if (record.classification === 'semantic_overlay') totals.semantic_overlays += 1;
        else if (record.classification === 'object_mapping_only') totals.object_mapping_only += 1;
        else if (record.classification === 'binding_or_runtime_audit') totals.binding_or_runtime_audit += 1;
        else totals.runtime_or_audit_record += 1;
      }
    }
    totals.main_files += 1;
    totals.runtime_blocks += blocks.length;
    catalog.push(fileCatalog);
  }
} finally {
  fs.closeSync(registryHandle);
  fs.closeSync(preciseHandle);
  fs.closeSync(blockedHandle);
}

const plan = {
  schema_version: 'runtime-upgrade-precision-plan-1.0',
  generated_at: new Date().toISOString(),
  source_batch: path.relative(PROJECT_ROOT, batchRoot).replaceAll('\\', '/'),
  source_backup: path.relative(PROJECT_ROOT, backupRoot).replaceAll('\\', '/'),
  source_immutable: true,
  main_material_catalog: 'main-material-catalog.json',
  runtime_layer_register: 'runtime-layer-register.jsonl',
  precise_upgrade_map: 'precise-upgrade-map.jsonl',
  blocked_or_incomplete: 'blocked-or-incomplete-upgrades.jsonl',
  totals,
  writeback_policy: {
    prerequisites: [
      'exact_object_locator',
      'baseline_object_sha256',
      'field_path',
      'before_value_matches_current_object',
      'after_value_present',
      'writeback_allowed=true',
      'status_is_not_pending_or_requires_review',
    ],
    current_result: 'no_record_may_be_automatically_written_back_without_a_new_approval_or_current_value_verification',
    reason: 'The absorbed backup preserves many runtime and audit records, but a record is not a material replacement unless it has an exact object, field-level before/after values, and explicit writeback authorization.',
  },
};

fs.writeFileSync(path.join(outputRoot, 'main-material-catalog.json'), `${JSON.stringify({
  schema_version: 'complete-absorbed-material-catalog-1.0',
  source_immutable: true,
  source_backup: plan.source_backup,
  files: catalog,
}, null, 2)}\n`, 'utf8');
fs.writeFileSync(path.join(outputRoot, 'writeback-plan.json'), `${JSON.stringify(plan, null, 2)}\n`, 'utf8');
fs.writeFileSync(path.join(outputRoot, 'README.md'), [
  '# Complete Material Runtime Upgrade Map',
  '',
  'This package is built from the selected largest absorbed-material backup.',
  'The six source files are not changed. Their main-material boundary is recorded',
  'in main-material-catalog.json; all appended runtime records are indexed separately.',
  '',
  'Use precise-upgrade-map.jsonl only for field-level records. A record can be',
  'written into a main material only after every prerequisite in writeback-plan.json',
  'passes against the current target object.',
  '',
].join('\n'), 'utf8');

console.log(JSON.stringify({ output: outputRoot, totals }, null, 2));
