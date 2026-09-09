# Fitness Copilot - 项目使用说明

## 项目结构

```
Fitness-Copilot/
├── pom.xml                 # Maven父项目配置
├── common/                 # 公共模块
│   ├── entity/            # 基础实体类
│   ├── result/            # 统一返回结果
│   └── enums/             # 枚举类
├── infrastructure/         # 基础设施模块
│   ├── config/            # DeepSeek和数据库配置
│   └── service/           # AI服务
├── user-service/          # 用户服务
│   ├── entity/            # 用户实体
│   ├── mapper/            # MyBatis Mapper
│   └── repository/        # 数据访问层
├── training-service/      # 训练服务
│   ├── entity/            # 训练实体（有氧/无氧）
│   ├── mapper/            # MyBatis Mapper
│   └── repository/        # 数据访问层
├── plan-service/          # 计划服务
│   ├── entity/            # 计划实体（周计划/日计划）
│   ├── mapper/            # MyBatis Mapper
│   └── repository/        # 数据访问层
├── nutrition-service/     # 营养服务
│   ├── entity/            # 营养实体
│   ├── mapper/            # MyBatis Mapper
│   └── repository/        # 数据访问层
├── database/              # 数据库脚本
│   ├── init.sql           # 旧版含示例数据的初始化脚本
│   └── migration/         # Flyway 版本化迁移脚本
└── config/                # 配置文件
    └── application.yml    # 主配置文件
```

## 技术栈

- **Java 17**
- **Spring Boot 3.2.0**
- **Spring Cloud 2023.0.0**
- **MyBatis Plus 3.5.5**
- **MySQL 8.0**
- **LangChain4j 0.27.0** (用于DeepSeek集成)
- **Lombok**
- **Hutool**

## 数据库初始化

### 1. 创建数据库并执行迁移

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fitness_copilot DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
.\mvnw.cmd flyway:migrate -Dflyway.url="jdbc:mysql://localhost:3306/fitness_copilot?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai" -Dflyway.user=root -Dflyway.password=your_password_here
```

### 2. 配置数据库连接

在项目根目录基于 `.env.example` 设置环境变量（或在部署系统中配置）：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/fitness_copilot?useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai
    username: root
    password: your_password_here  # 替换为你的MySQL密码
```

## DeepSeek配置

### 1. 获取API密钥

访问 [DeepSeek官网](https://www.deepseek.com/) 获取API密钥

### 2. 配置DeepSeek

修改 `config/application.yml` 文件：

```yaml
deepseek:
  api-key: your_deepseek_api_key_here  # 替换为你的API密钥
  base-url: https://api.deepseek.com
  model-name: deepseek-chat
  temperature: 0.7
  max-tokens: 2000
  timeout: 60
```

## 构建项目

```bash
# 编译所有模块
.\mvnw.cmd clean install

# 编译单个模块
.\mvnw.cmd clean install -pl user-service -am
```

## 数据表结构

### 用户表 (user_profile)
- 存储用户基本信息和身体数据
- 包含：年龄、性别、身高、体重、体脂率、BMI等

### 有氧训练表 (aerobic_training)
- 记录有氧运动数据
- 包含：跑步、游泳、骑行等
- 字段：时长、距离、心率、消耗热量

### 无氧训练表 (anaerobic_training)
- 记录力量训练数据
- 包含：深蹲、硬拉、卧推等
- 字段：组数、次数、重量、目标肌群

### 七天计划表 (weekly_plan)
- 存储周训练计划
- 包含：开始日期、结束日期、健身目标、整体策略

### 每天计划表 (daily_plan)
- 存储每日详细训练计划
- 包含：时间段、活动类型、强度、目标肌群

### 营养计划表 (nutrition_plan)
- 存储每日饮食计划
- 包含：总热量、蛋白质、碳水化合物、脂肪配比

### 食物摄入表 (food_intake)
- 记录实际食物摄入
- 包含：餐次、食物名称、份量、营养成分

## 下一步开发建议

1. **实现服务层**：为每个微服务添加Service层和Controller层
2. **添加API接口**：实现RESTful API
3. **集成测试**：编写单元测试和集成测试
4. **服务注册与发现**：集成Spring Cloud Eureka或Nacos
5. **配置中心**：使用Spring Cloud Config或Nacos配置中心
6. **API网关**：使用Spring Cloud Gateway
7. **多智能体集成**：集成LangGraph实现Agent协作

## 注意事项

- 所有实体类继承自 `BaseEntity`，包含通用字段（id、createTime、updateTime等）
- 使用MyBatis Plus的逻辑删除功能（deleted字段）
- 数据库使用utf8mb4字符集，支持emoji等特殊字符
- 各服务端口：user-service(8081)、training-service(8082)、plan-service(8083)、nutrition-service(8084)
