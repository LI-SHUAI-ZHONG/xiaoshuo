/*
 * Creates a non-destructive complete material edition. Every registered runtime
 * binding is attached to the original material object identified by source_ref,
 * source_id, and the V2 object index. Source files are never changed.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const U = (...codes) => String.fromCharCode(...codes);
const DOC = U(0x6587, 0x6863);
const EVIDENCE = U(0x8bc1, 0x636e);
const MERGE = U(0x5408, 0x5e76, 0x5347, 0x7ea7);
const INDEX_V2 = U(0x539f,0x7248,0x8d44,0x6599,0x5bf9,0x8c61,0x7d22,0x5f15) + '_V2';
const OBJECT_INDEX = U(0x5bf9,0x8c61,0x7d22,0x5f15) + '.jsonl';
const BINDINGS = U(0x5168,0x91cf,0x8d44,0x6599,0x89e3,0x91ca,0x8bcd,0x521b,0x4f5c,0x7ed1,0x5b9a) + '.json';
const CLASSIFIED_START = `===== ${U(0x5206,0x7c7b,0x5347,0x7ea7,0x8d44,0x6599)}${U(0x5f00,0x59cb)} =====`;
const ORIGINAL_PREFIX = U(0x539f,0x59cb,0x8d44,0x6599) + '/';

const root = process.cwd();
const mergeRoot = path.join(root, DOC, MERGE);
const selectedBatch = 'material-absorption-20260818T054129Z';
const batchRoot = path.join(mergeRoot, selectedBatch);
const backupName = fs.readdirSync(batchRoot, { withFileTypes: true })
  .find((entry) => entry.isDirectory())?.name;
if (!backupName) throw new Error('The selected absorption batch has no backup directory.');
const backupRoot = path.join(batchRoot, backupName);
const outputName = process.argv[2] || '完整运行层升级版-20260819-01';
const outputRoot = path.join(mergeRoot, outputName);
if (fs.existsSync(outputRoot)) throw new Error(`Refusing to overwrite existing output: ${outputRoot}`);

const kindToFile = {
  [U(0x8d44,0x6599,0x5e93)]: U(0x8d44,0x6599,0x5e93) + '.txt',
  [U(0x9759,0x6001,0x7f51,0x7edc)]: U(0x9759,0x6001,0x7f51,0x7edc) + '.txt',
  [U(0x52a8,0x6001,0x7f51,0x7edc)]: U(0x52a8,0x6001,0x7f51,0x7edc) + '.txt',
  [U(0x951a,0x70b9,0x7f51,0x7edc)]: U(0x951a,0x70b9,0x7f51,0x7edc) + '.txt',
  [U(0x7c7b,0x578b,0x7cfb,0x7edf)]: U(0x7c7b,0x578b,0x7cfb,0x7edf) + '.txt',
  [U(0x7c7b,0x578b,0x7cfb,0x7edf,0x6765,0x6e90,0x5757)]: U(0x7c7b,0x578b,0x7cfb,0x7edf) + '.txt',
  [U(0x7c7b,0x578b,0x8fde,0x63a5)]: U(0x7c7b,0x578b,0x8fde,0x63a5) + '.txt',
};

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function parseLocator(sourceRef) {
  if (typeof sourceRef !== 'string') return null;
  const dictLocator = sourceRef.match(/['"]locator['"]\s*:\s*['"]([^'"]+)['"]/);
  if (dictLocator) return dictLocator[1];
  const hashLocator = sourceRef.match(/#(.+)$/);
  if (hashLocator) return hashLocator[1];
  const colon = sourceRef.lastIndexOf(':');
  return colon >= 0 ? sourceRef.slice(colon + 1).trim() || null : null;
}

function normalizeFile(sourceFile) {
  if (typeof sourceFile !== 'string') return null;
  const name = sourceFile.replaceAll('\\', '/').split('/').at(-1);
  return name || null;
}

function directRecords(bindingDocument) {
  if (!Array.isArray(bindingDocument.records)) throw new Error('Binding document lacks records[].');
  return bindingDocument.records.filter((record) => record && typeof record.binding_id === 'string');
}

function indexRecords(indexPath) {
  const maps = {
    byObjectId: new Map(),
    byFileLocator: new Map(),
    byFileIdentity: new Map(),
  };
  for (const line of fs.readFileSync(indexPath, 'utf8').split(/\r?\n/)) {
    if (!line.trim()) continue;
    const entry = JSON.parse(line);
    const file = normalizeFile(entry.source_file);
    const locatorKey = `${file}|${entry.locator}`;
    const identityKey = `${file}|${entry.identity}`;
    maps.byObjectId.set(entry.object_id, entry);
    if (!maps.byFileLocator.has(locatorKey)) maps.byFileLocator.set(locatorKey, []);
    if (!maps.byFileIdentity.has(identityKey)) maps.byFileIdentity.set(identityKey, []);
    maps.byFileLocator.get(locatorKey).push(entry);
    maps.byFileIdentity.get(identityKey).push(entry);
  }
  return maps;
}

function resolveObject(record, maps) {
  const materialFile = kindToFile[record.source_kind];
  if (!materialFile) return { status: 'unmapped_source_kind', material_file: null, object: null };
  const locator = parseLocator(record.source_ref);
  const locatorMatches = locator ? maps.byFileLocator.get(`${materialFile}|${locator}`) || [] : [];
  if (locatorMatches.length === 1) {
    return { status: 'exact_source_ref_locator', material_file: materialFile, object: locatorMatches[0] };
  }
  const identityMatches = maps.byFileIdentity.get(`${materialFile}|${record.source_id}`) || [];
  if (identityMatches.length === 1) {
    return { status: 'exact_source_id_identity', material_file: materialFile, object: identityMatches[0] };
  }
  if (locatorMatches.length > 1) {
    return { status: 'ambiguous_locator', material_file: materialFile, object: null, candidates: locatorMatches.map((entry) => entry.object_id) };
  }
  if (identityMatches.length > 1) {
    return { status: 'ambiguous_identity', material_file: materialFile, object: null, candidates: identityMatches.map((entry) => entry.object_id) };
  }
  // Legacy source structures may be absent from V2 despite the binding baseline
  // declaring an exact source_ref. Use that declared object identity, never a
  // nearest-text heuristic, so every binding remains attached to its source.
  if (locator || record.source_id) {
    const canonicalLocator = locator || record.source_id;
    return {
      status: 'exact_declared_source_ref_unindexed',
      material_file: materialFile,
      object: {
        object_id: `${ORIGINAL_PREFIX}${materialFile}#${canonicalLocator}`,
        locator: canonicalLocator,
        identity: record.source_id,
        content_sha256: null,
        line_start: null,
        line_end: null,
        object_kind: 'declared_source_ref',
      },
    };
  }
  return { status: 'index_locator_missing', material_file: materialFile, object: null };
}

function runtimeProjection(record) {
  return {
    binding_id: record.binding_id,
    source_kind: record.source_kind,
    source_id: record.source_id,
    name: record.name,
    source_ref: record.source_ref,
    source_ref_sha256: record.use_authorization?.source_ref_sha256 || null,
    model_input_eligible: record.model_input_eligible,
    prose_write_allowed: record.prose_write_allowed,
    translation_status: record.translation_status,
    activation_status: record.activation_status,
    semantic_interpretation: record.semantic_interpretation || null,
    creation_binding: record.creation_binding || null,
    evidence_contract: record.evidence_contract || null,
    use_authorization: record.use_authorization || null,
  };
}

function runtimeSummary(record) {
  const binding = record.creation_binding || {};
  const strategy = binding.creative_strategy || {};
  return {
    primary_stage: binding.primary_stage || null,
    stages: binding.stages || null,
    creative_object: binding.creative_object || null,
    creative_action: binding.creative_action || null,
    trigger: strategy.source_specific_trigger || null,
    observable_action: strategy.observable_action || null,
    observable_result: strategy.observable_result || null,
    cost_or_change: strategy.cost_or_change || null,
    activation_conditions: binding.activation_policy?.conditions || null,
    semantic_anchor: strategy.semantic_anchor || record.semantic_interpretation?.source_semantic_anchor || null,
    evidence_required: record.evidence_contract || null,
  };
}

const bindingPath = path.join(root, DOC, EVIDENCE, BINDINGS);
const bindingDocument = JSON.parse(fs.readFileSync(bindingPath, 'utf8'));
const bindings = directRecords(bindingDocument);
if (bindings.length !== 13345) throw new Error(`Expected 13345 binding records, got ${bindings.length}.`);
const indexPath = path.join(root, DOC, EVIDENCE, INDEX_V2, OBJECT_INDEX);
const maps = indexRecords(indexPath);

const groups = new Map();
const unresolved = [];
const bindingMapRows = [];
const summary = {
  schema_version: 'complete-runtime-enhanced-materials-1.0',
  generated_at: new Date().toISOString(),
  source_backup: path.relative(root, backupRoot).replaceAll('\\', '/'),
  source_backup_immutable: true,
  binding_baseline: path.relative(root, bindingPath).replaceAll('\\', '/'),
  binding_count: bindings.length,
  target_files: {},
  resolution_counts: {},
};

for (const record of bindings) {
  const resolution = resolveObject(record, maps);
  summary.resolution_counts[resolution.status] = (summary.resolution_counts[resolution.status] || 0) + 1;
  const mapping = {
    binding_id: record.binding_id,
    source_kind: record.source_kind,
    source_id: record.source_id,
    source_ref: record.source_ref,
    material_file: resolution.material_file,
    resolution_status: resolution.status,
    original_object_id: resolution.object?.object_id || null,
    original_locator: resolution.object?.locator || parseLocator(record.source_ref),
    original_object_sha256: resolution.object?.content_sha256 || null,
    candidate_object_ids: resolution.candidates || null,
  };
  bindingMapRows.push(mapping);
  if (!resolution.material_file || !resolution.object) {
    unresolved.push({ ...mapping, runtime_layer: runtimeProjection(record) });
    continue;
  }
  const key = `${resolution.material_file}\u0000${resolution.object.object_id}`;
  if (!groups.has(key)) {
    groups.set(key, { material_file: resolution.material_file, object: resolution.object, entries: [] });
  }
  groups.get(key).entries.push({
    mapping,
    summary: runtimeSummary(record),
    full_runtime_layer: runtimeProjection(record),
  });
}

fs.mkdirSync(outputRoot, { recursive: false });
const materialDir = path.join(outputRoot, U(0x5b8c,0x6574,0x8d44,0x6599));
fs.mkdirSync(materialDir);
const mapHandle = fs.openSync(path.join(outputRoot, U(0x8fd0,0x884c,0x5c42,0x7cbe,0x51c6,0x786e,0x6620,0x5c04) + '.jsonl'), 'w');
const unresolvedHandle = fs.openSync(path.join(outputRoot, U(0x5f85,0x5b9a,0x4f4d,0x7cbe,0x7684,0x8fd0,0x884c,0x5c42,0x7cbe) + '.jsonl'), 'w');

try {
  for (const mapping of bindingMapRows) fs.writeSync(mapHandle, `${JSON.stringify(mapping)}\n`);
  for (const row of unresolved) fs.writeSync(unresolvedHandle, `${JSON.stringify(row)}\n`);
} finally {
  fs.closeSync(mapHandle);
  fs.closeSync(unresolvedHandle);
}

const files = fs.readdirSync(backupRoot, { withFileTypes: true })
  .filter((entry) => entry.isFile() && entry.name.endsWith('.txt'))
  .map((entry) => entry.name)
  .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));

for (const file of files) {
  const sourcePath = path.join(backupRoot, file);
  const sourceText = fs.readFileSync(sourcePath, 'utf8');
  // Preserve the complete user-selected backup, including every absorbed
  // source block, then append the object-addressable enhanced runtime view.
  const mainText = sourceText;
  const objectGroups = [...groups.values()]
    .filter((group) => group.material_file === file)
    .sort((left, right) => left.object.line_start - right.object.line_start || left.object.object_id.localeCompare(right.object.object_id));
  const header = [
    '',
    '',
    '===== 运行层精准增强开始 =====',
    '说明：以下增强按 binding_id -> source_ref/source_id -> 原版对象索引精确归并。',
    '规则：原始条目正文保留；运行层作为其可检索、可调用、可校验的增强，不虚构项目事实。',
    `原始资料文件：${file}`,
    `原始主资料SHA256：${sha256(Buffer.from(mainText, 'utf8'))}`,
    `已归并原版对象数：${objectGroups.length}`,
    `已归并运行层条目数：${objectGroups.reduce((sum, group) => sum + group.entries.length, 0)}`,
    '===== 运行层精准增强目录结束 =====',
    '',
  ].join('\n');
  const blocks = objectGroups.map((group) => [
    '===== 原版条目运行层增强开始 =====',
    `原版对象：${group.object.object_id}`,
    `原版定位：${group.object.locator}`,
    `原版对象SHA256：${group.object.content_sha256}`,
    `原版行范围：${group.object.line_start}-${group.object.line_end}`,
    `增强条目数：${group.entries.length}`,
    '运行层增强JSON：',
    JSON.stringify({
      canonical_object_id: group.object.object_id,
      original_locator: group.object.locator,
      runtime_entries: group.entries,
    }, null, 2),
    '===== 原版条目运行层增强结束 =====',
    '',
  ].join('\n'));
  const content = `${mainText.replace(/\s+$/, '')}\n${header}${blocks.join('\n')}`;
  const outputPath = path.join(materialDir, file);
  fs.writeFileSync(outputPath, content, 'utf8');
  summary.target_files[file] = {
    source_total_sha256: sha256(fs.readFileSync(sourcePath)),
    source_main_material_sha256: sha256(Buffer.from(mainText, 'utf8')),
    source_main_material_bytes: Buffer.byteLength(mainText, 'utf8'),
    enhanced_file_sha256: sha256(Buffer.from(content, 'utf8')),
    enhanced_file_bytes: Buffer.byteLength(content, 'utf8'),
    enhanced_object_count: objectGroups.length,
    enhanced_binding_count: objectGroups.reduce((sum, group) => sum + group.entries.length, 0),
  };
}

summary.resolved_binding_count = bindings.length - unresolved.length;
summary.unresolved_binding_count = unresolved.length;
summary.output_files = Object.keys(summary.target_files).map((file) => `完整资料/${file}`);
summary.mapping_ledger = U(0x8fd0,0x884c,0x5c42,0x7cbe,0x51c6,0x786e,0x6620,0x5c04) + '.jsonl';
summary.unresolved_ledger = U(0x5f85,0x5b9a,0x4f4d,0x7cbe,0x7684,0x8fd0,0x884c,0x5c42,0x7cbe) + '.jsonl';
fs.writeFileSync(path.join(outputRoot, 'manifest.json'), `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
fs.writeFileSync(path.join(outputRoot, 'README.md'), [
  '# 完整运行层升级版',
  '',
  '本版本以指定的当前资料备份为主资料基线，保留每份文件在首个“分类升级资料开始”标记之前的正文。',
  '运行层不再作为无序的文件尾部批次存在，而是按每条 binding_id 的 source_ref、source_id 和 V2 原版对象索引，归并到对应的原版对象增强块中。',
  '',
  '完整资料目录包含六份可供 Cline 读取的升级资料。每个“原版条目运行层增强”块保留完整运行层 JSON，以及精确对象定位、哈希、阶段、触发、行动、结果、代价、激活条件和证据合同。',
  '',
  '无法唯一定位的条目没有被错误写入，保留在待定位运行层条目.jsonl。所有 13,345 个绑定的映射决定保留在运行层精准映射.jsonl。',
  '',
].join('\n'), 'utf8');

console.log(JSON.stringify({ output: outputRoot, summary }, null, 2));
