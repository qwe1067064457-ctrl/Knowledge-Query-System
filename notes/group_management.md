# group_management 模块说明

本文记录 `group_management` 模块目前已经完成的设计与实现，方便后续继续做登录、权限、知识库分组检索和前端管理能力时快速接上上下文。

## 1. 模块目标

`group_management` 是当前知识库系统的“组与用户治理层”。它解决的是：

- 谁是系统用户。
- 哪些知识库组存在。
- 用户属于哪些组。
- 用户在组里是什么角色。
- 创建组时应自动生成哪些知识库、记忆系统和元数据结构。

它不是聊天模块，也不是检索模块，而是这些模块的上游基础设施。

当前系统里，“组”基本等价于一个知识库/业务空间。后续聊天、记忆、知识库检索都应该逐步显式带上 `group_id`。

## 2. 当前已完成内容

已完成：

- 后端文件型用户管理。
- 后端文件型组管理。
- 后端组成员管理。
- 创建组时自动初始化知识库目录。
- 创建组时自动初始化组级 `memory_policy`。
- 用户、组、成员的软删除语义。
- FastAPI 路由。
- 前端 `/groups` 组管理看板。
- 前端 API client 类型与请求方法。
- 独立 `unittest` 测试套件。

未完成：

- 登录模块。
- API 鉴权。
- 角色权限真正生效。
- 用户邀请流程。
- 组级知识库检索过滤。
- 组详情编辑表单。
- `memory_policy` 可视化编辑器。
- 物理删除用户/组/成员数据。

当前版本可以理解为：**本地管理台 + 组模型基础设施**。它已经能支撑后续登录与权限模块接入，但本身还不是正式权限边界。

## 3. 后端模块结构

核心后端模块：

```text
backend/group_management/
  __init__.py
  models.py
  service.py
```

API 文件：

```text
backend/api/users.py
backend/api/groups.py
backend/app.py
```

其中：

- `models.py`：定义用户、组、成员关系的数据结构。
- `service.py`：实现文件型读写、创建、更新、归档、成员管理和目录初始化。
- `__init__.py`：导出 service 和异常类型。
- `api/users.py`：用户管理接口。
- `api/groups.py`：组和成员管理接口。
- `app.py`：注册 `users_router` 和 `groups_router`。

## 4. 核心数据模型

### 4.1 UserRecord

用户记录代表系统中的一个用户。

```json
{
  "id": "u1",
  "display_name": "User u1",
  "status": "active",
  "created_at": "2026-05-09T00:00:00+00:00",
  "updated_at": "2026-05-09T00:00:00+00:00",
  "metadata": {}
}
```

字段说明：

- `id`：用户 ID，也是文件路径的一部分，必须是安全路径片段。
- `display_name`：展示名称。
- `status`：用户状态。
- `created_at`：创建时间，UTC ISO 字符串。
- `updated_at`：更新时间，UTC ISO 字符串。
- `metadata`：扩展信息，当前不做固定 schema。

用户状态：

- `active`：正常用户。
- `disabled`：软删除/禁用用户。

删除用户时不删除文件，只把 `status` 改成 `disabled`。

### 4.2 GroupRecord

组记录代表一个知识库/业务空间。

```json
{
  "id": "law",
  "name": "Law KB",
  "description": "Legal knowledge",
  "status": "active",
  "default_agent_id": "default",
  "created_by": "u1",
  "created_at": "2026-05-09T00:00:00+00:00",
  "updated_at": "2026-05-09T00:00:00+00:00",
  "knowledge": {
    "root": "knowledge/groups/law",
    "documents": "knowledge/groups/law/documents",
    "uploads": "knowledge/groups/law/uploads"
  },
  "memory_policy": {},
  "metadata": {}
}
```

字段说明：

- `id`：组 ID，也是知识库和 storage 路径的一部分。
- `name`：组展示名。
- `description`：组描述。
- `status`：组状态。
- `default_agent_id`：该组默认使用的 agent 策略。
- `created_by`：创建人用户 ID。
- `knowledge`：该组的知识库目录信息。
- `memory_policy`：该组的记忆写入规则配置。
- `metadata`：扩展信息。

组状态：

- `active`：正常组。
- `archived`：归档组。

删除组时不删除目录，只把 `status` 改成 `archived`。

注意：`default_agent_id` 只是默认问答策略字段，不参与知识库或记忆的物理隔离。当前物理隔离主维度仍是 `group_id`。

### 4.3 MembershipRecord

成员记录表示一个用户在某个组中的角色。

