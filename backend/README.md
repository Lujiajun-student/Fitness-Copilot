# Java 后端

Java 8 + Spring Boot 2.7 的业务 API 工程。当前已实现账号密码注册、登录和 JWT 签发；后续将在此实现身体档案、训练记录、月度计划和饮食计划等领域接口。

```powershell
mvn spring-boot:run
```

健康检查：`GET http://localhost:8080/api/health`

## 认证接口

`POST /api/auth/register` 注册账号，成功后返回 JWT：

```json
{"account":"fitness_user","password":"strong-password-123"}
```

`POST /api/auth/login` 使用同一请求体登录。账号仅允许字母、数字、`_`、`-`，长度 3–50；密码长度为 8–72。

应用默认使用本地 H2 文件数据库（`backend/data/`）。部署前请设置至少 32 字符的 `APP_JWT_SECRET`，并在后续 MySQL 配置完成后替换开发数据库。

## 身体数据接口

每次录入都会在 `body_measurement` 表新增一条测量快照，不覆盖历史数据。字段包括身高、体重、胸围、腰围、臀围、可选体脂率，以及后端自动计算的 BMI。

`POST /api/body-measurements` 需携带 `Authorization: Bearer <token>`：

```json
{
  "heightCm": 175,
  "weightKg": 70,
  "chestCm": 96,
  "waistCm": 80,
  "hipCm": 94,
  "bodyFatPercent": 18.5
}
```

- `GET /api/body-measurements/latest`：获取当前用户最近一次测量。
- `GET /api/body-measurements`：按时间倒序获取当前用户全部测量记录。

## 训练与计划接口

- `POST /api/training-logs`、`GET /api/training-logs`：新增/查询当前用户最近 30 条训练日志。
- `POST /api/plans/monthly`：保存月度训练计划 JSON。
- `POST /api/plans/nutrition-daily`：保存某日饮食计划 JSON。

这组接口由 Agent 服务的 MCP 工具调用，均需要 JWT。

## 个人资料接口

- `GET /api/users/me`：获取当前账户的账号、简介和头像。
- `PATCH /api/users/me`：修改账号、简介、头像（Data URL）或密码；都需要携带 JWT。请求中的字段均可选：`account`、`bio`、`avatarDataUrl`、`newPassword`。
