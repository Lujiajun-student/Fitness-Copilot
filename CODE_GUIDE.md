# Fitness Copilot 源码文件与方法说明

> 本文覆盖仓库中业务源码（Java、Python、Vue/JavaScript）及主要配置/知识文件；`node_modules`、构建产物和锁文件不属于业务源码，未逐项列出。Java DTO/实体中的 getter/setter 统一按属性访问器说明，避免对同一字段的读写方法重复描述。

## 1. 项目根目录

| 文件 | 用处 |
| --- | --- |
| `README.md` | 项目总览、启动方式和模块说明。 |
| `PROJECT_SETUP.md` | 本地环境配置与联调说明。 |
| `backend/pom.xml` | Java/Spring Boot 的依赖、插件和构建配置。 |
| `backend/README.md` | Java 后端的单独说明。 |
| `frontend/package.json` | Vue 前端的脚本和 npm 依赖声明。 |
| `frontend/babel.config.js` | Babel 编译配置。 |
| `frontend/vue.config.js` | Vue CLI 开发服务器/代理等配置。 |
| `frontend/public/index.html` | Vue 单页应用挂载的 HTML 壳。 |
| `backend/src/main/resources/application.yml` | 后端端口、数据库、JWT 等运行配置。 |
| `agent-service/.env.example` | DeepSeek、后端地址等环境变量模板，不放真实密钥。 |
| `agent-service/requirements.txt` | Python Agent 服务所需依赖。 |
| `agent-service/README.md` | Agent 服务、MCP 与 LangGraph 工作流说明。 |

前端样式文件 `frontend/src/assets/styles.css`、`dashboard.css`、`profile.css` 只定义页面视觉样式，不包含业务方法。`backend/src/test/.../AuthControllerTest.java` 是认证接口测试，`backend/src/test/resources/application.yml` 是测试环境配置。

---

## 2. Python Agent 服务（`agent-service/app`）

### `__init__.py`

包标记文件，使 `app` 可以作为 Python 包被导入；不包含业务方法。

### `config.py`：运行配置

| 类/方法 | 用处 |
| --- | --- |
| `DeepSeekConfigurationError` | 未配置 DeepSeek API Key 时抛出的专用异常，便于 API 层返回可读错误。 |
| `Settings` | 不可变配置对象，保存 API Key、DeepSeek 地址、模型名和温度。 |
| `Settings.deepseek_configured` | 属性方法；判断 API Key 是否非空。 |
| `get_settings()` | 从 `.env`/环境变量读取配置，填充默认 DeepSeek 地址、模型 `deepseek-chat` 和温度 `0.2`。 |

### `deepseek_client.py`：模型调用适配器

| 类/方法 | 用处 |
| --- | --- |
| `DeepSeekClient.__init__(settings=None)` | 注入测试配置或加载默认配置。 |
| `DeepSeekClient.json_completion(system_prompt, payload)` | 异步调用 DeepSeek Chat Completions：检查密钥、要求 JSON 对象响应、发送系统提示词和上下文、解析返回 JSON；HTTP 错误或非法 JSON 会转成 `RuntimeError`。 |

### `prompts.py`：Agent 系统提示词

| 常量 | 用处 |
| --- | --- |
| `PLANNER_PROMPT` | 约束总规划 Agent 生成恰好 30 天的结构化训练计划，并吸收安全整改意见。 |
| `STRENGTH_PROMPT` | 约束力量 Agent 只提出需要调整日期的力量训练修订。 |
| `ENDURANCE_PROMPT` | 约束体能 Agent 优化有氧、恢复及低冲击安排。 |
| `HARNESS_PROMPT` | 约束安全审核 Agent 输出批准结果、风险及强制整改项。 |
| `NUTRITION_PROMPT` | 约束营养 Agent 生成完整 30 天、每天三餐的饮食计划。 |

### `rag.py`：本地隔离知识库检索

| 类/方法 | 用处 |
| --- | --- |
| `KNOWLEDGE_ROOT` | 指向 `agent-service/knowledge` 根目录。 |
| `ALLOWED_KNOWLEDGE_BASES` | 允许访问的三类知识库：`strength`、`endurance`、`nutrition`。 |
| `_terms(text)` | 把英文数字词和中文双字切分为检索词集合，用于简单词法匹配。 |
| `retrieve_agent_knowledge(agent, query, limit=3)` | 校验 Agent 权限后，只扫描其专属目录；按查询词重合度排序，返回最多 5 个截断后的知识片段。 |

