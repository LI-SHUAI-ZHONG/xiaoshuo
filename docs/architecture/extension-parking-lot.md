# 扩展能力停车场

## 定位

多模态、通用关系图、协作、权属、市场、信誉、增长和外部知识网络均为远期能力。当前只提供框架无关契约、默认关闭的 Feature Flag、权限与事件清单、Null Adapter、状态 API 和晋升门槛；它们不是已完成的业务模块。

核心模块只依赖 `accos.kernel` 中的抽象契约，不导入 `accos.extensions` 或具体适配器。`accos.extensions` 不能导入核心私有仓储、应用服务、入口或组合根；只有组合根可以装配 `accos.adapters.extensions` 中的实现。

## 能力清单与默认状态

所有开关默认 `false`。关闭时不读取提供商配置、不要求 SDK、密钥、外部服务或网络访问，状态固定为 `DISABLED`。开关打开但仍使用 Null Adapter 时状态为 `NOT_CONFIGURED`，不会创建 Job、输出引用、用量、协作会话、权属结论或生态数据。

| 能力                              | Feature Flag         | 环境变量                                     | 默认适配器                     | 调用权限                        |
| --------------------------------- | -------------------- | -------------------------------------------- | ------------------------------ | ------------------------------- |
| `multimodal.image`                | `multimodal_image`   | `ACCOS_EXTENSION_MULTIMODAL_IMAGE_ENABLED`   | Null                           | `model:run`                     |
| `multimodal.audio`                | `multimodal_audio`   | `ACCOS_EXTENSION_MULTIMODAL_AUDIO_ENABLED`   | Null                           | `model:run`                     |
| `multimodal.video`                | `multimodal_video`   | `ACCOS_EXTENSION_MULTIMODAL_VIDEO_ENABLED`   | Null                           | `model:run`                     |
| `multimodal.three_d`              | `multimodal_three_d` | `ACCOS_EXTENSION_MULTIMODAL_THREE_D_ENABLED` | Null                           | `model:run`                     |
| `graph.relationship_projection`   | `graph`              | `ACCOS_EXTENSION_GRAPH_ENABLED`              | Null；启用后为 PostgreSQL 投影 | `project:read`                  |
| `collaboration.workspace`         | `collaboration`      | `ACCOS_EXTENSION_COLLABORATION_ENABLED`      | Null                           | `project:write`                 |
| `rights.metadata`                 | `rights`             | `ACCOS_EXTENSION_RIGHTS_ENABLED`             | Null                           | `workspace:write`、`audit:read` |
| `ecosystem.marketplace`           | `marketplace`        | `ACCOS_EXTENSION_MARKETPLACE_ENABLED`        | Null                           | `feature-flag:manage`           |
| `ecosystem.reputation`            | `reputation`         | `ACCOS_EXTENSION_REPUTATION_ENABLED`         | Null                           | `feature-flag:manage`           |
| `ecosystem.growth`                | `growth`             | `ACCOS_EXTENSION_GROWTH_ENABLED`             | Null                           | `feature-flag:manage`           |
| `knowledge_network.acquisition`   | `knowledge_network`  | `ACCOS_EXTENSION_KNOWLEDGE_NETWORK_ENABLED`  | Null                           | `project:write`                 |
| `knowledge_network.research_team` | `knowledge_network`  | 同上                                         | Null                           | `project:write`                 |
| `knowledge_network.verification`  | `knowledge_network`  | 同上                                         | Null                           | `project:read`                  |

`GET /api/v1/extensions/status` 只返回能力清单、真实运行状态、配置 schema、权限、事件和晋升条件。它要求 `workspace:read`，不返回配置值或凭据。

## 契约边界

### 多模态

Image、Audio、Video 与 3D 共用引用型契约：输入和输出只允许携带 Workspace、Project、Asset、Asset Version、Owner 与媒体类型引用；Job 另带 capability、状态、provenance、usage 和 safety 元数据。Null Adapter 返回 `NOT_CONFIGURED` 且 `job=None`，因此不会生成假资产或假用量。

### Graph

`GraphStore` 定义 Node、Edge、投影替换、删除、邻接读取、有限深度 traversal 和按权威事件 rebuild。`extension_graph_nodes` 与 `extension_graph_edges` 是可删除投影，不是事实源，也不部署独立图数据库。

PostgreSQL 适配器按 Workspace 与 `projection_owner` 隔离。重建流程先按事件 sequence 回放 `upsert/remove`，再在一个事务中替换投影；删除一个 owner 的投影不会影响其他 owner。遍历限制为深度 1–10、边数 1–1000。

### Collaboration

契约只表示 Team、Role、Task、Comment、Presence 和 collaborative-editor 请求。默认关闭且没有 WebSocket、CRDT、文档锁、在线状态或实时编辑实现。

### Rights

Rights 仅保存 owner、contributor、license metadata、permission、provenance 和 audit 引用，不作法律版权验证。`RightsBoundary` 在适配器返回后再次校验 Workspace、Asset 与核心 Owner；任一改变都会以 scope violation 拒绝。

### Ecosystem 与 Knowledge Network

Marketplace、Reputation、Growth 只有 manifest、权限、事件和状态，没有支付、商品、评分、推荐或增长算法。Knowledge Network 只有 Acquisition、Research Team、External Verification Provider 端口；Null Provider 不访问外网，也不生成专业知识内容。

## 晋升门槛

任何能力进入真实模块前，以下七项必须全部形成可审计批准记录：

1. 已验证的用户需求；
2. 明确的数据所有者；
3. 威胁模型；
4. SLO；
5. 成本上限与归属；
6. 数据和接口迁移方案；
7. 提供商退出与数据导出方案。

缺少任一项时，能力继续停留在停车场，不得接入真实 SDK、密钥、外网、支付或生产流量。
