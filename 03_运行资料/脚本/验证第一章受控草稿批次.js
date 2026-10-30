"use strict";

const fs = require("fs");
const path = require("path");

const root = process.argv[2];
if (!root) throw new Error("用法: node 验证第一章受控草稿批次.js <project-root>");
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
const readJsonl = (file) => fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean).map(JSON.parse);
const authorized = readJsonl(path.join(root, "文档", "证据", "全量资料输入与正文授权", "已审计授权清单.jsonl"));
const batch = readJson(path.join(root, "文档", "证据", "第一章受控草稿批次.json"));
const config = readJson(path.join(root, "配置", "project_config.json"));
const source = readJson(path.join(root, "配置", "project_source_confirmation.json"));
const bindingIds = new Set(authorized.map((row) => row.binding_id));
const violations = batch.records.flatMap((task) => task.allowed_binding_ids.filter((id) => !bindingIds.has(id)).map((id) => `${task.scene_id}:${id}`));
if (authorized.length !== 12 || batch.task_count !== 4 || batch.authorized_binding_count !== 12 || violations.length || batch.publication_status !== "formal_release_prohibited" || source.formal_fact_approval !== false || config.type_selection_policy.formal_release_allowed !== false) {
  throw new Error(JSON.stringify({ authorized_count: authorized.length, task_count: batch.task_count, batch_binding_count: batch.authorized_binding_count, violations, publication_status: batch.publication_status, formal_fact_approval: source.formal_fact_approval, formal_release_allowed: config.type_selection_policy.formal_release_allowed }));
}
console.log("VALIDATION PASSED: 12 audited bindings; 4 controlled draft-only tasks; formal publication remains prohibited.");