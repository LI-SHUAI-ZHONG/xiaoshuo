"use strict";

const fs = require("fs");
const path = require("path");

const root = process.argv[2];
if (!root) throw new Error("用法: node 编排第一章受控草稿批次.js <project-root>");
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
const readJsonl = (file) => fs.existsSync(file)
  ? fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean).map(JSON.parse)
  : [];
const writeJson = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");

const config = readJson(path.join(root, "配置", "project_config.json"));
const sourceConfirmation = readJson(path.join(root, "配置", "project_source_confirmation.json"));
const designDir = path.join(root, "文档", "创作设计");
const cards = readJson(path.join(designDir, "第一章场景卡.json"));
const materialPlan = readJson(path.join(designDir, "第一章最小资料包与授权申请.json"));
const authorized = readJsonl(path.join(root, "文档", "证据", "全量资料输入与正文授权", "已审计授权清单.jsonl"));

if (config.type_selection_policy.formal_release_allowed !== false || sourceConfirmation.formal_fact_approval !== false) {
  throw new Error("正式发布门状态异常；受控草稿编排必须在正式发布关闭时执行");
}
if (cards.artifact_status !== "author_confirmed_editorial_approved_for_authorization_preparation") {
  throw new Error("第一章场景卡未处于可授权编排状态");
}
const granted = new Map(authorized.filter((row) => row.model_input_eligible === true && row.prose_write_allowed === true).map((row) => [row.binding_id, row]));
const packages = new Map(materialPlan.scene_packages.map((row) => [row.scene_id, row]));
const records = cards.scenes.map((scene, index) => {
  const pack = packages.get(scene.scene_id);
  if (!pack) throw new Error(`场景缺少资料包: ${scene.scene_id}`);
  const bindingIds = [...pack.direct_creation_bindings, ...pack.indirect_constraint_bindings, ...pack.candidate_retrieval_bindings];
  const missing = bindingIds.filter((id) => !granted.has(id));
  if (missing.length) throw new Error(`场景 ${scene.scene_id} 存在未经审计授权的绑定: ${missing.join(", ")}`);
  const scopeViolations = bindingIds.filter((id) => {
    const scope = granted.get(id).authorization_scope;
    return typeof scope !== "string" || !scope.includes("draft_only") || !scope.includes("no_formal_publication") || !scope.includes(`scenes=${scene.scene_id}`) && !scope.includes(`,${scene.scene_id}`);
  });
  if (scopeViolations.length) throw new Error(`场景 ${scene.scene_id} 存在不覆盖本场的授权范围: ${scopeViolations.join(", ")}`);
  return {
    task_id: `BATCH-0001-T${String(index + 1).padStart(2, "0")}`,
    batch_id: "BATCH-0001",
    chapter_id: cards.chapter_id,
    scene_id: scene.scene_id,
    task_status: "automatic_draft_requires_semantic_editorial_review",
    allowed_binding_ids: bindingIds,
    allowed_authorization_scopes: bindingIds.map((id) => ({ binding_id: id, authorization_scope: granted.get(id).authorization_scope })),
    scene_contract: {
      viewpoint: scene.viewpoint,
      setting: scene.setting,
      goal: scene.goal,
      conflict: scene.conflict,
      action_and_choice: scene.action_and_choice,
      information_gain: scene.information_gain,
      consequence: scene.consequence,
      causality_to_next: scene.causality_to_next,
      must_not_do: scene.must_not_do
    },
    output_policy: {
      allowed_output: "candidate_draft_only",
      formal_publication_allowed: false,
      required_next_review: ["semantic_editorial_review", "literary_review", "traceability_review"],
      prohibited: ["使用未列 binding", "跨越第一章信息上限", "标记正式发布", "将候选草稿写入正式发布目录"]
    }
  };
});
const batch = {
  schema_version: "controlled-scene-draft-batch-1.0",
  project_id: config.project_id,
  generated_at: new Date().toISOString(),
  batch_id: "BATCH-0001",
  batch_status: "authorized_for_draft_not_generated",
  publication_status: "formal_release_prohibited",
  formal_fact_approval: false,
  chapter_information_ceiling: cards.chapter_information_ceiling,
  task_count: records.length,
  authorized_binding_count: new Set(records.flatMap((r) => r.allowed_binding_ids)).size,
  records
};
const output = path.join(root, "文档", "证据", "第一章受控草稿批次.json");
writeJson(output, batch);
console.log(JSON.stringify({ status: "passed", batch_id: batch.batch_id, task_count: batch.task_count, authorized_binding_count: batch.authorized_binding_count, publication_status: batch.publication_status }, null, 2));