### `mcp_server.py`：MCP 工具服务

| 方法 | 用处 |
| --- | --- |
| `backend_get(path, access_token)` | 带 Bearer Token 调用 Java 后端 GET 接口；处理空响应并解析 JSON。 |
| `backend_post(path, access_token, payload)` | 带认证调用 Java 后端 POST 接口并解析 JSON。 |
| `get_current_user(access_token)` | MCP 工具：读取当前用户档案 `/api/users/me`。 |
| `get_latest_body_measurement(access_token)` | MCP 工具：读取最新身体测量数据。 |
| `get_training_history(access_token)` | MCP 工具：读取近期训练日志。 |
| `calculate_training_load(duration_minutes, perceived_exertion, average_heart_rate=None)` | MCP 工具：以“时长 × RPE”计算透明训练负荷；高心率会标记为高强度。 |
| `calculate_calorie_target(weight_kg, goal, activity_multiplier=30)` | MCP 工具：保守估算维持/目标热量和蛋白质目标。 |
| `search_food_nutrition(query)` | MCP 工具：检索内置的小型食物营养种子库。 |
| `retrieve_agent_knowledge_base(agent, query, limit=3)` | MCP 工具：调用本地 RAG，且限制 Agent 只能访问自己的知识库。 |
| `validate_plan_safety(days, bmi=None)` | MCP 工具：用确定性规则检测连续三天力量训练及高 BMI 下跳跃/冲刺风险。 |
| `save_monthly_plan(access_token, goal, content)` | MCP 工具：把已批准的月度训练计划写入 Java 后端。 |
| `save_daily_nutrition_plan(access_token, plan_date, content)` | MCP 工具：把单日营养计划写入 Java 后端。 |

文件末尾的 `mcp.run(transport="stdio")` 是脚本入口：将工具以标准输入输出的 MCP Server 方式运行。

### `mcp_client.py`：MCP 客户端

| 类/方法 | 用处 |
| --- | --- |
| `BackendMcpClient.load_user_context(access_token)` | 启动本地 MCP Server，并发调用用户档案、身体测量和训练历史三个读取工具，汇总为 LangGraph 初始上下文。 |
| `BackendMcpClient._json_content(result)` | 静态辅助方法；识别 MCP 工具错误并从工具返回内容解析 JSON。 |
| `AgentRagMcpClient.retrieve(agent, query, limit=3)` | 启动 MCP Server 并调用隔离 RAG 工具，为专项 Agent 获取参考知识。 |

### `workflow.py`：LangGraph 编排核心

`PlanState` 是跨节点共享状态，包含用户目标/资料/历史、30 天训练计划、力量与体能修订、安全结果、协商轮数和饮食计划。

| 方法 | 用处 |
| --- | --- |
| `_context(state)` | 从完整状态中提取每个 Agent 都需要的用户目标、身体数据、档案、历史和 Harness 反馈。 |
| `_rag_query(state, focus)` | 将目标、训练经验、伤病、忌口和器械等拼成 RAG 查询语句。 |
| `_apply_revisions(plan, proposal)` | 深拷贝计划，并按 `day` 用 Agent 输出的 `revisions` 替换当天训练动作。 |
| `_start_minutes(profile)` | 从用户可训练时段提取第一个 `HH:MM`；缺失时使用 09:00。 |
| `_duration_minutes(session)` | 优先使用模型提供的时长；缺失时按热身、有氧、恢复、核心或组数推断安全默认时长。 |
| `_time_label(minutes)` | 将分钟数格式化为 `HH:MM`。 |
| `_schedule_plan(plan, profile)` | 对每天训练动作顺序排程，重写 `durationMinutes` 与 `timeRange`，避免模型返回的时间段重叠。 |
| `_validate_plan(plan)` | 确定性校验：计划必须覆盖 30 天，且每一天必须有训练/恢复活动。 |
| `build_graph(client=None, rag_client=None)` | 构建并编译 LangGraph；允许注入模型/RAG 客户端，便于测试。 |
| `planner_node(state)` | 调用总规划 Agent，校验 `monthly_plan`，完成初步排程并重置协商轮数。 |
| `strength_node(state)` | 检索力量知识库，结合体能上一轮建议，生成力量训练局部修订并重新排程。 |
| `endurance_node(state)` | 检索体能知识库，结合力量建议，生成有氧/恢复局部修订，协商轮数加一。 |
| `harness_node(state)` | 调用安全 Agent，合并模型风险和代码校验风险，给出审批结果与整改反馈。 |
| `nutrition_node(state)` | 检索营养知识库，调用营养 Agent 并确保返回完整 30 天饮食计划。 |
| `debate_route(state)` | 条件路由：协商少于两轮回到力量节点，否则进入安全审核。 |
| `harness_route(state)` | 条件路由：审核通过进入营养；未通过但整改不超过两次回总规划；否则失败。 |
| `failed_node(state)` | 提取安全风险/整改意见并抛出终止异常，拒绝输出不安全计划。 |
| `plan_graph` | 模块加载时通过 `build_graph()` 创建的已编译工作流实例。 |

