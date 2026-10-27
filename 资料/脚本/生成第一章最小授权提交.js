"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const root = process.argv[2];
if (!root) throw new Error("用法: node 生成第一章最小授权提交.js <project-root>");

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
const evidence = path.join(root, "文档", "证据");
const design = path.join(root, "文档", "创作设计");
const candidate = readJson(path.join(design, "第一章最小资料包与授权申请.json"));
const bindings = readJson(path.join(evidence, "全量资料解释词创作绑定.json"));
if (candidate.artifact_status !== "project_owner_confirmed_pending_machine_audit") {
  throw new Error("第一章资料包尚未获得项目作者确认");
}
const byId = new Map(bindings.records.map((row) => [row.binding_id, row]));
const now = new Date().toISOString();
const rows = candidate.per_binding_authorization_requests.map((request) => {
  const binding = byId.get(request.binding_id);
  if (!binding) throw new Error(`基线不存在绑定: ${request.binding_id}`);
  return {
    schema_version: "full-source-model-input-prose-authorization-1.0",
    binding_id: binding.binding_id,
    source_id: binding.source_id,
    source_ref_sha256: crypto.createHash("sha256").update(String(binding.source_ref || ""), "utf8").digest("hex"),
    model_input_eligible: true,
    prose_write_allowed: true,
    authorization_scope: `draft_only; chapter=CH-01; scenes=${request.proposed_scope.join(",")}; role=${request.requested_role}; no_formal_publication`,
    authorized_by: "project_owner_confirmation_2026-08-13",
    authorized_at: now,
    authorization_rationale: "项目作者已确认第一章创作设计；仅授权最小场景资料包用于隔离候选草稿。必须遵守场景卡信息上限、不得使用未列入资料包的绑定、不得用于正式发布。"
  };
});
const output = path.join(root, "配置", "全量资料输入与正文授权.jsonl");
fs.writeFileSync(output, rows.map((row) => JSON.stringify(row)).join("\n") + "\n", "utf8");
console.log(JSON.stringify({ status: "written", file: output, record_count: rows.length, binding_ids: rows.map((r) => r.binding_id) }, null, 2));