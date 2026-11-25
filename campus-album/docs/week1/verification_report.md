# 校园影集｜第一周联调验收与测试报告

- **项目路径**：`campus-album`
- **验证时间**：`2026-11-25 19:29:12 +0800` ～ `2026-11-25 19:30:17 +0800`（UTC `2026-11-25T11:29:12Z` ～ `11:30:17Z`）
- **验证环境**：
  - Python：`.venv/bin/python`（Python 3.14，Flask 3.1.3）
  - Node.js：`/opt/homebrew/bin/node`（`v26.0.0`，用于微信小程序 JS 语法静态校验）
  - 数据库：SQLite 3（全部自动化测试与演示抓包均通过环境变量 `CAMPUS_ALBUM_DATABASE` 指向临时隔离数据库，不污染默认实例库）
- **验收结论**：**全部通过（PASS）** — 11 项自动化测试（含真实 Flask 子进程重启持久化测试）零失败、零警告通过；实时 HTTP 联调抓包全部符合第一周接口契约；小程序 5 个 JSON、5 个 JS 及 3 组页面文件静态校验全部通过；第一周扩展设计文档及线框图均已齐备。

---

## 1. 第一周验收项总览

| 验收项 | 对应要求（`README.md`） | 实际验证结果 | 状态 |
|---|---|---|---|
| 服务健康检查 | `GET /api/health` 返回 `200` `{"status":"ok"}` | 返回 `HTTP 200`，JSON `{"status": "ok"}` | PASS |
| 空库作品流 | 无作品时 `GET /api/posts` 返回 `200` `{"posts":[]}` | 返回 `HTTP 200`，JSON `{"posts": []}` | PASS |
| 账号注册与去重 | `POST /api/auth/register` 成功 `201`，空字段 `400`，重名 `409`，默认 `role='user'`，密码哈希存储 | 全部命中预期状态码与统一错误结构，数据库存密码哈希而非明文 | PASS |
| 登录与错误拦截 | `POST /api/auth/login` 成功 `200` 返回 `token` + `user`；错误密码 / 不存在用户 `401`；令牌存 SHA-256 摘要与过期时间 | 全部命中预期，`sessions.token_digest` 存 SHA-256 摘要且校验 `expires_at` | PASS |
| 发帖鉴权与校验 | 未带令牌 / 无效令牌 / 过期会话 / 已删除用户 `401`；空白或纯空格正文 `400` 统一错误格式 | 全部命中预期，非法输入未写入 `posts` 表 | PASS |
| 发布文字与列表展示 | 首尾空白自动裁剪，返回 `201` `{"post":{id,text,author,createdAt}}`；列表仅返回 `status='visible'` 且未删除作者作品，按 `created_at DESC, id DESC` 倒序 | 精确裁剪中文正文首尾空白，排序与可见性过滤全部通过 | PASS |
| 后端重启持久化与 `init-db` 幂等 | 终止 Flask 进程并重新启动后，刷新首页仍返回已发布作品；重复执行 `init-db` 保留已有记录 | 进程 PID 9528 终止后重复 `init-db`，新进程 PID 9531 返回完全一致的作品对象且旧令牌仍有效 | PASS |
| 小程序静态检查 | JSON 合法、JS 无语法错误、`urlCheck: false`、页面文件与 `utils/api.js` 导出一致 | 5 个 JSON + 5 个 JS + 3 个页面（12 文件）全部通过校验 | PASS |
| 第一周设计文档 | `docs/week1/comments_ratings_design.md` 与 `admin_web_design.md` 齐备 | 两份设计文档与两张线框图 PNG 均存在 | PASS |

---

## 2. 自动化测试套件结果（Verbatim）

### 2.1 复现命令

```sh
cd campus-album
.venv/bin/python -m unittest discover -s tests -v
```

### 2.2 原始测试输出（采集时间：`2026-11-25 19:30:17 +0800`）