### `main.py`：FastAPI 接口层

| 类/方法 | 用处 |
| --- | --- |
| `PlanRequest` | 请求体 Schema，要求 `goal` 非空。 |
| `sse(event_type, payload)` | 将事件名和 JSON 数据格式化为 SSE 文本。 |
| `build_plan_document(goal, state)` | 将训练和饮食结果按日期合并为最终计划文档；校验每天都有三餐且总天数为 30。 |
| `build_generation_response(goal, profile, state)` | 封装统一响应：状态、用户档案和计划文档。 |
| `missing_safety_profile_fields(profile)` | 找出生成前尚未填写的训练/健康安全字段。 |
| `health()` | `GET /api/health`：返回 Agent 服务状态、模型名与是否配置密钥。 |
| `generate_monthly_plan(request, authorization)` | `POST /api/v1/plans/generate`：校验认证和资料，读取 MCP 上下文，执行整个 LangGraph 后返回结果。 |
| `generate_monthly_plan_stream(request, authorization)` | `POST /api/v1/plans/generate/stream`：以 SSE 执行同样的工作流，逐节点发送进度、错误或最终计划。 |
| `events()` | 嵌套异步生成器；由流式接口使用，负责发出 profile/planner/strength/endurance/harness/nutrition 等阶段事件。 |

### `knowledge/*/*.md`：RAG 知识文件

| 文件 | 用处 |
| --- | --- |
| `knowledge/strength/safe_strength_design.md` | 力量训练 Agent 的安全设计依据。 |
| `knowledge/endurance/cardio_recovery_design.md` | 有氧与恢复 Agent 的参考依据。 |
| `knowledge/nutrition/meal_planning_safety.md` | 营养 Agent 的三餐与安全限制参考。 |

---

## 3. Java 后端（`backend/src/main/java`）

后端已按三层架构重组：`controller/` 仅处理 HTTP、认证信息和请求/响应；`service/` 承载业务规则与事务；`mapper/` 负责 JPA 数据访问。领域实体统一在 `entity/`，请求与响应 DTO 统一在 `dto/`。以下按功能说明这些分层文件中的类型。

### 启动与配置

| 文件 | 方法 | 用处 |
| --- | --- | --- |
| `FitnessCopilotApplication.java` | `main(args)` | Spring Boot 启动入口，创建应用上下文并启动 Web 服务。 |
| `config/AuthConfiguration.java` | `passwordEncoder()` | 注册 BCrypt `PasswordEncoder` Bean，供注册、登录和改密使用。 |
| `controller/HealthController.java` | `health()` | `GET /api/health`，返回 `{status: "ok"}` 供健康探针调用。 |

### 认证相关类型

