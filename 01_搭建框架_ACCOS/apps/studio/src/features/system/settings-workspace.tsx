"use client";

import type { components } from "@accos/api-client";
import { Badge, Button, Input, Select } from "@accos/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type SyntheticEvent } from "react";

import { StateResolver } from "../../components/state-resolver";
import { useApiClient } from "../../providers/api-provider";
import { useAuth } from "../../providers/auth-provider";
import { useIdentity } from "../../providers/identity-provider";
import { mapApiError } from "../../lib/api/errors";
import { ModelNavigation } from "../models/model-common";

type Settings = components["schemas"]["WorkspaceSettings"];
type Values = components["schemas"]["WorkspacePreferences"];
type Member = components["schemas"]["MemberView"];
type Grant = components["schemas"]["ScopeGrant"];
type Credential = components["schemas"]["CredentialView"];
function data<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (!result.response.ok || result.data === undefined)
    throw mapApiError(result.error, result.response);
  return result.data;
}
function successful(result: { error?: unknown; response: Response }) {
  if (!result.response.ok) throw mapApiError(result.error, result.response);
}

export function SettingsWorkspace() {
  const client = useApiClient();
  const identity = useIdentity();
  const { session, refresh } = useAuth();
  const queryClient = useQueryClient();
  const owner =
    identity.permissions.includes("membership:manage") &&
    ["local", "oidc"].includes(identity.auth_method);
  const key = ["identity-settings", identity.actor_id, identity.workspace_id];
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tokenOnce, setTokenOnce] = useState("");
  const [tokenName, setTokenName] = useState("");
  const [tokenDays, setTokenDays] = useState("30");
  const [tokenProject, setTokenProject] = useState("");
  const [tokenScopes, setTokenScopes] = useState<string[]>(["workspace:read", "project:read"]);
  const [memberSubject, setMemberSubject] = useState("");
  const [memberIssuer, setMemberIssuer] = useState("urn:accos:local");
  const [memberPassword, setMemberPassword] = useState("");
  const [memberRole, setMemberRole] = useState<Member["role"]>("EDITOR");
  const [credentialId, setCredentialId] = useState("");
  const [credentialName, setCredentialName] = useState("");
  const [secret, setSecret] = useState("");
  const [externalRef, setExternalRef] = useState("");
  const [grantUser, setGrantUser] = useState("");
  const [grantKind, setGrantKind] = useState<Grant["scope_kind"]>("project");
  const [grantScope, setGrantScope] = useState("");
  const [grantPermissions, setGrantPermissions] = useState("project:read");
  const [importText, setImportText] = useState("");
  const [exportText, setExportText] = useState("");
  const [passwordUser, setPasswordUser] = useState("");
  const [passwordOld, setPasswordOld] = useState("");
  const [passwordNew, setPasswordNew] = useState("");
  const query = useQuery({
    queryKey: key,
    queryFn: async () => {
      const [
        settings,
        capabilities,
        sessions,
        tokens,
        members,
        credentials,
        grants,
        approvals,
        creator,
      ] = await Promise.all([
        client
          .GET("/api/v1/settings/workspace", {
            params: { header: { "X-Workspace-ID": identity.workspace_id } },
          })
          .then(data),
        client
          .GET("/api/v1/capabilities", {
            params: { header: { "X-Workspace-ID": identity.workspace_id } },
          })
          .then(data),
        client
          .GET("/api/v1/auth/sessions", {
            params: { header: { "X-Workspace-ID": identity.workspace_id } },
          })
          .then(data),
        client
          .GET("/api/v1/identity/tokens", {
            params: { header: { "X-Workspace-ID": identity.workspace_id } },
          })
          .then(data),
        owner
          ? client
              .GET("/api/v1/identity/members", {
                params: { header: { "X-Workspace-ID": identity.workspace_id } },
              })
              .then(data)
          : Promise.resolve([] as Member[]),
        owner
          ? client
              .GET("/api/v1/settings/credentials", {
                params: { header: { "X-Workspace-ID": identity.workspace_id } },
              })
              .then(data)
          : Promise.resolve([] as Credential[]),
        owner
          ? client
              .GET("/api/v1/identity/grants", {
                params: { header: { "X-Workspace-ID": identity.workspace_id } },
              })
              .then(data)
          : Promise.resolve([] as Grant[]),
        owner
          ? client
              .GET("/api/v1/identity/control-requests", {
                params: { header: { "X-Workspace-ID": identity.workspace_id } },
              })
              .then(data)
          : Promise.resolve([] as components["schemas"]["ControlRequestView"][]),
        client
          .GET("/api/v1/identity/creator", {
            params: { header: { "X-Workspace-ID": identity.workspace_id } },
          })
          .then(data),
      ]);
      return {
        settings,
        capabilities,
        sessions,
        tokens,
        members,
        credentials,
        grants,
        approvals,
        creator,
      };
    },
  });
  const header = { "X-Workspace-ID": identity.workspace_id };
  const versionHeader = (version: number) => ({ ...header, "If-Match": '"' + version + '"' });
  async function act(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: key });
      setMessage("操作已保存。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "操作失败，请重试。");
    } finally {
      setBusy(false);
    }
  }
  async function memberChange(member: Member, role: Member["role"], active: boolean) {
    successful(
      await client.PUT("/api/v1/identity/members", {
        params: { header: versionHeader(member.version) },
        body: {
          issuer: member.issuer,
          subject: member.subject,
          role,
          active,
          expected_version: member.version,
        },
      }),
    );
  }
  async function revokeGrant(grant: Grant) {
    successful(
      await client.PUT("/api/v1/identity/grants", {
        params: { header: versionHeader(grant.version ?? 1) },
        body: { grant: { ...grant, active: !grant.active }, expected_version: grant.version ?? 1 },
      }),
    );
  }
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError)
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  const current = query.data;
  const selectedCredential = current.credentials.find((c) => c.id === credentialId);
  return (
    <section className="studio-page">
      <header className="studio-page__header">
        <p className="studio-eyebrow">Settings</p>
        <h1>账号与工作区设置</h1>
        <ModelNavigation />
        <p>管理登录、创作偏好、授权和服务凭据。运行验证状态单独展示。</p>
      </header>
      <div aria-live="polite">
        {message ? <p role="status">{message}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
      </div>
      <Preferences
        key={current.settings.version}
        initial={current.settings}
        editable={owner}
        busy={busy}
        save={(values) =>
          act(async () => {
            successful(
              await client.PUT("/api/v1/settings/workspace", {
                params: { header: versionHeader(current.settings.version) },
                body: { expected_version: current.settings.version, values },
              }),
            );
          })
        }
      />
      <section className="studio-panel">
        <h2>登录与会话</h2>
        <p>
          作者身份：<code>{current.creator.id}</code>
        </p>
        <p>修改密码后，所有现有浏览器会话都会失效。</p>
        <form
          className="studio-settings-grid"
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              successful(
                await client.POST("/api/v1/auth/password", {
                  params: { header },
                  body: {
                    username: passwordUser,
                    password: passwordOld,
                    new_password: passwordNew,
                  },
                }),
              );
              setPasswordOld("");
              setPasswordNew("");
              await refresh();
            });
          }}
        >
          <Input
            label="本地账号"
            value={passwordUser}
            onChange={(e) => setPasswordUser(e.target.value)}
            autoComplete="username"
            required
          />
          <Input
            label="当前密码"
            type="password"
            value={passwordOld}
            onChange={(e) => setPasswordOld(e.target.value)}
            autoComplete="current-password"
            required
          />
          <Input
            label="新密码"
            type="password"
            minLength={12}
            maxLength={256}
            value={passwordNew}
            onChange={(e) => setPasswordNew(e.target.value)}
            autoComplete="new-password"
            required
          />
          <Button busy={busy} type="submit">
            修改密码并退出
          </Button>
        </form>
        <ul className="studio-settings-list">
          {current.sessions.map((s) => (
            <li key={s.id}>
              <span>
                {s.method === "local" ? "本地登录" : "团队登录"} · 到期{" "}
                {new Date(s.expires_at).toLocaleString()}
                {s.id === session?.sessionId ? " · 当前会话" : ""}
              </span>
              <Button
                disabled={s.revoked || busy}
                variant="secondary"
                onClick={() =>
                  void act(async () => {
                    successful(
                      await client.DELETE("/api/v1/auth/sessions/{session_id}", {
                        params: { header, path: { session_id: s.id } },
                      }),
                    );
                    if (s.id === session?.sessionId) await refresh();
                  })
                }
              >
                {s.revoked ? "已撤销" : "撤销会话"}
              </Button>
            </li>
          ))}
        </ul>
      </section>
      <section className="studio-panel">
        <h2>开放 API 令牌</h2>
        <p>只授予所需权限，最长 90 天有效。令牌不能批准真人关卡。</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              const issued = data(
                await client.POST("/api/v1/identity/tokens", {
                  params: { header },
                  body: {
                    name: tokenName,
                    days: Number(tokenDays),
                    scopes: tokenScopes,
                    project_id: tokenProject || null,
                  },
                }),
              );
              setTokenOnce(issued.token);
              setTokenName("");
            });
          }}
        >
          <div className="studio-settings-grid">
            <Input
              label="令牌用途"
              value={tokenName}
              onChange={(e) => setTokenName(e.target.value)}
              maxLength={100}
              required
            />
            <Input
              label="有效天数"
              type="number"
              min={1}
              max={90}
              value={tokenDays}
              onChange={(e) => setTokenDays(e.target.value)}
              required
            />
            <Input
              label="限定项目 ID（可空）"
              value={tokenProject}
              onChange={(e) => setTokenProject(e.target.value)}
            />
          </div>
          <fieldset>
            <legend>令牌权限</legend>
            {[
              "workspace:read",
              "project:read",
              "project:write",
              "data:export",
              "agent:run",
              "model:run",
              "tool:run",
            ]
              .filter((p) => identity.permissions.includes(p))
              .map((p) => (
                <label className="studio-check-label" key={p}>
                  <input
                    type="checkbox"
                    checked={tokenScopes.includes(p)}
                    onChange={(e) =>
                      setTokenScopes((old) =>
                        e.target.checked ? [...old, p] : old.filter((v) => v !== p),
                      )
                    }
                  />
                  {p}
                </label>
              ))}
          </fieldset>
          <Button type="submit" busy={busy}>
            创建令牌
          </Button>
        </form>
        {tokenOnce ? (
          <div role="status">
            <p>仅本次显示，请现在保存；关闭后无法再次读取。</p>
            <textarea aria-label="新 API 令牌" readOnly value={tokenOnce} />
            <Button onClick={() => setTokenOnce("")} variant="secondary">
              已保存，关闭显示
            </Button>
          </div>
        ) : null}
        <ul className="studio-settings-list">
          {current.tokens.map((t) => (
            <li key={t.id}>
              <span>
                {t.name} · {t.scopes.join("、")} · {new Date(t.expires_at).toLocaleDateString()}
              </span>
              <Button
                disabled={t.revoked || busy}
                variant="secondary"
                onClick={() =>
                  void act(async () =>
                    successful(
                      await client.DELETE("/api/v1/identity/tokens/{token_id}", {
                        params: { header, path: { token_id: t.id } },
                      }),
                    ),
                  )
                }
              >
                {t.revoked ? "已撤销" : "撤销"}
              </Button>
            </li>
          ))}
        </ul>
      </section>
      {owner ? (
        <>
          <section className="studio-panel">
            <h2>服务凭据</h2>
            <p>保存后仅显示引用。轮换会使旧版本引用失效；使用该引用的模型配置需要改用新版本。</p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () => {
                  successful(
                    await client.PUT("/api/v1/settings/credentials", {
                      params: { header: versionHeader(selectedCredential?.version ?? 0) },
                      body: {
                        id: credentialId || crypto.randomUUID(),
                        name: credentialName,
                        expected_version: selectedCredential?.version ?? 0,
                        value: secret || null,
                        external_ref: externalRef || null,
                        active: true,
                      },
                    }),
                  );
                  setSecret("");
                  setExternalRef("");
                  setCredentialId("");
                  setCredentialName("");
                });
              }}
            >
              <div className="studio-settings-grid">
                <Select
                  label="新建或轮换"
                  value={credentialId}
                  onChange={(e) => {
                    setCredentialId(e.target.value);
                    setCredentialName(
                      current.credentials.find((c) => c.id === e.target.value)?.name ?? "",
                    );
                    setSecret("");
                    setExternalRef("");
                  }}
                >
                  <option value="">新建凭据</option>
                  {current.credentials.map((c) => (
                    <option value={c.id} key={c.id}>
                      {c.name} · v{c.version}
                    </option>
                  ))}
                </Select>
                <Input
                  label="凭据名称"
                  value={credentialName}
                  maxLength={100}
                  onChange={(e) => setCredentialName(e.target.value)}
                  required
                />
                <Input
                  label="密钥值（与外部引用二选一）"
                  type="password"
                  autoComplete="off"
                  value={secret}
                  maxLength={8192}
                  onChange={(e) => setSecret(e.target.value)}
                />
                <Input
                  label="外部引用（env://ACCOS_PROVIDER_SECRET_…）"
                  value={externalRef}
                  onChange={(e) => setExternalRef(e.target.value)}
                />
              </div>
              <Button busy={busy} type="submit">
                保存凭据
              </Button>
            </form>
            <ul className="studio-settings-list">
              {current.credentials.map((c) => (
                <li key={c.id}>
                  <span>
                    {c.name} · {c.storage} · <code>{c.secret_ref}</code>
                  </span>
                  <Button
                    disabled={!c.active || busy}
                    variant="secondary"
                    onClick={() =>
                      void act(async () =>
                        successful(
                          await client.PUT("/api/v1/settings/credentials", {
                            params: { header: versionHeader(c.version) },
                            body: {
                              id: c.id,
                              name: c.name,
                              expected_version: c.version,
                              active: false,
                            },
                          }),
                        ),
                      )
                    }
                  >
                    {c.active ? "停用" : "已停用"}
                  </Button>
                </li>
              ))}
            </ul>
            <Button
              busy={busy}
              variant="secondary"
              onClick={() =>
                void act(async () =>
                  successful(
                    await client.POST("/api/v1/settings/credentials/rewrap", {
                      params: { header },
                    }),
                  ),
                )
              }
            >
              用安装入口配置的新主密钥重新加密
            </Button>
          </section>
          <section className="studio-panel">
            <h2>工作区成员</h2>
            <p>团队身份按身份服务的 issuer 与 subject 精确绑定，不根据邮箱自动合并。</p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () => {
                  successful(
                    await client.PUT("/api/v1/identity/members", {
                      params: { header: versionHeader(0) },
                      body: {
                        issuer: memberIssuer,
                        subject: memberSubject,
                        role: memberRole,
                        active: true,
                        expected_version: 0,
                        ...(memberPassword ? { password: memberPassword } : {}),
                      },
                    }),
                  );
                  setMemberPassword("");
                  setMemberSubject("");
                });
              }}
            >
              <div className="studio-settings-grid">
                <Input
                  label="身份发行方（本地：urn:accos:local）"
                  value={memberIssuer}
                  onChange={(e) => setMemberIssuer(e.target.value)}
                  required
                />
                <Input
                  label="本地账号或团队 subject"
                  value={memberSubject}
                  onChange={(e) => setMemberSubject(e.target.value)}
                  required
                />
                <Select
                  label="角色"
                  value={memberRole}
                  onChange={(e) => setMemberRole(e.target.value as Member["role"])}
                >
                  <option value="OWNER">管理员 / 审批人</option>
                  <option value="EDITOR">编辑</option>
                  <option value="VIEWER">只读</option>
                </Select>
                <Input
                  label="新本地账号初始密码（已有账号留空）"
                  type="password"
                  minLength={12}
                  autoComplete="new-password"
                  value={memberPassword}
                  onChange={(e) => setMemberPassword(e.target.value)}
                />
              </div>
              <Button busy={busy} type="submit">
                添加成员
              </Button>
            </form>
            <ul className="studio-settings-list">
              {current.members.map((m) => (
                <li key={m.id}>
                  <span>
                    {m.subject} · <code>{m.user_id}</code> · {m.active ? "有效" : "已撤权"}
                  </span>
                  <Select
                    label={`${m.subject} 的角色`}
                    value={m.role}
                    disabled={busy}
                    onChange={(e) =>
                      void act(() => memberChange(m, e.target.value as Member["role"], m.active))
                    }
                  >
                    <option value="OWNER">管理员</option>
                    <option value="EDITOR">编辑</option>
                    <option value="VIEWER">只读</option>
                  </Select>
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void act(() => memberChange(m, m.role, !m.active))}
                  >
                    {m.active ? "撤销成员资格" : "恢复成员资格"}
                  </Button>
                </li>
              ))}
            </ul>
          </section>
          <section className="studio-panel">
            <h2>项目、作者与宇宙授权</h2>
            <p>
              项目首次添加专属授权后，仅管理员及仍有授权的成员可访问；撤销最后一条授权也不会重新公开。跨作者与宇宙资料始终需要明确授权。
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () =>
                  successful(
                    await client.PUT("/api/v1/identity/grants", {
                      params: { header: versionHeader(0) },
                      body: {
                        expected_version: 0,
                        grant: {
                          id: crypto.randomUUID(),
                          workspace_id: identity.workspace_id,
                          user_id: grantUser,
                          scope_kind: grantKind,
                          scope_id: grantScope,
                          permissions: grantPermissions
                            .split(",")
                            .map((p) => p.trim())
                            .filter(Boolean),
                          active: true,
                          version: 1,
                        },
                      },
                    }),
                  ),
                );
              }}
            >
              <div className="studio-settings-grid">
                <Select
                  label="授权成员"
                  value={grantUser}
                  onChange={(e) => setGrantUser(e.target.value)}
                  required
                >
                  <option value="">选择成员</option>
                  {current.members
                    .filter((m) => m.active)
                    .map((m) => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.subject}
                      </option>
                    ))}
                </Select>
                <Select
                  label="资源类型"
                  value={grantKind}
                  onChange={(e) => setGrantKind(e.target.value as Grant["scope_kind"])}
                >
                  <option value="project">项目</option>
                  <option value="creator">作者（记忆身份 ID）</option>
                  <option value="universe">宇宙</option>
                </Select>
                <Input
                  label="资源 ID"
                  value={grantScope}
                  onChange={(e) => setGrantScope(e.target.value)}
                  required
                />
                <Input
                  label="权限（逗号分隔）"
                  value={grantPermissions}
                  onChange={(e) => setGrantPermissions(e.target.value)}
                  required
                />
              </div>
              <Button busy={busy} type="submit">
                保存授权
              </Button>
            </form>
            <ul className="studio-settings-list">
              {current.grants.map((g) => (
                <li key={g.id}>
                  <span>
                    {g.scope_kind} · {g.scope_id} → {g.user_id} · {g.permissions.join("、")}
                  </span>
                  <Button
                    disabled={busy}
                    variant="secondary"
                    onClick={() => void act(() => revokeGrant(g))}
                  >
                    {g.active ? "撤销" : "恢复"}
                  </Button>
                </li>
              ))}
            </ul>
          </section>
          <section className="studio-panel">
            <h2>待处理作者决定</h2>
            <p>每个请求保留创建时的审批策略。修改当前策略不会改动旧请求。</p>
            {current.approvals.length ? (
              <ul className="studio-settings-list">
                {current.approvals.map((a) => (
                  <li key={a.id}>
                    <span>
                      {a.kind} · {a.resource_id} · {a.status} · {a.approval_policy_ref}
                    </span>
                    {a.status === "pending" ? (
                      <>
                        <Button
                          disabled={busy}
                          onClick={() =>
                            void act(async () =>
                              successful(
                                await client.POST(
                                  "/api/v1/identity/control-requests/{request_id}/decision",
                                  {
                                    params: { header, path: { request_id: a.id } },
                                    body: { decision: "approve" },
                                  },
                                ),
                              ),
                            )
                          }
                        >
                          批准
                        </Button>
                        <Button
                          disabled={busy}
                          variant="secondary"
                          onClick={() =>
                            void act(async () =>
                              successful(
                                await client.POST(
                                  "/api/v1/identity/control-requests/{request_id}/decision",
                                  {
                                    params: { header, path: { request_id: a.id } },
                                    body: { decision: "reject" },
                                  },
                                ),
                              ),
                            )
                          }
                        >
                          拒绝
                        </Button>
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p>暂无作者控制请求。创作流程中的审批仍在对应运行详情页处理。</p>
            )}
          </section>
          <section className="studio-panel">
            <h2>设置导入与导出</h2>
            <p>导出不含密码、令牌和密钥值；导入仅更新可写偏好，密钥需单独配置。</p>
            <Button
              variant="secondary"
              onClick={() =>
                void act(async () =>
                  setExportText(
                    JSON.stringify(
                      data(await client.GET("/api/v1/settings/export", { params: { header } })),
                      null,
                      2,
                    ),
                  ),
                )
              }
            >
              生成脱敏导出
            </Button>
            {exportText ? (
              <textarea aria-label="脱敏设置导出" readOnly rows={8} value={exportText} />
            ) : null}
            <textarea
              aria-label="待导入的设置 JSON"
              rows={6}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
            />
            <Button
              disabled={busy || !importText.trim()}
              onClick={() =>
                void act(async () => {
                  const parsed: unknown = JSON.parse(importText);
                  if (typeof parsed !== "object" || parsed === null || !("values" in parsed))
                    throw new Error("导入格式需要包含 values。");
                  successful(
                    await client.POST("/api/v1/settings/import", {
                      params: { header: versionHeader(current.settings.version) },
                      body: {
                        expected_version: current.settings.version,
                        values: parsed.values as Values,
                      },
                    }),
                  );
                  setImportText("");
                })
              }
            >
              导入偏好
            </Button>
          </section>
        </>
      ) : (
        <p>成员、审批策略和服务凭据由工作区管理员管理。</p>
      )}
      <section className="studio-panel">
        <h2>能力状态</h2>
        <div className="studio-table-scroll">
          <table>
            <thead>
              <tr>
                <th>能力</th>
                <th>实现</th>
                <th>配置</th>
                <th>健康</th>
                <th>验证</th>
                <th>数据</th>
              </tr>
            </thead>
            <tbody>
              {current.capabilities.map((c) => (
                <tr key={c.capability}>
                  <th>{c.capability}</th>
                  <td>{c.implementation}</td>
                  <td>{c.configuration}</td>
                  <td>{c.health}</td>
                  <td>
                    <Badge tone="neutral">{c.verification}</Badge>
                  </td>
                  <td>{c.data}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>未验证的能力不表示已通过测试；高级能力随所属施工步骤接入。</p>
      </section>
    </section>
  );
}

function Preferences({
  initial,
  editable,
  busy,
  save,
}: {
  initial: Settings;
  editable: boolean;
  busy: boolean;
  save: (values: Values) => Promise<void>;
}) {
  const [values, setValues] = useState<Values>(initial.values);
  function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void save(values);
  }
  return (
    <form className="studio-panel" onSubmit={submit}>
      <h2>工作区偏好</h2>
      <p>版本 {initial.version}。并发修改会提示冲突，请重新读取后保存。</p>
      <fieldset disabled={!editable || busy}>
        <div className="studio-settings-grid">
          <Input
            label="工作区名称"
            maxLength={100}
            value={values.name ?? ""}
            onChange={(e) => setValues({ ...values, name: e.target.value })}
            required
          />
          <Select
            label="审批方式（仅影响新请求）"
            value={values.approval_mode}
            onChange={(e) =>
              setValues({ ...values, approval_mode: e.target.value as Values["approval_mode"] })
            }
          >
            <option value="human_owner">个人作者本人确认</option>
            <option value="dual_control">团队双人审批</option>
          </Select>
          <Select
            label="默认创作模式"
            value={values.default_creation_mode}
            onChange={(e) =>
              setValues({
                ...values,
                default_creation_mode: e.target.value as Values["default_creation_mode"],
              })
            }
          >
            <option value="assisted">辅助</option>
            <option value="collaborative">协作</option>
            <option value="delegated">托管</option>
          </Select>
          <Select
            label="界面语言"
            value={values.locale}
            onChange={(e) => setValues({ ...values, locale: e.target.value as Values["locale"] })}
          >
            <option value="zh-CN">简体中文</option>
            <option value="en">English</option>
          </Select>
          <Input
            label="时区"
            value={values.timezone ?? ""}
            onChange={(e) => setValues({ ...values, timezone: e.target.value })}
            required
          />
          <Input
            label="每日模型 token 预算"
            type="number"
            min={0}
            max={100000000}
            value={String(values.daily_token_budget ?? 100000)}
            onChange={(e) => setValues({ ...values, daily_token_budget: Number(e.target.value) })}
          />
        </div>
        <label className="studio-check-label">
          <input
            type="checkbox"
            checked={values.cloud_content_allowed ?? false}
            onChange={(e) => setValues({ ...values, cloud_content_allowed: e.target.checked })}
          />
          允许已配置的云端模型处理作品资料
        </label>
        <p>创作模式、预算和出站许可将由后续模型与调度步骤消费；当前保存偏好不会发起模型调用。</p>
        <Button type="submit" busy={busy}>
          保存偏好
        </Button>
      </fieldset>
    </form>
  );
}
