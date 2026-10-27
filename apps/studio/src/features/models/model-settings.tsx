"use client";

import { Badge, Button, Input, Select, Table, TableBody, TableHead } from "@accos/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { StateResolver } from "../../components/state-resolver";
import { useIdentity } from "../../providers/identity-provider";
import {
  ModelNavigation,
  TextArea,
  objectJson,
  pretty,
  useAction,
  useModelOwner,
} from "./model-common";
import {
  money,
  pinKey,
  useModelApi,
  type ProfileInput,
  type Policy,
  type Budget,
} from "./model-api";

const blankProfile: ProfileInput = {
  id: "",
  version: 1,
  label: "",
  protocol: "ollama",
  endpoint: "http://127.0.0.1:11434",
  model: "",
  locality: "local",
  capabilities: ["text"],
  capability_version: "1",
  context_window: 8192,
  max_output_tokens: 2048,
  embedding_dimensions: null,
  allowed_parameters: [],
  defaults: {},
  enabled: true,
  chat_stream_usage: false,
  chat_token_parameter: "max_completion_tokens",
  max_response_bytes: 2000000,
  send_embedding_dimensions: false,
  timeout_seconds: 120,
  tokenizer: "utf8_upper_bound.v1",
  price: {
    version: "1",
    currency: "USD",
    input_per_million: null,
    output_per_million: null,
    cached_input_per_million: null,
  },
};
const blankPolicy: Policy = {
  id: "default",
  version: 1,
  label: "默认任务策略",
  route: [],
  allowed_tasks: ["agent.task"],
  max_attempts: 2,
  attempts_per_profile: 1,
  retry_delay_seconds: 1,
  task_token_limit: 100000,
  task_call_limit: 32,
  task_cost_limit_micro_usd: 1000000,
  cache_ttl_seconds: 0,
  enabled: true,
};
const capabilityLabels = {
  text: "文本",
  structured: "结构化输出",
  tools: "工具",
  stream: "流式",
  embedding: "向量",
} as const;

