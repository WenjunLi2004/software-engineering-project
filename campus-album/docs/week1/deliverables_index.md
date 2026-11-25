# 校园影集｜第一周交付索引与提交记录

- **项目名称**：校园影集（深圳大学软件工程课程大作业）
- **周期阶段**：第一周（最小闭环联调 + 第二/三周扩展模块前置设计）
- **Git 仓库与分支**：`software-engineering-project` / `campus-album/kickoff`（基线提交 `7aa45c1`，本地原子化提交，未推送远端）
- **整体验收状态**：**PASS**（`tests/test_week1_flow.py` 11/11 通过，耗时 `1.630s`；真实 Flask 子进程重启持久化与 `init-db` 幂等通过；小程序 5 个 JSON、5 个 JS、3 组页面静态检查全部通过；评论评分与管理员 Web 后台设计文档及 1280×720 线框图齐备）

---

## 1. 六角色内部交付跟踪表

| 模块和汇报人 | 本周实际产出 | 文件、提交或材料位置 | 验证情况 |
|---|---|---|---|
| **李文俊｜架构与联调** | 搭建 `.venv`（Python 3.14 / Flask 3.1.3）；编写统一错误与序列化工具 `errors.py`、`serializers.py`；在 `__init__.py` 集成三组业务蓝图及 `BadRequest` 非法 JSON 400 处理器；搭建小程序工程外壳（`project.config.json` 设 `urlCheck: false`、主题样式、封装 Bearer Token 与统一错误解析的 `utils/api.js`）；统筹本地原子化提交与整体验收 | 提交 `b340f75`（架构与联调集成）、`b1aade5`（测试套件与验收报告）<br>`campus-album/backend/campus_album/{errors.py,serializers.py,__init__.py}`<br>`campus-album/miniprogram/{project.config.json,app.js,app.json,app.wxss,utils/api.js}`<br>`campus-album/tests/test_week1_flow.py`<br>`campus-album/docs/week1/verification_report.md` | **已通过**：`flask --app backend/campus_album routes` 确认 5 条业务/健康接口全部注册；非法 JSON 返回 `400 INVALID_INPUT`；全套 11 项自动化测试与重启持久化实测通过；小程序 5 JSON / 5 JS 静态检查全过 |
| **陈俊年｜账号与权限** | 实现 `POST /api/auth/register`（`role='user'`、密码哈希、重名 `409 USERNAME_TAKEN`、空字段 `400`）与 `POST /api/auth/login`（随机 Token + SHA-256 摘要入 `sessions` + 7 天过期、错密码 `401 INVALID_CREDENTIALS`），导出 `get_current_user()` / `require_auth()`；实现微信小程序登录/注册切换页与游客返回入口 | 提交 `97092aa`<br>`campus-album/backend/campus_album/auth.py`<br>`campus-album/miniprogram/pages/login/{login.js,login.json,login.wxml,login.wxss}` | **已通过**：自动化测试验证注册 `201`/空输入 `400`/重名 `409`、密码哈希落库、登录 `200`/错密码与不存在用户 `401`、过期与软删用户 `401` 拦截；`py_compile`、`json.tool`、`node --check` 全部通过 |
| **吕辉亮｜发布与作品维护** | 实现 `POST /api/posts`（基于 `require_auth()` 校验 Bearer Token、自动裁剪正文首尾空白、空/纯空格返回 `400 INVALID_INPUT`、写入 `posts(status='visible')` 返回 `201` 标准作品对象）；实现小程序文字作品发布页（前端裁剪校验、字符计数、失败保留当前页提示、401 引导重新登录） | 提交 `571428b`<br>`campus-album/backend/campus_album/posts_publish.py`<br>`campus-album/miniprogram/pages/publish/{publish.js,publish.json,publish.wxml,publish.wxss}` | **已通过**：自动化测试与实机 HTTP 抓包验证无令牌/错令牌 `401`、空白正文 `400`（不入库）、带首尾空格中文正文自动裁剪并 `201` 入库；`py_compile`、`json.tool`、`node --check` 全部通过 |
| **黄子特｜浏览与检索** | 实现 `GET /api/posts`（仅返回 `posts.status='visible'` 且 `users.deleted_at IS NULL` 的作品，严格按 `created_at DESC, id DESC` 倒序，空库返回 `{"posts":[]}`）；实现小程序首页作品流（登录/游客顶栏、`onShow` 自动加载、下拉刷新与手动“刷新列表”按钮、空态卡片与错误提示条） | 提交 `e67be07`<br>`campus-album/backend/campus_album/posts_feed.py`<br>`campus-album/miniprogram/pages/index/{index.js,index.json,index.wxml,index.wxss}` | **已通过**：自动化测试验证空库 `{"posts":[]}`、同秒按 ID 倒序、已移除作品与已软删作者过滤；Flask 子进程重启前后首页接口返回完全一致作品；`py_compile`、`json.tool`、`node --check` 全部通过 |
| **江耿锐｜评论与评分** | 完成第 1 周前置设计文档：扩展 `comments` 与 `ratings` 表 DDL（`UNIQUE(post_id, user_id)` + `UPSERT` 保证同一用户改分不重复计数），定义 `GET /api/posts/<id>`、`POST /api/posts/<id>/comments`、`PUT /api/posts/<id>/rating` 契约，编写 `TC-CR-01`～`TC-CR-05`（含 `TC-CR-02` 改分数值演示 `4.0/1 → 4.5/2 → 3.5/2`）；产出中文详情页线框图与改分流程图 | 提交 `9f51da2`<br>`campus-album/docs/week1/comments_ratings_design.md`<br>`campus-album/docs/week1/assets/comments_ratings_wireframe.png` | **已通过**：DDL 已基于 `schema.sql` 约束核对且语法校验通过；1280×720 中文线框图经人工/视觉复检，PingFang SC 字体清晰无乱码无重叠，可直接复用于周报与 PPT |
| **张轩玮｜管理员 Web 后台** | 完成第 1 周前置设计文档：规划基于 Flask Jinja 的管理员登录/用户管理/内容管理页面及普通用户 `403` 越权拦截；梳理作品移除（`posts.status='removed'`）与用户软删+会话清空（`users.deleted_at` + 清 `sessions` 使旧 Token 立即 `401`）状态流转；交付「跨端移除一致性检查表」（首页列表、日期/标签检索、旧详情页 `404 POST_REMOVED` 三入口）与 `TC-AD-01`～`TC-AD-05`；产出管理员后台与跨端同步线框图 | 提交 `85683dd`<br>`campus-album/docs/week1/admin_web_design.md`<br>`campus-album/docs/week1/assets/admin_web_wireframe.png` | **已通过**：严格复用既有 `schema.sql` 字段定义，三入口跨端一致性与 5 组验收用例闭环完整；1280×720 中文线框图经视觉复检清晰无重叠，可直接复用于周报与 PPT |