```text
test_create_post_auth_guards (test_week1_flow.Week1ApiTestCase.test_create_post_auth_guards) ... ok
test_create_post_rejects_blank_and_whitespace (test_week1_flow.Week1ApiTestCase.test_create_post_rejects_blank_and_whitespace) ... ok
test_create_post_trims_whitespace_and_returns_expected_shape (test_week1_flow.Week1ApiTestCase.test_create_post_trims_whitespace_and_returns_expected_shape) ... ok
test_health_endpoint (test_week1_flow.Week1ApiTestCase.test_health_endpoint) ... ok
test_init_db_rerun_preserves_existing_rows (test_week1_flow.Week1ApiTestCase.test_init_db_rerun_preserves_existing_rows) ... ok
test_list_posts_empty_on_fresh_db (test_week1_flow.Week1ApiTestCase.test_list_posts_empty_on_fresh_db) ... ok
test_list_posts_ordering_and_visibility_filtering (test_week1_flow.Week1ApiTestCase.test_list_posts_ordering_and_visibility_filtering) ... ok
test_login_success_wrong_password_and_nonexistent_user (test_week1_flow.Week1ApiTestCase.test_login_success_wrong_password_and_nonexistent_user) ... ok
test_register_success_duplicate_and_db_storage (test_week1_flow.Week1ApiTestCase.test_register_success_duplicate_and_db_storage) ... ok
test_register_validation_errors (test_week1_flow.Week1ApiTestCase.test_register_validation_errors) ... ok
test_post_persists_across_flask_restart_and_init_db_rerun (test_week1_flow.Week1LiveRestartPersistenceTestCase.test_post_persists_across_flask_restart_and_init_db_rerun) ... ok

----------------------------------------------------------------------
Ran 11 tests in 1.630s

OK
```

### 2.3 测试覆盖明细（`tests/test_week1_flow.py`）

| 测试类 | 测试用例 | 覆盖要点 |
|---|---|---|
| `Week1ApiTestCase` | `test_health_endpoint` | `GET /api/health` -> `200` `{"status": "ok"}` |
| `Week1ApiTestCase` | `test_list_posts_empty_on_fresh_db` | 新建空库 `GET /api/posts` -> `200` `{"posts": []}` |
| `Week1ApiTestCase` | `test_register_success_duplicate_and_db_storage` | 注册返回 `201`、`role='user'`、密码哈希存储、重复用户名返回 `409` 统一错误 |
| `Week1ApiTestCase` | `test_register_validation_errors` | 空/纯空格/缺失/非字符串字段及非法 JSON 请求体均返回 `400` 统一错误 |
| `Week1ApiTestCase` | `test_login_success_wrong_password_and_nonexistent_user` | 登录成功 `200` + `sessions.token_digest` SHA-256 摘要校验；错密码 `401`；不存在用户 `401`；空字段 `400` |
| `Week1ApiTestCase` | `test_create_post_auth_guards` | 无 `Authorization`、非 Bearer、无效令牌、过期会话、`deleted_at` 非空用户均返回 `401` |
| `Week1ApiTestCase` | `test_create_post_rejects_blank_and_whitespace` | `""`、`"   "`、`"\t\n  "`、缺失 `text`、非字符串 `text` 均返回 `400`，且不入库 |
| `Week1ApiTestCase` | `test_create_post_trims_whitespace_and_returns_expected_shape` | 首尾空白自动裁剪，返回 `201` 完整 `post` 对象，ISO-8601 UTC `createdAt` |
| `Week1ApiTestCase` | `test_list_posts_ordering_and_visibility_filtering` | 精确验证 `created_at DESC, id DESC`（含同秒按 ID 倒序），过滤 `status='removed'` 与已软删用户作品 |
| `Week1ApiTestCase` | `test_init_db_rerun_preserves_existing_rows` | 重复调用 `init-db` 后既有作品记录完整保留 |
| `Week1LiveRestartPersistenceTestCase` | `test_post_persists_across_flask_restart_and_init_db_rerun` | 启动真实 Flask 进程 -> 注册/登录/发布中文作品 -> 彻底终止进程并确认端口不可达 -> 重复 `init-db` -> 启动全新 Flask 进程 -> 验证原作品及旧 Bearer 令牌均持续有效 |

### 2.4 Flask 已注册路由核验

命令：`.venv/bin/python -m flask --app backend/campus_album routes`

```text
Endpoint                   Methods  Rule                   
-------------------------  -------  -----------------------
auth.login                 POST     /api/auth/login        
auth.register              POST     /api/auth/register     
health                     GET      /api/health            
posts_feed.list_posts      GET      /api/posts             
posts_publish.create_post  POST     /api/posts             
static                     GET      /static/<path:filename>
```

---