```json
{
  "group_id": "law",
  "user_id": "u1",
  "role": "owner",
  "status": "active",
  "created_at": "2026-05-09T00:00:00+00:00",
  "updated_at": "2026-05-09T00:00:00+00:00"
}
```

角色：

- `owner`
- `admin`
- `member`
- `viewer`

成员状态：

- `active`：当前有效成员。
- `removed`：已从组中软移除。

移除成员时不删除记录，只把 `status` 改成 `removed`。

## 5. 文件型存储结构

当前不使用数据库，所有数据落在 `backend/storage` 和 `backend/knowledge` 下。

### 5.1 用户存储

```text
backend/storage/users/
  registry.json
  {user_id}/
    profile.json
```

说明：

- `registry.json` 是用户列表索引。
- `profile.json` 是单个用户详情。
- registry 损坏时，service 会按空 registry 处理，不会崩溃。

### 5.2 组存储

```text
backend/storage/groups/
  registry.json
  {group_id}/
    meta.json
    members.json
    shared/
      domain_cases.jsonl
```

说明：

- `registry.json` 是组列表索引。
- `meta.json` 是组元数据主文件。
- `members.json` 是组成员关系。
- `shared/domain_cases.jsonl` 是该组共享案例记忆文件。

`meta.json` 同时也是 `memory_system` 读取组级 `memory_policy` 的位置。

### 5.3 知识库目录

创建组时会初始化：

```text
backend/knowledge/groups/
  {group_id}/
    README.md
    documents/
      .gitkeep
    uploads/
      .gitkeep
```

说明：

- `README.md` 是该组知识库说明入口。
- `documents/` 是正式知识库文档目录。
- `uploads/` 是后续上传文件入口。
- 当前知识库索引器尚未按组过滤，这部分是给后续分组检索做准备。

## 6. GroupManagementService

入口：

```python
GroupManagementService(backend_dir: Path)
```

内部路径：

- `backend_dir / "storage" / "users"`
- `backend_dir / "storage" / "groups"`
- `backend_dir / "knowledge" / "groups"`

### 6.1 用户方法

```python
create_user(user_id, display_name=None, metadata=None)
get_user(user_id)
list_users(include_disabled=False)
update_user(user_id, display_name=None, metadata=None, status=None)
delete_user(user_id)
```

行为：

- `create_user` 写 `profile.json` 和 `storage/users/registry.json`。
- 重复创建用户抛 `ConflictError`。
- 非法 `user_id` 抛 `ValidationError`。
- `delete_user` 是软删除，将用户状态设为 `disabled`。
- `list_users()` 默认过滤 `disabled` 用户。
- `list_users(include_disabled=True)` 返回全部用户。

### 6.2 组方法

```python
create_group(
    group_id,
    name,
    created_by,
    description="",
    default_agent_id="default",
    memory_policy=None,
    metadata=None,
)
get_group(group_id)
list_groups(include_archived=False)
update_group(group_id, ...)
archive_group(group_id)
restore_group(group_id)
delete_group(group_id)
```

行为：

- 创建组要求 `created_by` 用户存在且未禁用。
- 重复创建组抛 `ConflictError`。
- 非法 `group_id` 抛 `ValidationError`。
- 创建组会写 `meta.json`。
- 创建组会写 `members.json`，创建人自动成为 `owner`。
- 创建组会初始化知识库目录。
- 创建组会初始化 `shared/domain_cases.jsonl`。
- 创建组会读取 `backend/memory_system/policy.default.json`。
- 传入 `memory_policy` 时，会与默认 policy 深合并。
- 默认 policy 文件缺失时，创建组仍成功，`memory_policy` 为空对象。
- `delete_group` 是软删除，实际调用 `archive_group`。
- `list_groups()` 默认过滤 `archived` 组。
- `list_groups(include_archived=True)` 返回全部组。

### 6.3 成员方法

```python
list_members(group_id, include_removed=False)
add_member(group_id, user_id, role="member")
remove_member(group_id, user_id)
```

行为：

- 添加成员前会确认组存在。
- 添加成员前会确认用户存在且未禁用。
- 角色必须是 `owner/admin/member/viewer` 之一。
- 重复添加同一用户不会追加重复记录，而是更新角色和状态。
- 移除成员是软移除，状态改成 `removed`。
- `list_members()` 默认过滤 `removed` 成员。
- `list_members(include_removed=True)` 返回全部成员记录。

## 7. 路径安全与异常

路径片段校验：

```text
[A-Za-z0-9_.@-]+
```

适用字段：

- `user_id`
- `group_id`
- `created_by`
- `default_agent_id`

