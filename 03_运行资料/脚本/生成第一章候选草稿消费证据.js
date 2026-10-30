"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const root = process.argv[2];
if (!root) throw new Error("用法: node 生成第一章候选草稿消费证据.js <project-root>");
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
const batch = readJson(path.join(root, "文档", "证据", "第一章受控草稿批次.json"));
const proseRelative = "文档/候选草稿/BATCH-0001/CH-01-第七息-候选草稿.md";
const prose = fs.readFileSync(path.join(root, proseRelative), "utf8").replace(/^\uFEFF/, "").split(/\r?\n/);
const sourceIds = new Map(fs.readFileSync(path.join(root, "文档", "证据", "全量资料输入与正文授权", "已审计授权清单.jsonl"), "utf8").split(/\r?\n/).filter(Boolean).map(JSON.parse).map((row) => [row.binding_id, row.source_id]));
const lineForScene = new Map([["CH-01-S1", 5], ["CH-01-S2", 7], ["CH-01-S3", 9], ["CH-01-S4", 11]]);
const records = batch.records.flatMap((task) => {
  const line = lineForScene.get(task.scene_id);
  const paragraph = prose[line - 1];
  if (!paragraph || paragraph.length < 80) throw new Error(`场景正文缺失或过短: ${task.scene_id}`);
  return task.allowed_binding_ids.map((bindingId) => ({
    consumption_id: `${task.task_id}-${bindingId}`,
    batch_id: batch.batch_id,
    chapter_id: task.chapter_id,
    scene_id: task.scene_id,
    binding_id: bindingId,
    source_id: sourceIds.get(bindingId),
    prose_location: `${proseRelative}#lines[${line}]`,
    paragraph_sha256: crypto.createHash("sha256").update(paragraph, "utf8").digest("hex"),
    paragraph,
    trigger: task.scene_contract.conflict,
    action: task.scene_contract.action_and_choice,
    observable_result: task.scene_contract.information_gain,
    cost_or_change: task.scene_contract.consequence,
    semantic_support: `该绑定仅在 ${task.scene_id} 的场景契约内转译为可观察行动、限制或后果；待人工逐条核验。`,
    quality_status: "automatic_draft_requires_semantic_editorial_review",
    literary_review_status: "automatic_draft_requires_semantic_editorial_review",
    traceability_status: "hash_and_location_generated_pending_human_review",
    publication_status: "formal_release_prohibited"
  }));
});
const result = {
  schema_version: "controlled-scene-draft-consumption-evidence-1.0",
  project_id: batch.project_id,
  batch_id: batch.batch_id,
  generated_at: new Date().toISOString(),
  status: "automatic_draft_requires_semantic_editorial_review",
  publication_status: "formal_release_prohibited",
  record_count: records.length,
  records
};
const output = path.join(root, "文档", "候选草稿", "BATCH-0001", "消费证据待审.json");
fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ status: result.status, record_count: result.record_count, output }, null, 2));