## 3. 端到端实时 HTTP 演示抓包（含重启前后持久化证明）

以下输出于 `2026-11-25 19:29:17 +0800` 在真实本地 Flask 进程（临时 `CAMPUS_ALBUM_DATABASE`）上逐项采集（响应中的令牌已脱敏展示前缀）：

```text
[0. init-db] rc=0 output='Campus Album database is ready.'
[Server #1 started] pid=9528 url=http://127.0.0.1:51682
[1. Health check] GET /api/health -> HTTP 200
{
  "status": "ok"
}
[2. Empty feed] GET /api/posts -> HTTP 200
{
  "posts": []
}
[3. Register user] POST /api/auth/register -> HTTP 201
{
  "user": {
    "id": 1,
    "username": "campus_demo"
  }
}
[4. Login (wrong password)] POST /api/auth/login -> HTTP 401
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "用户名或密码错误"
  }
}
[5. Login (success)] POST /api/auth/login -> HTTP 200
{
  "token": "q2EQ4GuCTLDn...<redacted>",
  "user": {
    "id": 1,
    "username": "campus_demo"
  }
}
[6. Publish (blank text)] POST /api/posts -> HTTP 400
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "请输入作品内容"
  }
}
[7. Publish (valid Chinese post)] POST /api/posts -> HTTP 201
{
  "post": {
    "author": {
      "id": 1,
      "username": "campus_demo"
    },
    "createdAt": "2026-11-25T11:29:17Z",
    "id": 1,
    "text": "今天在校运会上认识了新朋友，南区操场的晚霞真好看！"
  }
}
[8. List posts BEFORE restart] GET /api/posts -> HTTP 200
{
  "posts": [
    {
      "author": {
        "id": 1,
        "username": "campus_demo"
      },
      "createdAt": "2026-11-25T11:29:17Z",
      "id": 1,
      "text": "今天在校运会上认识了新朋友，南区操场的晚霞真好看！"
    }
  ]
}
[Server #1 stopped] pid=9528 returncode=-15
[9. init-db rerun] rc=0 output='Campus Album database is ready.'
[Server #2 started] pid=9531 url=http://127.0.0.1:51693
[10. Health check AFTER restart] GET /api/health -> HTTP 200
{
  "status": "ok"
}
[11. List posts AFTER restart] GET /api/posts -> HTTP 200
{
  "posts": [
    {
      "author": {
        "id": 1,
        "username": "campus_demo"
      },
      "createdAt": "2026-11-25T11:29:17Z",
      "id": 1,
      "text": "今天在校运会上认识了新朋友，南区操场的晚霞真好看！"
    }
  ]
}
[Server #2 stopped] pid=9531 returncode=-15
```

> **重启持久化比对结果**：Server #1（`pid=9528`）在发布后返回的 `id=1`、`text="今天在校运会上认识了新朋友，南区操场的晚霞真好看！"`、`author={"id": 1, "username": "campus_demo"}`、`createdAt="2026-11-25T11:29:17Z"`，在进程完全终止（`SIGTERM`, `returncode=-15`）、重复执行 `init-db` 并启动全新进程 Server #2（`pid=9531`）后，再次请求 `GET /api/posts` 返回逐字段完全一致的记录。

---

## 4. 微信小程序静态校验结果

### 4.1 JSON 配置解析与页面完整性

| 文件路径 | 校验结果 | 关键检查项 |
|---|---|---|
| `miniprogram/project.config.json` | PASS | 合法 JSON，`appid: "touristappid"`，`miniprogramRoot: "./"`，`setting.urlCheck: false`（支持连接本地 `http://127.0.0.1:5001`） |
| `miniprogram/app.json` | PASS | 合法 JSON，`pages` 注册 `pages/index/index`、`pages/login/login`、`pages/publish/publish`，导航栏色 `#156082` |
| `miniprogram/pages/index/index.json` | PASS | 合法 JSON，`enablePullDownRefresh: true`，标题 `"校园影集"` |
| `miniprogram/pages/login/login.json` | PASS | 合法 JSON，配置完整 |
| `miniprogram/pages/publish/publish.json` | PASS | 合法 JSON，配置完整 |

- 页面四件套完整性：`pages/index/*`、`pages/login/*`、`pages/publish/*` 各自的 `.js`、`.json`、`.wxml`、`.wxss` 共 12 个文件均已齐备。