禁止路径穿越，例如：

```text
../bad
```

异常类型：

- `GroupManagementError`：模块基础异常。
- `ValidationError`：非法参数、非法状态、非法角色、禁用用户参与操作。
- `NotFoundError`：用户、组、成员不存在。
- `ConflictError`：重复创建用户或组。

## 8. API 设计

### 8.1 用户 API

```text
GET    /api/users
POST   /api/users
GET    /api/users/{user_id}
PUT    /api/users/{user_id}
DELETE /api/users/{user_id}
```

查询参数：

- `GET /api/users?include_disabled=true`

创建用户请求：

```json
{
  "id": "u1",
  "display_name": "Alice",
  "metadata": {}
}
```

更新用户请求：

```json
{
  "display_name": "Alice",
  "metadata": {},
  "status": "active"
}
```

删除用户返回禁用后的用户记录。

### 8.2 组 API

```text
GET    /api/groups
POST   /api/groups
GET    /api/groups/{group_id}
PUT    /api/groups/{group_id}
DELETE /api/groups/{group_id}
POST   /api/groups/{group_id}/archive
POST   /api/groups/{group_id}/restore
```

查询参数：

- `GET /api/groups?include_archived=true`

创建组请求：

```json
{
  "id": "law",
  "name": "Law KB",
  "created_by": "u1",
  "description": "Legal knowledge",
  "default_agent_id": "default",
  "memory_policy": {},
  "metadata": {}
}
```

更新组请求：

```json
{
  "name": "Law KB",
  "description": "Updated description",
  "default_agent_id": "legal_qa",
  "memory_policy": {},
  "metadata": {},
  "status": "active"
}
```

### 8.3 成员 API

```text
GET    /api/groups/{group_id}/members
POST   /api/groups/{group_id}/members
DELETE /api/groups/{group_id}/members/{user_id}
```

查询参数：

- `GET /api/groups/{group_id}/members?include_removed=true`

添加成员请求：

```json
{
  "user_id": "u2",
  "role": "member"
}
```

### 8.4 API 错误映射

API 层把 service 异常映射为 HTTP 状态码：

- `ValidationError` -> 400
- `NotFoundError` -> 404
- `ConflictError` -> 409
- 其他异常 -> 500

## 9. app.py 集成

在 `backend/app.py` 中新增：

```python
from api.groups import router as groups_router
from api.users import router as users_router
```

并注册：

```python
app.include_router(users_router, prefix="/api", tags=["users"])
app.include_router(groups_router, prefix="/api", tags=["groups"])
```

因此前端访问路径统一为：

```text
http://127.0.0.1:8004/api/users
http://127.0.0.1:8004/api/groups
```

## 10. 创建组完整流程

创建组时，service 会按顺序完成：

1. 校验 `group_id`。
2. 校验 `created_by`。
3. 校验 `default_agent_id`。
4. 读取创建人用户记录。
5. 如果创建人不存在，抛 `NotFoundError`。
6. 如果创建人已禁用，抛 `ValidationError`。
7. 检查 `storage/groups/{group_id}/meta.json` 是否已经存在。
8. 如果已经存在，抛 `ConflictError`。
9. 读取 `backend/memory_system/policy.default.json`。
10. 将默认 `memory_policy` 与请求传入的 `memory_policy` 深合并。
11. 构造 `GroupRecord`。
12. 构造 owner 级 `MembershipRecord`。
13. 创建 `storage/groups/{group_id}/shared/`。
14. 创建 `storage/groups/{group_id}/shared/domain_cases.jsonl`。
15. 创建 `knowledge/groups/{group_id}/README.md`。
16. 创建 `knowledge/groups/{group_id}/documents/.gitkeep`。
17. 创建 `knowledge/groups/{group_id}/uploads/.gitkeep`。
18. 写入 `storage/groups/{group_id}/meta.json`。
19. 写入 `storage/groups/{group_id}/members.json`。
20. 更新 `storage/groups/registry.json`。
21. 返回组记录。

## 11. 与 memory_system 的关系

`memory_system` 使用：

```text
storage/groups/{group_id}/meta.json
```

中的：

```json
{
  "memory_policy": {}
}
```

作为组级记忆策略来源。

组管理模块负责创建和更新该字段，但不负责执行记忆写入。记忆写入仍由 `backend/memory_system` 模块负责。

当前记忆作用域约定：

- `core`：`user_global` 或 `user_group`
- `daily_log`：`user_group`
- `domain_case`：`group_shared`

其中：

- 用户级长期偏好属于用户。
- 每日日志主要属于用户在某个组中的时间线。
- 案例记忆属于组共享资源。