| 文件 | 类/方法 | 用处 |
| --- | --- | --- |
| `AuthController.java` | `AuthController(authService)` | 注入认证服务。 |
|  | `register(request)` | `POST /api/auth/register`：校验注册请求并创建账户，返回 Token。 |
|  | `login(request)` | `POST /api/auth/login`：校验登录请求并返回 Token。 |
| `AuthService.java` | `AuthService(userMapper, passwordEncoder, jwtService)` | 注入用户 Mapper、密码加密器和 JWT 服务。 |
|  | `register(request)` | 去除账号空白、检查账号重复、BCrypt 加密密码、保存用户并签发登录响应。 |
|  | `login(request)` | 根据账号查询用户、比对密码哈希，成功后签发登录响应。 |
|  | `responseFor(user)` | 私有方法；把用户 ID、账号和新 JWT 组装为 `AuthResponse`。 |
| `JwtService.java` | `JwtService(secret, expirationSeconds)` | 从配置生成 HMAC 签名密钥和 Token 有效期。 |
|  | `createToken(userId, account)` | 创建含账号、用户 ID、签发时间和过期时间的 HS256 JWT。 |
|  | `extractUserId(authorizationHeader)` | 校验 Bearer Header、解析签名和过期状态，并返回 JWT 内的用户 ID；无效则返回 401。 |
| `AuthResponse.java` | `AuthResponse(userId, account, token)` | 构造认证响应。 |
|  | `getUserId()` / `getAccount()` / `getToken()` / `getTokenType()` | 返回用户标识、账号、JWT 和固定的 `Bearer` 类型。 |
| `LoginRequest.java` | `getAccount()` / `setAccount()` | 读取/设置登录账号。 |
|  | `getPassword()` / `setPassword()` | 读取/设置登录密码。 |
| `RegisterRequest.java` | `getAccount()` / `setAccount()` | 读取/设置注册账号；字段注解限制长度和字符集。 |
|  | `getPassword()` / `setPassword()` | 读取/设置注册密码；字段注解限制长度。 |

### 用户与训练安全档案相关类型

| 文件 | 类/方法 | 用处 |
| --- | --- | --- |
| `AppUser.java` | `AppUser()` | JPA 使用的受保护无参构造器。 |
|  | `AppUser(account, passwordHash)` | 创建新用户实体。 |
|  | `beforeCreate()` | JPA `@PrePersist` 回调，写入创建时间。 |
|  | `getId()`、`getAccount()`、`getPasswordHash()`、`getBio()`、`getAvatarDataUrl()`、`getCreatedAt()` | 返回账户基础字段。 |
|  | `getTrainingExperience()`、`getWeeklyTrainingDays()`、`getSessionDurationMinutes()`、`getAvailableTrainingTimes()`、`getAvailableEquipment()`、`getInjuryOrMedicalNotes()`、`getAverageSleepHours()`、`getDietaryRestrictions()` | 返回供 Agent 安全规划使用的训练与健康档案字段。 |
|  | `updateProfile(account, bio, avatarDataUrl)` | 更新账号、个人简介和头像。 |
|  | `updateSafetyProfile(...)` | 更新训练经验、可训练时间、器械、伤病、睡眠和饮食限制。 |
|  | `changePassword(passwordHash)` | 更新已加密的新密码。 |
| `UserMapper.java` | `findByAccount(account)` | 按账号查找用户。 |
|  | `existsByAccount(account)` | 判断账号是否已存在。 |
| `UserProfileController.java` | `UserProfileController(service, jwtService)` | 注入个人资料服务与 JWT 服务。 |
|  | `get(authorization)` | `GET /api/users/me`：从 Token 获取当前用户并返回档案。 |
|  | `update(authorization, request)` | `PATCH /api/users/me`：更新当前用户档案。 |
| `UserProfileService.java` | `UserProfileService(userMapper, passwordEncoder)` | 注入用户 Mapper 与密码加密器。 |
|  | `get(userId)` | 找到用户并转换为对外的资料响应。 |
|  | `update(userId, request)` | 合并非空字段、检查改名冲突、更新安全档案；有新密码时加密后保存。 |
|  | `findUser(userId)` | 私有方法；按 ID 查用户，不存在时抛出 404。 |
| `UserProfileRequest.java` | `getXxx()` / `setXxx()`（`account`、`bio`、`avatarDataUrl`、`newPassword`） | 读取/设置基础资料更新字段。 |
|  | `getXxx()` / `setXxx()`（训练经验、训练天数、训练时长、时段、器械、伤病、睡眠、忌口） | 读取/设置安全档案字段；字段注解负责范围和长度校验。 |
| `UserProfileResponse.java` | `UserProfileResponse(user)` | 将用户实体映射为不含密码的响应 DTO。 |
|  | 全部 `getXxx()` | 返回基础资料与安全档案字段给前端和 MCP。 |