---

## 2. 本地原子提交记录（`campus-album/kickoff`）

| Short SHA | 负责角色 / 范围 | 提交说明（Commit Message） |
|---|---|---|
| `7aa45c1` | 基线（Coursework Bootstrap） | `Bootstrap Campus Album coursework backend` |
| `97092aa` | 陈俊年｜账号与权限 | `feat(auth): implement register/login API and Mini Program login page` |
| `571428b` | 吕辉亮｜发布与作品维护 | `feat(publish): implement text post API and Mini Program publish page` |
| `e67be07` | 黄子特｜浏览与检索 | `feat(feed): implement visible post feed API and Mini Program home page` |
| `b340f75` | 李文俊｜架构与联调 | `feat(arch): add shared backend helpers, Mini Program shell, and integrate Week 1 blueprints` |
| `9f51da2` | 江耿锐｜评论与评分 | `docs(interact): add Week 1 comments/ratings design, re-rating cases, and wireframe` |
| `85683dd` | 张轩玮｜管理员 Web 后台 | `docs(admin): add Week 1 admin web design, cross-end removal checklist, and wireframe` |
| `b1aade5` | 测试与验收（QA Verification） | `test(week1): add Week 1 flow/restart persistence suite and verification report` |

> 注：本索引文件本身将紧随 `b1aade5` 提交至 `campus-album/kickoff` 分支，供第一周进度汇报 PPT 及后续迭代追溯引用。

---

## 3. 一键复现与验收核对命令

```sh
cd campus-album
# 1. 初始化数据库并启动本地 Flask 服务（默认端口 5001）
.venv/bin/python -m flask --app backend/campus_album init-db
.venv/bin/python -m flask --app backend/campus_album run --port 5001

# 2. 运行第一周自动化测试套件（11 项用例，含真实子进程重启持久化测试）
.venv/bin/python -m unittest discover -s tests -v
```

- 详细测试输出、重启前后逐字段 HTTP 抓包记录与小程序静态校验明细见 [`docs/week1/verification_report.md`](./verification_report.md)。