## 12. 与 agent_id 的关系

当前设计保留 `default_agent_id`，但不把 agent 作为存储隔离维度。

含义：

- `group_id`：知识库、记忆和成员关系的主隔离维度。
- `default_agent_id`：该组默认使用的问答策略。

也就是说：

- 不会创建 `storage/groups/{group_id}/agents/{agent_id}` 作为组管理主路径。
- 不会按 agent 拆分 group memory。
- 后续如果一个组内需要多个 agent，可以在组配置里扩展策略，但不改变组的主存储模型。

## 13. 前端组管理看板

页面路径：

```text
/groups
```

前端文件：

```text
frontend/src/app/groups/page.tsx
frontend/src/components/groups/GroupManagementPage.tsx
frontend/src/lib/api.ts
frontend/src/components/layout/Navbar.tsx
```

前端已新增 API 类型：

- `UserRecord`
- `GroupRecord`
- `MembershipRecord`

前端已新增 API 方法：

- `listUsers`
- `createUser`
- `deleteUser`
- `listGroups`
- `createGroup`
- `archiveGroup`
- `restoreGroup`
- `listGroupMembers`
- `addGroupMember`
- `removeGroupMember`

看板当前能力：

- 查看组列表。
- 选择当前组。
- 创建组。
- 归档组。
- 恢复组。
- 查看组基础信息。
- 查看组知识库初始化路径。
- 查看组 `memory_policy` JSON。
- 查看用户列表。
- 创建用户。
- 禁用用户。
- 查看成员列表。
- 添加成员。
- 移除成员。
- 从聊天页进入组管理。
- 从组管理页返回聊天页。

当前没有做：

- 用户登录态。
- 当前用户自动识别。
- 按角色禁用按钮。
- 组信息编辑表单。
- `memory_policy` 图形化编辑。

## 14. 前端交互细节

`GroupManagementPage` 内部维护自己的页面状态，不接入聊天页的全局 `AppStore`。

主要状态：

- `groups`
- `users`
- `members`
- `selectedGroupId`
- `includeArchived`
- `includeDisabled`
- `loading`
- `busy`
- `error`
- `notice`
- 用户表单
- 组表单
- 成员表单

交互规则：

- 进入页面后并行加载组和用户。
- 有组时默认选择第一个组。
- 切换组时刷新成员列表。
- 创建组后自动选择新组并刷新成员。
- 创建用户后刷新用户列表。
- 添加成员后刷新成员列表。
- 移除成员后刷新成员列表。
- 归档/恢复组后刷新组列表。
- API 错误显示在页面顶部。
- 操作期间按钮禁用。

## 15. 测试

测试目录：

```text
backend_test/group_management/
  .gitignore
  __init__.py
  helpers.py
  test_user_service.py
  test_group_service.py
  test_membership_service.py
  test_group_user_api.py
```

测试框架：

```text
unittest
```

测试运行：

```powershell
py -m unittest discover -s backend_test\group_management -p "test_*.py"
```

全量后端测试可运行：

```powershell
py -m unittest discover -s backend_test -p "test_*.py"
```

测试覆盖点：

### 用户测试

- 创建用户会写 `profile.json`。
- 创建用户会写 `registry.json`。
- 重复创建用户抛 `ConflictError`。
- 非法 `user_id` 抛 `ValidationError`。
- 删除用户是软删除，状态变为 `disabled`。
- 默认列表过滤 disabled 用户。
- `include_disabled=True` 返回 disabled 用户。
- 用户 metadata 能完整读写。
- 损坏 registry 文件时按空 registry 处理。

### 组测试

- 创建组要求创建人存在。
- 创建组要求创建人未禁用。
- 创建组写 `meta.json`。
- 创建组写 `members.json`。
- 创建人成为 `owner`。
- 创建 `shared/domain_cases.jsonl`。
- 创建 `knowledge/groups/{group_id}/README.md`。
- 创建 `documents/.gitkeep`。
- 创建 `uploads/.gitkeep`。
- 默认 `memory_policy` 会写入组记录。
- 传入局部 `memory_policy` 会深合并默认配置。
- 重复创建组抛 `ConflictError`。
- 非法 `group_id` 抛 `ValidationError`。
- 删除组是归档，状态变为 `archived`。
- 默认组列表过滤 archived 组。
- 默认 policy 文件缺失时仍可创建组，policy 为空。
- 更新组 policy 会深合并，不覆盖未传入字段。
- `default_agent_id` 只写入组元数据。

### 成员测试