### 身体测量相关类型

| 文件 | 类/方法 | 用处 |
| --- | --- | --- |
| `BodyMeasurement.java` | `BodyMeasurement()` | JPA 使用的无参构造器。 |
|  | `BodyMeasurement(userId, heightCm, weightKg, chestCm, waistCm, hipCm, bodyFatPercent, bmi)` | 创建一条身体测量实体。 |
|  | `setRecordedAt()` | JPA `@PrePersist` 回调，记录测量创建时间。 |
|  | `getId()`、`getUserId()`、`getHeightCm()`、`getWeightKg()`、`getChestCm()`、`getWaistCm()`、`getHipCm()`、`getBodyFatPercent()`、`getBmi()`、`getRecordedAt()` | 返回测量实体各字段。 |
| `BodyMeasurementMapper.java` | `findFirstByUserIdOrderByRecordedAtDesc(userId)` | 找到用户最新一条测量记录。 |
|  | `findByUserIdOrderByRecordedAtDesc(userId)` | 按时间倒序获取用户全部测量记录。 |
| `BodyMeasurementService.java` | `BodyMeasurementService(bodyMeasurementMapper)` | 注入测量 Mapper。 |
|  | `create(userId, request)` | 将厘米换算成米，计算 BMI，保存测量记录并返回 DTO。 |
|  | `getLatest(userId)` | 返回最新测量；没有记录时返回 `null`。 |
|  | `list(userId)` | 查询并映射用户的测量历史。 |
| `BodyMeasurementController.java` | `BodyMeasurementController(service, jwtService)` | 注入服务与 JWT 工具。 |
|  | `create(authorization, request)` | `POST /api/body-measurements`：保存当前用户测量数据。 |
|  | `latest(authorization)` | `GET /api/body-measurements/latest`：返回当前用户最新测量。 |
|  | `list(authorization)` | `GET /api/body-measurements`：返回当前用户测量历史。 |
| `BodyMeasurementRequest.java` | 各字段 `getXxx()` / `setXxx()` | 读取/设置身高、体重、围度和体脂率；注解校验合法范围。 |
| `BodyMeasurementResponse.java` | `BodyMeasurementResponse(measurement)` | 将实体转为 API 响应 DTO。 |
|  | 各字段 `getXxx()` | 返回测量 ID、体格指标、BMI 与记录时间。 |

### 训练日志相关类型

| 文件 | 类/方法 | 用处 |
| --- | --- | --- |
| `TrainingLog.java` | `TrainingLog()` | JPA 无参构造器。 |
|  | `TrainingLog(userId, request)` | 从请求创建训练记录；没有完成时间时使用当前时间。 |
|  | 各字段 `getXxx()` | 返回训练类别、动作、时长、组次、负重、距离、心率、RPE 和完成时间。 |
| `TrainingLogRequest.java` | 各字段 `getXxx()` / `setXxx()` | 读取/设置训练日志输入；注解限定类别为 `strength/cardio/recovery` 并校验数值范围。 |
| `TrainingLogMapper.java` | `findTop30ByUserIdOrderByCompletedAtDesc(userId)` | 查询用户最近 30 条日志，供 MCP 和 Agent 使用。 |
| `TrainingLogService.java` | `create(userId, request)` | 创建并通过 Mapper 保存训练日志。 |
|  | `listRecent(userId)` | 查询用户最近 30 条训练日志。 |
| `TrainingLogController.java` | `TrainingLogController(trainingLogService, jwt)` | 注入日志服务与 JWT 服务。 |
|  | `create(auth, request)` | `POST /api/training-logs`：保存当前用户训练记录。 |
|  | `list(auth)` | `GET /api/training-logs`：返回当前用户最近 30 条记录。 |

### 计划持久化相关类型

