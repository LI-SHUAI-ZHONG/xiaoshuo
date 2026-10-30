# 本地身份、设置与密钥

适用第25步真实身份实现。施工阶段仅交付本说明和工具，不在用户库执行初始化或迁移；下列操作在45的隔离安装验证，正式安装使用同一流程。

## 初始化与保留已有作品

1. 安装时先完成数据库迁移（单次、单实例；当前身份迁移为0013）。不要在API启动时自动改表。
2. 在私有安装目录运行`.venv/Scripts/python.exe -I scripts/setup_identity.py --output .secrets/identity`。工具只创建新目录，写`identity.env`和`bootstrap-token.txt`，不联网、不连接数据库，终端只显示文件路径。Windows先为新目录关闭继承并只授予当前安装用户SID完全控制，再生成秘密；每个新文件也在写入前收紧ACL。权限设置失败即停止，不改用宽松权限。POSIX目录/文件权限分别为0700/0600。不要覆盖已有主密钥；失败时保留已产生的私有文件，检查权限后使用新的目标目录。
3. 在本地`.env`设置`ACCOS_IDENTITY_CONFIG_FILE=.secrets/identity/identity.env`。加载顺序：默认值→`.env`→私有身份文件→进程环境变量。API和Worker必须使用同一身份配置和keyring，不能用空的进程环境变量覆盖它。相对路径以`.env`所在目录为准；缺失的显式配置文件报错，不生成临时密钥。
4. Studio配置`ACCOS_API_ORIGIN=http://127.0.0.1:8000`，浏览器地址与`ACCOS_PUBLIC_ORIGIN`一致。API对Host和写请求Origin进行检查；自托管代理的实际后端Host需加入`ACCOS_ALLOWED_HOSTS`。远程访问使用HTTPS，不关闭来源限制来解决代理配置问题。
5. 打开`/setup`，从本地文件读取一次性初始化凭据，填写作者账号和至少12字符口令。口令存Argon2id摘要，模型密钥独立加密；登录Cookie为HttpOnly，会话可到期/撤销，写请求有CSRF校验。
6. 唯一未归档旧开发工作区会被接管，保留作者、工作区、作品ID。多个旧工作区时先在安装配置填写`ACCOS_BOOTSTRAP_ADOPT_WORKSPACE_ID`，再初始化。初始化不会删除其他工作区；旧在途审批保持`legacy_dual_control`，新个人设置使用`human_owner`。

初始化标记在数据库中只消费一次；更换环境token不解除该标记。初始化后可按安装政策移走一次性token文件，但必须保存主密钥；不要重新生成一套keyring覆盖现有密文所需密钥。

安装参数`--public-origin https://studio.example`和`--adopt-workspace <UUID>`可以直接写入对应身份配置；默认来源仍为`http://localhost:3000`。旧命令`prepare_local_identity.py --output .secrets/new-install/auth.env`保留文件路径参数，但复用同一实现，要求父目录尚不存在，初始化token另存为同目录`bootstrap-token.txt`，不再打印到终端。两个入口都不会修改现有目录的ACL或覆盖已有配置。

## 日常操作与团队

`/settings`提供工作区设置及历史CAS、成员/角色、项目/Creator/Universe grant、当前会话撤销、密码修改、PAT创建/撤销、凭据写入/停用/轮换、设置导入导出、能力五维与审批。PAT仅首次返回明文，有限期和最小scope；不能用于真人审批。修改密码撤销已有浏览器会话。

团队OIDC配置issuer、client_id、authorization/token/JWKS端点和按需client_secret，端点须HTTPS。回调固定为`ACCOS_PUBLIC_ORIGIN/api/v1/auth/oidc/callback`。当前适配器采用授权码、S256 PKCE、state/nonce及RS256/JWKS；在设置中预先登记精确issuer/subject与角色，不按电子邮箱自动合并身份。首次本地Owner不依赖IdP。

团队登录取消、身份验证失败、缺少成员资格或配置时，回调返回`/login`并显示固定原因及重试入口。取消也验证state与浏览器绑定并消费该流程；失败后清理OIDC临时Cookie，不创建新登录会话，不把供应商错误详情、授权码或state带入重定向。授权端点已有的租户路由查询参数会保留，state、redirect_uri、client_id与PKCE等安全参数由本次登录生成并去重覆盖。

新个人流程可由真实Owner自己确认；团队`dual_control`仍要求不同Owner。切换策略只影响新请求，既有请求继续使用冻结版本。删除、核心代码安装、发布等后续领域仍绑定各自具体审批对象，不因个人模式而跳过权限。

## 主密钥和外部凭据

- `ACCOS_SECRET_KEYS_JSON`是key_id到32字节随机密钥的Base64映射，`ACCOS_SECRET_ACTIVE_KEY_ID`选当前写入key。密文绑定工作区/credential_id/version；数据表不保存主密钥。
- 轮换主密钥时先在安装keyring中保留旧key并追加新key，设置新active并让API/Worker加载，再在设置执行重包。逐条CAS、失败可续做；旧key需保留至重包与备份恢复验证完成。重包产生新凭据版本，消费方需采用新secret_ref；不得删除旧key后才尝试解密。
- 外部凭据可用`env://ACCOS_PROVIDER_SECRET_NAME`引用安装进程环境，不读取任意环境变量。导出只含引用/配置元数据；重新部署需重新配置对应环境秘密。
- 主密钥丢失时不能恢复密文原值。可恢复备份中的keyring；否则重新录入供应商密钥并更新消费引用，不伪造解密成功。

当前能力状态的实现、配置、健康、验证、数据独立展示；第25步的`untested`并非错误，也不能被当作健康通过。真实模型等后续能力尚未实现时明确显示待施工。

## 契约映射与最终待测

身份管理沿用单一`/api/v1`实现：`/auth/*`处理会话；`/identity/members|grants|creator|tokens|control-requests`处理成员授权；`/settings/workspace|export|import|credentials`和`/capabilities`处理配置。工作区由已验证的`X-Workspace-ID`解析，与方案中的`W/*`操作族对应，不新增第二套账户表或重复管理路径。

成员、grant、设置、凭据及设置导入使用`If-Match`强整数ETag并校验与body的`expected_version`一致；首次创建为`"0"`。缺少头返回428，版本不匹配409。身份秘密不进入通用响应重放缓存：初始化有一次性标记，OIDC state单次消费，PAT只返回一次；未知的PAT创建结果应先查看/撤销令牌，再明确重新创建，不能重放明文令牌。

T004–T010在45运行：一次性初始化/旧项目保留、口令与会话、双工作区与撤权、PKCE/JWKS/重放、个人/团队/机器审批、凭据绑定/轮换/脱敏、PAT范围/期限以及设置并发。新安装工具的防覆盖、私有文件加载优先级与秘密不输出也计入T004/T008。本步不提供任何已通过的运行结论。