- 添加 active 用户为成员。
- 添加 disabled 用户抛 `ValidationError`。
- 添加不存在用户抛 `NotFoundError`。
- 添加不存在组抛 `NotFoundError`。
- 重复添加同一用户会更新角色。
- 重复添加不会产生重复成员记录。
- 移除成员是软移除。
- 默认成员列表过滤 removed 成员。
- `include_removed=True` 返回 removed 成员。
- 移除不存在成员抛 `NotFoundError`。

### API 测试

- `POST /api/users` 创建用户成功。
- 重复 `POST /api/users` 返回 409。
- `DELETE /api/users/{user_id}` 返回 disabled 用户。
- `GET /api/users` 默认不返回 disabled 用户。
- `POST /api/groups` 创建组成功。
- 创建组会初始化目录。
- 创建人不存在时返回 404。
- 归档组后 `GET /api/groups` 默认不返回。
- `include_archived=true` 返回归档组。
- 添加成员成功。
- 删除成员返回 removed 状态。
- 非法 ID 映射为 400。

## 16. 测试辅助设计

`backend_test/group_management/helpers.py` 做了几件事：

- 将 `backend` 加入 `sys.path`。
- 创建临时 backend 根目录。
- 写入临时 `memory_system/policy.default.json`。
- 提供 `GroupManagementService` 工厂。
- 提供 JSON/JSONL 读取工具。
- 提供 `seed_user` 快速创建用户。
- 提供只挂载 users/groups router 的 FastAPI `TestClient`。

测试不会写真实：

- `backend/storage`
- `backend/knowledge`

而是写入测试临时目录。

`.gitignore` 忽略：

```text
.test_tmp/
__pycache__/
```

## 17. 已知工程注意点

### 17.1 当前没有真实鉴权

API 可以创建和修改用户、组、成员，但还没有校验当前请求者是谁。

后续登录模块完成后，需要补：

- 当前用户身份解析。
- owner/admin/member/viewer 权限校验。
- 非管理员禁止创建/归档/恢复组。
- viewer 只读。

### 17.2 删除都是软删除

当前不会物理删除：

- 用户 profile。
- 组 meta。
- 成员记录。
- 知识库目录。
- 记忆文件。

这样做的好处是避免误删历史知识库和记忆。真正物理删除可以后续做成危险操作。

### 17.3 主知识库索引还没有按组过滤

组目录已经改成：

```text
knowledge/groups/{group_id}
```

但当前知识库检索/索引模块是否按组过滤，需要后续单独改造。

当前组管理只是把结构准备好。

### 17.4 前端看板是管理入口，不是安全边界

前端可以隐藏按钮，但真正安全必须在后端 API 做。

当前 `/groups` 页面用于：

- 验证组/用户模型。
- 本地管理数据。
- 为登录和权限模块提前铺 UI。

### 17.5 编码显示问题

当前仓库部分中文文件在 PowerShell 输出中会出现乱码。这不一定代表文件内容损坏，可能是终端编码问题。后续若继续写中文 UI 文案，建议统一编辑器和终端 UTF-8。

## 18. 下一步建议

建议按这个顺序推进：

1. 修正前端中文乱码和构建验证。
2. 给 `/groups` 页面补组详情编辑能力。
3. 给 `memory_policy` 做轻量编辑器。
4. 登录模块落地。
5. API 接入当前用户身份。
6. 角色权限真正生效。
7. 聊天请求显式携带 `group_id`。
8. 知识库索引和检索支持按组过滤。
9. 前端聊天页支持选择当前组。
10. 做组级审计日志。

## 19. 常用命令

运行后端组管理测试：

```powershell
py -m unittest discover -s backend_test\group_management -p "test_*.py"
```

运行全部 backend_test：

```powershell
py -m unittest discover -s backend_test -p "test_*.py"
```

前端构建：

```powershell
cd frontend
npm ci
npm run build
```

后端启动：

```powershell
cd backend
py -m uvicorn app:app --reload --port 8004
```

前端启动：

```powershell
cd frontend
npm run dev
```

访问：

```text
http://localhost:3000
http://localhost:3000/groups
```

## 20. 总结

`group_management` 当前已经完成了第一版“文件型组/用户管理基础设施”：

- 数据模型已经有了。
- 后端 service 已经有了。
- API 已经有了。
- 前端看板已经有了。
- 测试已经覆盖主链路。
- 组初始化会生成知识库目录和记忆配置。

后续真正重要的工作，是把它接入登录、权限、聊天上下文和知识库检索。到那一步，`group_id` 会成为系统里最重要的业务隔离维度之一。