| 文件 | 类/方法 | 用处 |
| --- | --- | --- |
| `PlanDocument.java` | `PlanDocument()` | JPA 无参构造器。 |
|  | `PlanDocument(userId, documentType, goal, planDate, contentJson)` | 创建计划文档；保存创建时间。 |
|  | `getId()`、`getDocumentType()`、`getGoal()`、`getPlanDate()`、`getContentJson()`、`getCreatedAt()` | 返回计划元数据和 JSON 字符串内容。 |
| `PlanDocumentMapper.java` | `findFirstByUserIdAndDocumentTypeOrderByCreatedAtDesc(userId, documentType)` | 获取指定类型最新计划。 |
|  | `deleteByUserIdAndDocumentType(userId, documentType)` | 删除某用户某类型的已有计划，用于月度计划覆盖。 |
| `PlanDocumentRequest.java` | `getGoal()` / `setGoal()` | 读取/设置计划目标。 |
|  | `getPlanDate()` / `setPlanDate()` | 读取/设置计划开始日期。 |
|  | `getContent()` / `setContent()` | 读取/设置必须存在的 JSON 计划正文。 |
| `PlanDocumentService.java` | `replaceMonthly(userId, request)` | 在事务内删除旧月计划并保存新计划。 |
|  | `getLatestMonthly(userId)` | 获取最新月计划并将 JSON 文本还原为响应对象。 |
|  | `saveDailyNutrition(userId, request)` | 保存每日营养计划。 |
|  | `save(...)` / `toResponse(...)` | 私有方法；分别负责序列化持久化与反序列化响应。 |
| `PlanDocumentController.java` | `PlanDocumentController(planDocumentService, jwt)` | 注入计划服务与 JWT 服务。 |
|  | `saveMonthly(auth, request)` | `POST /api/plans/monthly`：删除旧月计划后保存新计划，确保一个用户只有当前月计划。 |
|  | `latestMonthly(auth)` | `GET /api/plans/monthly/latest`：返回最近月计划；无计划时返回 204。 |
|  | `saveNutrition(auth, request)` | `POST /api/plans/nutrition-daily`：保存一份每日营养计划。 |

---

## 4. Vue 前端（`frontend/src`）

### 启动与路由

| 文件 | 方法/对象 | 用处 |
| --- | --- | --- |
| `main.js` | `new Vue(...).$mount("#app")` | 创建 Vue 根实例，注册路由和全局样式。 |
| `router/index.js` | `router.beforeEach(to, from, next)` | 全局路由守卫：未登录访问私有页跳登录；已登录访问登录页跳首页。 |
| `router/index.js` | `router` | 定义登录、仪表盘、AI 助理和个人信息四个 hash 路由。 |

### API 与本地状态

| 文件 | 方法/对象 | 用处 |
| --- | --- | --- |
| `api/session.js` | `session` | Vue 响应式会话对象，保存 Token、用户 ID、账号和展示资料。 |
|  | `setSession(data)` | 更新会话对象并写入浏览器 `localStorage`。 |
|  | `clearSession()` | 清空内存与本地存储中的登录状态。 |
| `api/http.js` | `apiRequest(path, options)` | Java 后端的统一 Fetch 包装：自动加 JSON 头和 JWT；401 时自动退出；统一解析错误。 |
| `api/fitness.js` | `authApi.login(data)` / `authApi.register(data)` | 调用注册、登录 API。 |
|  | `profileApi.get()` / `profileApi.update(data)` | 获取或更新当前用户资料。 |
|  | `bodyApi.latest()` / `bodyApi.create(data)` | 获取最新身体数据或新增测量记录。 |
|  | `planApi.latestMonthly()` / `planApi.replaceMonthly(plan)` | 读取最新月计划，或将新计划覆盖保存至后端。 |
| `api/plan-store.js` | `storageKey()` | 按登录用户生成当前计划的本地缓存 Key。 |
|  | `read()` | 从 `localStorage` 恢复计划；解析失败时返回 `null`。 |
|  | `activePlan` | Vue 响应式的当前计划容器。 |
|  | `setActivePlan(plan)` | 更新内存计划并写入本地缓存。 |
| `api/agent.js` | `generatePlan(goal, onEvent)` | 调 Agent 服务的 SSE 接口，增量解析事件：将 `stage` 回调给 UI，收到 `result` 后返回计划，收到 `error` 则抛错。 |

