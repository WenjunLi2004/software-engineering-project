# 校园影集

软件工程课程项目。微信小程序用于发布与浏览校园活动作品，管理员 Web 后台用于管理用户和内容。两个入口共用 Flask 后端和 SQLite 数据库。

第一周的联调目标是用小程序登录、发布一条文字作品，并在首页重新加载后看到它。当前基线提供 Flask 启动入口、健康检查及账号、会话、作品的初始表。下面的业务接口是供各模块并行开发的约定。

## 启动项目

在仓库根目录执行，创建 Python 3.10 或更新版本的虚拟环境。

### macOS / Linux

```sh
cd campus-album
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app backend/campus_album init-db
.venv/bin/python -m flask --app backend/campus_album run --port 5001
```

### Windows PowerShell

```powershell
cd campus-album
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app backend/campus_album init-db
.\.venv\Scripts\python.exe -m flask --app backend/campus_album run --port 5001
```

浏览器打开 [本地健康检查](http://127.0.0.1:5001/api/health)，看到 `{"status":"ok"}` 表示 Flask 可以响应请求。默认数据库在 `backend/instance/campus-album.sqlite3`，可重复运行 `init-db`，已有记录会保留。需要单独的测试文件时，通过环境变量 `CAMPUS_ALBUM_DATABASE` 指定路径。

[Flask 安装说明](https://flask.palletsprojects.com/en/stable/installation/) · [Flask SQLite 用法](https://flask.palletsprojects.com/en/stable/tutorial/database/)

## 第一周接口约定

请求和响应使用 JSON。小程序开发工具中的本地接口地址与本机 Flask 端口保持一致。前端使用下表的字段先做页面，联调时接实际后端。

| 方法和路径 | 请求 | 成功响应 |
|---|---|---|
| `GET /api/health` | 直接请求 | `200`，服务状态 |
| `POST /api/auth/register` | `username`、`password` | `201`，`user.id`、`user.username` |
| `POST /api/auth/login` | `username`、`password` | `200`，`token`、`user.id`、`user.username` |
| `POST /api/posts` | `text`，带登录令牌 | `201`，`post` |
| `GET /api/posts` | 直接请求 | `200`，`posts` 数组 |

登录令牌通过 `Authorization: Bearer <token>` 传递。后端从会话取得作者，存密码哈希和令牌摘要，并检查会话过期时间。普通账号注册使用 `user` 角色。

发布和列表使用同一种作品对象。示例里的账号和作品用于页面联调。

```json
{
  "id": 1,
  "text": "今天在校运会上认识了新朋友。",
  "author": {"id": 1, "username": "campus_demo"},
  "createdAt": "2026-11-20T12:30:00Z"
}
```

- 没有作品时返回 `{"posts":[]}`。作品流只返回可见作品，按创建时间倒序，同一时间按 ID 倒序。
- 用户名、密码必填。发布前去掉首尾空白，内容为空时返回 `400`。登录错误或发帖会话无效返回 `401`，重名注册返回 `409`。
- 统一错误格式为 `{"error":{"code":"INVALID_INPUT","message":"请输入作品内容"}}`。页面据此显示提示。
- 首周只处理文字作品。后续图片、视频和标签沿用同一个作品 ID。

## 首周联调验收

1. 在微信开发者工具中启动小程序，用测试账号完成登录。
2. 发布一条新文字，回到首页能看到正文、作者和时间。
3. 重启后端后重新进入首页，仍能看到刚发布的作品。
4. 用错误密码尝试登录，页面提示失败。提交空白正文时保留当前页并给出提示。

合并前提供复现命令和实际结果。保留一条可用于稍后文档的用户故事、页面行为和验收记录。