export function ModelSettings() {
  const identity = useIdentity();
  const owner = useModelOwner();
  const api = useModelApi(identity.workspace_id);
  const client = useQueryClient();
  const key = ["model-configuration", identity.actor_id, identity.workspace_id];
  const query = useQuery({
    queryKey: key,
    queryFn: async () => {
      const [profiles, policies, budget, capabilities, prompts, credentials] = await Promise.all([
        api.profiles(),
        api.policies(),
        api.budget(),
        api.capabilities(),
        api.prompts(),
        owner ? api.credentials() : Promise.resolve([]),
      ]);
      return { profiles, policies, budget, capabilities, prompts, credentials };
    },
  });
  const [profile, setProfile] = useState<ProfileInput>(blankProfile);
  const [profileBase, setProfileBase] = useState(0);
  const [parameters, setParameters] = useState("{}");
  const [policy, setPolicy] = useState<Policy>(blankPolicy);
  const [policyBase, setPolicyBase] = useState(0);
  const [budgetDraft, setBudgetDraft] = useState<Budget | null>(null);
  const action = useAction();
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError)
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  const { profiles, policies, budget, capabilities, prompts, credentials } = query.data;
  const capability = capabilities.find((item) => item.capability === "models.real");
  const budgetValue = budgetDraft ?? budget.settings;
  const refresh = () => client.invalidateQueries({ queryKey: key });
  const tasks = [...new Set(prompts.flatMap((item) => item.allowed_tasks))];
  return (
    <section className="studio-page studio-page--wide">
      <header className="studio-page__header">
        <p className="studio-eyebrow">模型设置</p>
        <h1>模型、路由与预算</h1>
        <p>为新任务选择明确版本。保存配置不会发送模型请求。</p>
      </header>
      <ModelNavigation />
      <section className="studio-panel">
        <h2>运行条件</h2>
        <p>
          <Badge tone={capability?.configuration === "configured" ? "info" : "warning"}>
            {capability?.configuration === "configured" ? "配置齐备" : "待配置"}
          </Badge>
          　实现：{capability?.implementation ?? "未知"} · 服务健康：{capability?.health ?? "未知"}{" "}
          · 验证：{capability?.verification ?? "未测试"}
        </p>
        {capability?.requirements.map((item) => (
          <p key={item.message}>{item.message}</p>
        ))}
        <p>
          真实调用需启用安装配置中的
          REAL_PROVIDER_CALLS；本地端点需在安装白名单中。云端内容还需工作区允许外发，任务选择“遵循工作区策略”。
        </p>
        <Link className="studio-link-button" href="/settings">
          管理密钥与工作区内容权限
        </Link>
      </section>
      {action.notice}
      <section className="studio-panel">
        <h2>每日预算（UTC）</h2>
        <p>
          已用 {money(budget.spent_micro_usd)} · 预留 {money(budget.reserved_micro_usd)} · 待对账{" "}
          {budget.unknown_count} 次 · 已尝试 {budget.calls} 次
        </p>
        <form
          className="studio-form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void action.run(async () => {
              await api.saveBudget(budgetValue);
              setBudgetDraft(null);
              await refresh();
            });
          }}
        >
          <fieldset disabled={!owner || action.busy} className="model-fieldset studio-form-grid">
            {(
              [
                ["daily_cost_limit_micro_usd", "每日费用上限（微美元）", 0],
                ["daily_call_limit", "每日调用上限", 0],
                ["concurrent_calls", "共享并发上限", 1],
                ["requests_per_minute", "每分钟请求上限", 1],
              ] as const
            ).map(([name, label, min]) => (
              <Input
                key={name}
                label={label}
                type="number"
                min={min}
                required
                value={budgetValue[name] ?? ""}
                onChange={(event) =>
                  setBudgetDraft({ ...budgetValue, [name]: Number(event.target.value) })
                }
              />
            ))}
            <Button type="submit">保存预算</Button>
          </fieldset>
        </form>
        <p>
          1 美元 = 1,000,000 微美元；Token
          日限额在工作区设置中维护。未知用量或价格会保留预算占用，需有凭据后对账。
        </p>
      </section>
      <section className="studio-panel">
        <h2>模型版本</h2>
        {profiles.length ? (
          <Table caption="已发布模型配置">
            <TableHead>
              <tr>
                <th>名称 / 版本</th>
                <th>协议 / 模型</th>
                <th>能力</th>
                <th>输入 / 输出价格（USD / 百万 Token）</th>
                <th>操作</th>
              </tr>
            </TableHead>
            <TableBody>
              {profiles.map((item) => (
                <tr key={pinKey(item)}>
                  <td>
                    {item.label} · {pinKey(item)}
                  </td>
                  <td>
                    {item.protocol} / {item.model}
                  </td>
                  <td>{item.capabilities.map((c) => capabilityLabels[c]).join("、")}</td>
                  <td>
                    {item.price.input_per_million ?? "未知"} /{" "}
                    {item.price.output_per_million ?? "未知"}
                  </td>
                  <td>
                    <Button
                      disabled={!owner}
                      variant="secondary"
                      onClick={() => {
                        const version = Math.max(
                          ...profiles.filter((p) => p.id === item.id).map((p) => p.version),
                        );
                        setProfileBase(version);
                        setProfile({ ...item, version: version + 1 });
                        setParameters(pretty(item.defaults));
                      }}
                    >
                      编辑为新版本
                    </Button>
                  </td>
                </tr>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p>还没有模型配置。填写实际端点与模型名后发布首个版本。</p>
        )}
        <Button
          variant="secondary"
          onClick={() => {
            setProfile(blankProfile);
            setProfileBase(0);
            setParameters("{}");
          }}
        >
          新建模型配置
        </Button>
        <form
          className="studio-form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void action.run(async () => {
              const result = await api.saveProfile(
                { ...profile, defaults: objectJson(parameters) },
                profileBase,
              );
              setProfileBase(result.version);
              setProfile({ ...result, version: result.version + 1 });
              await refresh();
            });
          }}
        >
          <fieldset disabled={!owner || action.busy} className="model-fieldset studio-form-stack">
            <div className="studio-form-grid">
              <Input
                label="配置 ID"
                required
                pattern="[a-zA-Z][a-zA-Z0-9_.-]{0,99}"
                readOnly={profileBase > 0}
                value={profile.id}
                onChange={(e) => setProfile({ ...profile, id: e.target.value })}
              />
              <Input
                label="显示名称"
                required
                value={profile.label}
                onChange={(e) => setProfile({ ...profile, label: e.target.value })}
              />
              <Select
                label="协议"
                value={profile.protocol}
                onChange={(e) =>
                  setProfile({ ...profile, protocol: e.target.value as ProfileInput["protocol"] })
                }
              >
                <option value="ollama">Ollama</option>
                <option value="openai_responses">OpenAI Responses</option>
                <option value="chat_completions">Chat Completions 兼容接口</option>
              </Select>
              <Select
                label="内容位置"
                value={profile.locality}
                onChange={(e) =>
                  setProfile({ ...profile, locality: e.target.value as ProfileInput["locality"] })
                }
              >
                <option value="local">本地白名单端点</option>
                <option value="cloud">云端（HTTPS）</option>
              </Select>
              <Input
                label="API 基础地址"
                required
                type="url"
                description="OpenAI 使用含 /v1 的基础地址；Ollama 使用服务根地址。"
                value={profile.endpoint}
                onChange={(e) => setProfile({ ...profile, endpoint: e.target.value })}
              />
              <Input
                label="实际模型名"
                required
                value={profile.model}
                onChange={(e) => setProfile({ ...profile, model: e.target.value })}
              />
              <Select
                label="密钥引用"
                value={profile.secret_ref ?? ""}
                onChange={(e) => setProfile({ ...profile, secret_ref: e.target.value || null })}
              >
                <option value="">不使用密钥（仅限本地）</option>
                {credentials
                  .filter((item) => item.active)
                  .map((item) => (
                    <option key={item.secret_ref} value={item.secret_ref}>
                      {item.name} · {item.secret_ref}
                    </option>
                  ))}
              </Select>
              <Input
                label="能力版本"
                required
                value={profile.capability_version}
                onChange={(e) => setProfile({ ...profile, capability_version: e.target.value })}
              />
              <Input
                label="上下文上限"
                type="number"
                min={256}
                max={4000000}
                required
                value={profile.context_window}
                onChange={(e) => setProfile({ ...profile, context_window: Number(e.target.value) })}
              />
              <Input
                label="输出 Token 上限"
                type="number"
                min={1}
                max={1000000}
                required
                value={profile.max_output_tokens}
                onChange={(e) =>
                  setProfile({ ...profile, max_output_tokens: Number(e.target.value) })
                }
              />
              <Input
                label="向量维度（向量模型必填）"
                type="number"
                min={1}
                max={65536}
                value={profile.embedding_dimensions ?? ""}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    embedding_dimensions: e.target.value ? Number(e.target.value) : null,
                  })
                }
              />
              <Input
                label="请求超时（秒）"
                type="number"
                min={1}
                max={600}
                required
                value={profile.timeout_seconds ?? 120}
                onChange={(e) =>
                  setProfile({ ...profile, timeout_seconds: Number(e.target.value) })
                }
              />
            </div>
            <div className="model-options">
              {(Object.keys(capabilityLabels) as (keyof typeof capabilityLabels)[]).map((value) => (
                <label key={value}>
                  <input
                    type="checkbox"
                    checked={profile.capabilities.includes(value)}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        capabilities: e.target.checked
                          ? [...profile.capabilities, value]
                          : profile.capabilities.filter((c) => c !== value),
                      })
                    }
                  />
                  {capabilityLabels[value]}
                </label>
              ))}
            </div>
            <div className="studio-form-grid">
              <Input
                label="价格版本"
                required
                value={profile.price.version}
                onChange={(e) =>
                  setProfile({ ...profile, price: { ...profile.price, version: e.target.value } })
                }
              />
              {(
                [
                  ["input_per_million", "输入单价"],
                  ["output_per_million", "输出单价"],
                  ["cached_input_per_million", "缓存输入单价"],
                ] as const
              ).map(([name, label]) => (
                <Input
                  key={name}
                  label={label + "（USD / 百万 Token；空为未知）"}
                  min={0}
                  step="0.00000001"
                  type="number"
                  value={profile.price[name] ?? ""}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      price: { ...profile.price, [name]: e.target.value || null },
                    })
                  }
                />
              ))}
            </div>
            <details>
              <summary>参数与协议选项</summary>
              <div className="model-options">
                {(["temperature", "top_p", "seed", "reasoning_effort"] as const).map((name) => (
                  <label key={name}>
                    <input
                      type="checkbox"
                      checked={profile.allowed_parameters?.includes(name) ?? false}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          allowed_parameters: e.target.checked
                            ? [...(profile.allowed_parameters ?? []), name]
                            : profile.allowed_parameters?.filter((p) => p !== name),
                        })
                      }
                    />
                    {name}
                  </label>
                ))}
              </div>
              <TextArea
                label="默认参数 JSON（必须在允许列表中）"
                rows={5}
                value={parameters}
                onChange={(e) => setParameters(e.target.value)}
              />
              <Select
                label="Chat 输出上限字段"
                value={profile.chat_token_parameter ?? "max_completion_tokens"}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    chat_token_parameter: e.target.value as ProfileInput["chat_token_parameter"],
                  })
                }
              >
                <option value="max_completion_tokens">max_completion_tokens</option>
                <option value="max_tokens">max_tokens</option>
              </Select>
              <label>
                <input
                  type="checkbox"
                  checked={profile.chat_stream_usage ?? false}
                  onChange={(e) => setProfile({ ...profile, chat_stream_usage: e.target.checked })}
                />
                Chat 流式接口支持用量返回
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={profile.send_embedding_dimensions ?? false}
                  onChange={(e) =>
                    setProfile({ ...profile, send_embedding_dimensions: e.target.checked })
                  }
                />
                向量接口支持 dimensions 参数
              </label>
            </details>
            <Button type="submit">发布模型版本 {profile.version}</Button>
          </fieldset>
        </form>
      </section>
      <section className="studio-panel">
        <h2>路由策略</h2>
        <p>
          按列表顺序尝试，固定引用模型版本。只有明确未计费且可重试的失败才继续；本地限定任务不会转发到云端。
        </p>
        <Select
          label="从已发布策略创建新版"
          value=""
          onChange={(e) => {
            const item = policies.find((p) => pinKey(p) === e.target.value);
            if (item) {
              const version = Math.max(
                ...policies.filter((p) => p.id === item.id).map((p) => p.version),
              );
              setPolicyBase(version);
              setPolicy({ ...item, version: version + 1 });
            }
          }}
        >
          <option value="">选择策略</option>
          {policies.map((item) => (
            <option key={pinKey(item)} value={pinKey(item)}>
              {item.label} · {pinKey(item)}
            </option>
          ))}
        </Select>
        <Button
          variant="secondary"
          onClick={() => {
            setPolicy({ ...blankPolicy, id: "" });
            setPolicyBase(0);
          }}
        >
          新建策略
        </Button>
        <form
          className="studio-form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void action.run(async () => {
              const result = await api.savePolicy(policy, policyBase);
              setPolicyBase(result.version ?? 1);
              setPolicy({ ...result, version: (result.version ?? 1) + 1 });
              await refresh();
            });
          }}
        >
          <fieldset className="model-fieldset studio-form-stack" disabled={!owner || action.busy}>
            <div className="studio-form-grid">
              <Input
                label="策略 ID"
                required
                readOnly={policyBase > 0}
                value={policy.id}
                onChange={(e) => setPolicy({ ...policy, id: e.target.value })}
              />
              <Input
                label="策略名称"
                required
                value={policy.label}
                onChange={(e) => setPolicy({ ...policy, label: e.target.value })}
              />
            </div>
            <ol>
              {policy.route.map((pin, index) => (
                <li key={pinKey(pin)}>
                  {pinKey(pin)}{" "}
                  <Button
                    variant="secondary"
                    onClick={() =>
                      setPolicy({ ...policy, route: policy.route.filter((_, i) => i !== index) })
                    }
                  >
                    移除
                  </Button>
                </li>
              ))}
            </ol>
            <Select
              label="按顺序追加模型版本"
              value=""
              onChange={(e) => {
                const item = profiles.find((p) => pinKey(p) === e.target.value);
                if (item && !policy.route.some((p) => pinKey(p) === pinKey(item)))
                  setPolicy({
                    ...policy,
                    route: [...policy.route, { id: item.id, version: item.version }],
                  });
              }}
            >
              <option value="">选择模型</option>
              {profiles
                .filter((p) => p.enabled)
                .map((item) => (
                  <option key={pinKey(item)} value={pinKey(item)}>
                    {item.label} · {pinKey(item)}
                  </option>
                ))}
            </Select>
            <div className="model-options">
              {tasks.map((task) => (
                <label key={task}>
                  <input
                    type="checkbox"
                    checked={policy.allowed_tasks.includes(task)}
                    onChange={(e) =>
                      setPolicy({
                        ...policy,
                        allowed_tasks: e.target.checked
                          ? [...policy.allowed_tasks, task]
                          : policy.allowed_tasks.filter((t) => t !== task),
                      })
                    }
                  />
                  {task}
                </label>
              ))}
            </div>
            <div className="studio-form-grid">
              {(
                [
                  ["max_attempts", "总尝试上限", 1, 8],
                  ["attempts_per_profile", "每模型尝试上限", 1, 3],
                  ["task_call_limit", "单任务调用上限", 1, 1000],
                  ["task_token_limit", "单任务 Token 上限", 1, 100000000],
                  ["task_cost_limit_micro_usd", "单任务费用上限（微美元）", 0, 1000000000000],
                  ["cache_ttl_seconds", "相同输入缓存秒数（0 关闭）", 0, 86400],
                ] as const
              ).map(([name, label, min, max]) => (
                <Input
                  key={name}
                  label={label}
                  type="number"
                  min={min}
                  max={max}
                  required
                  value={policy[name]}
                  onChange={(e) => setPolicy({ ...policy, [name]: Number(e.target.value) })}
                />
              ))}
              <Input
                label="价格未知时每次预留（微美元；空为拒绝调用）"
                type="number"
                min={1}
                value={policy.unknown_price_hold_micro_usd ?? ""}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    unknown_price_hold_micro_usd: e.target.value ? Number(e.target.value) : null,
                  })
                }
              />
            </div>
            <Button
              type="submit"
              disabled={policy.route.length === 0 || policy.allowed_tasks.length === 0}
            >
              发布策略版本 {policy.version}
            </Button>
          </fieldset>
        </form>
      </section>
      {!owner ? <p>当前身份可查看配置；发布和预算修改需要真人工作区管理员。</p> : null}
    </section>
  );
}