### `App.vue`：应用外壳

| 位置 | 方法 | 用处 |
| --- | --- | --- |
| computed | `pageTitle()` | 根据当前路由元数据显示页面标题。 |
| computed | `isAuthenticated()` | 根据 Token 决定展示应用壳还是仅展示登录页。 |
| computed | `accountInitial()` | 获取账号首字符作为默认头像文字。 |
| computed | `avatarStyle()` | 有头像 Data URL 时生成背景图样式。 |
| methods | `goToProfile()` | 关闭账户菜单并跳转个人信息页。 |
| methods | `logout()` | 清空会话并跳转登录页。 |

### `views/LoginView.vue`：注册与登录

| 位置 | 方法 | 用处 |
| --- | --- | --- |
| methods | `submit()` | 根据注册/登录模式调用认证 API；保存会话、加载展示资料，成功后进入首页；失败时展示错误。 |

### `views/ProfileView.vue`：个人档案和身体数据

| 位置 | 方法 | 用处 |
| --- | --- | --- |
| computed | `avatarStyle()` | 为头像预览生成背景图样式。 |
| lifecycle | `created()` | 页面创建后调用 `load()`。 |
| methods | `load()` | 并按顺序读取用户资料和最新身体测量，填充账户、安全档案和身体表单，同时同步会话展示信息。 |
| methods | `previewAvatar(event)` | 使用 `FileReader` 将用户选择的图片转为 Data URL，供本地预览和提交。 |
| methods | `save()` | 更新个人和安全档案，随后新增身体测量记录；成功显示短暂“已保存”反馈。 |

### `views/AssistantView.vue`：AI 计划生成页面

| 位置 | 方法 | 用处 |
| --- | --- | --- |
| computed | `firstDay()` | 安全获取生成计划的第一天，用于页面预览。 |
| methods | `send()` | 校验目标，调用流式 Agent 接口，更新本地计划，并尝试将月计划保存到 Java 后端；无论成功失败都会恢复加载状态。 |
| methods | `updateStage(event)` | 根据 SSE 阶段事件更新步骤文案和 pending/active/done 状态。 |

### `views/DashboardView.vue`：日历和当天计划

| 位置 | 方法 | 用处 |
| --- | --- | --- |
| 模块函数 | `dateKey(year, month, day)` | 格式化日期为 `YYYY-MM-DD`。 |
| 模块函数 | `parseDate(value)` | 将 `YYYY-MM-DD` 解析为本地 `Date`。 |
| computed | `monthLabel()` | 生成年月标题。 |
| computed | `calendarCells()` | 生成日历空白格和当月日期格。 |
| computed | `selectedDateLabel()` | 格式化当前选中日期的中文显示文本。 |
| computed | `dayPlan()` | 根据计划开始日和选中日期计算偏移量，取出对应计划日。 |
| lifecycle | `created()` | 页面创建后加载服务器上的计划。 |
| methods | `loadPlan()` | 尝试从 Java 后端获取最新计划；失败时继续使用本地缓存。 |
| methods | `moveMonth(step)` | 前进或后退一个月。 |
| methods | `selectDate(value)` | 选择有效的日历日期。 |
| methods | `hasPlan(value)` | 判断日期是否落在当前计划天数范围内。 |
| methods | `exerciseDetail(exercise)` | 组合次数、组间休息和备注，得到动作详情文本。 |
| methods | `exerciseDuration(exercise)` | 读取或按动作类别/组数推断时长，与 Agent 服务的排程逻辑保持兼容。 |
| methods | `exerciseTime(exercises, index)` | 从第一个动作开始时间逐项累加，计算指定动作的显示时间段。 |

---

## 5. 关键链路速览

```text
LoginView / ProfileView
        │ Java API + JWT
        ▼
AssistantView ──SSE──> FastAPI main.py
                         │ MCP 读取 Java 用户资料、测量和训练历史
                         ▼
              LangGraph: Planner → Strength ↔ Endurance → Harness → Nutrition
                         │
                         ▼
                 返回 30 天训练与三餐计划
                         │
                         ├─ plan-store.js（本地缓存）
                         └─ PlanDocumentController（保存当前月计划）
```