### 4.2 JavaScript 语法校验（`node --check`，Node `v26.0.0`）

```text
OK JS: miniprogram/app.js
OK JS: miniprogram/utils/api.js
OK JS: miniprogram/pages/index/index.js
OK JS: miniprogram/pages/login/login.js
OK JS: miniprogram/pages/publish/publish.js
```

### 4.3 前后端契约与页面事件一致性审查

- **`utils/api.js` 导出契约**：`BASE_URL`、`getToken`、`getUser`、`setSession`、`clearSession`、`request`、`register`、`login`、`createPost`、`listPosts` 全部导出并与三个页面调用完全匹配；`request()` 正确注入 `Authorization: Bearer <token>` 并解析后端 `{"error":{"code","message"}}` 拒绝为 `{ statusCode, code, message }`。
- **WXML 事件绑定一致性**：
  - `pages/index/index.wxml`：`handleGoPublish`、`handleLogout`、`handleGoLogin`、`handleRefresh` 均在 `index.js` 中定义；支持 `onShow` 自动加载、下拉刷新与手动“刷新列表”按钮。
  - `pages/login/login.wxml`：`onSwitchMode`、`onToggleMode`、`onUsernameInput`、`onPasswordInput`、`onSubmit`、`onLogout`、`onContinueAsGuest` 均在 `login.js` 中定义；错误密码（`401`）与重名注册（`409`）均在页面内联提示。
  - `pages/publish/publish.wxml`：`onTextInput`、`onSubmit`、`onCancel`、`onGoToLogin` 均在 `publish.js` 中定义；空白正文提交留在当前页提示“请输入作品内容”，`401` 清理本地会话并引导重新登录。

---

## 5. 第一周扩展设计文档检查

| 文件路径 | 大小 | 状态 |
|---|---|---|
| `docs/week1/comments_ratings_design.md` | 22,313 bytes | 存在 |
| `docs/week1/assets/comments_ratings_wireframe.png` | 353,456 bytes | 存在 |
| `docs/week1/admin_web_design.md` | 21,811 bytes | 存在 |
| `docs/week1/assets/admin_web_wireframe.png` | 407,036 bytes | 存在 |

---

## 6. 复现命令与可复用验收记录（供后续文档 / 周报 / PPT 直接引用）

### 6.1 本地启动与联调复现命令

```sh
# macOS / Linux（在 campus-album 目录执行）
.venv/bin/python -m flask --app backend/campus_album init-db
.venv/bin/python -m flask --app backend/campus_album run --port 5001

# 另开终端运行完整第一周自动化验收测试（含重启持久化）
.venv/bin/python -m unittest discover -s tests -v
```

### 6.2 标准用户故事、页面行为与验收记录

- **用户故事（US-W1-01）**：作为深圳大学学生，我希望在“校园影集”小程序中注册并登录个人账号，发布一条校园文字动态，并在返回首页及后端重启后依然能看到该作品（含正文、作者与发布时间）；同时在输入错误密码或提交空白内容时获得清晰提示而不丢失当前页上下文。
- **页面行为路径**：
  1. 游客进入首页 `pages/index/index`，展示空态或可见作品流，点击“去登录”进入 `pages/login/login`。
  2. 在登录页输入错误密码提交时，后端返回 `401 INVALID_CREDENTIALS`，页面停留在登录页并展示红底内联错误条“用户名或密码错误”。
  3. 切换“注册”或使用有效账号登录后，本地保存 `token` 与 `user` 并 `wx.reLaunch` 回到首页，顶部切换为已登录状态。
  4. 点击“发文字作品”进入 `pages/publish/publish`：输入纯空格点击发布时，留在当前页提示“请输入作品内容”（后端同样返回 `400 INVALID_INPUT` 兜底）；输入有效中文正文后提交成功返回 `201` 并回到首页。
  5. 首页 `onShow` 拉取 `GET /api/posts`，按 `created_at DESC, id DESC` 倒序呈现正文、作者与格式化时间；停止并重启本地 Flask 进程后，点击首页“刷新列表”或下拉刷新，刚发布的作品完整保留。
- **验收记录**：`2026-11-25 19:30 +0800` 执行 `tests/test_week1_flow.py` 全部 11 项用例（`Ran 11 tests in 1.630s — OK`）及实机子进程重启抓包与小程序静态校验，全部通过。
