# AI Poster MVP 技术方案

## 1. 目标与边界

### 1.1 MVP 目标

构建一个面向 `AI 科技` 赛道的全自动内容生产系统，每天自动完成以下链路：

1. 拉取过去 `24` 小时的行业重大事件。
2. 对候选事件做去重、聚类、排序、选题。
3. 补充背景资料并生成分析结论。
4. 自动生成 `公众号长文` 和 `小红书短帖` 两版内容。
5. 自动完成事实校验、内容 review、质量打分。
6. 仅在通过质量闸门后输出最终稿件。

### 1.2 MVP 不做

- 不做自动发布到公众号和小红书。
- 不做财经赛道正式支持。
- 不做复杂运营后台。
- 不做“开放式通用 Agent 平台”。

### 1.3 技术原则

- `Deterministic Pipeline > Freeform Agent`：MVP 优先可控流水线，不优先追求开放式多智能体。
- `Same Fact Base`：长文和短帖必须共享同一事实底座，禁止事实漂移。
- `Rule First`：质量放行不能只依赖模型主观判断，必须有硬规则。
- `Full Traceability`：每一步输入、输出、评分、来源、提示词版本都可追溯。
- `Fail Closed`：校验失败时直接废弃，不强行产出。

## 2. 总体架构

```text
+--------------------+
| Scheduler          |
| Cron / Manual Run  |
+---------+----------+
          |
          v
+--------------------+      +----------------------+
| Workflow Engine    |----->| Admin API / Console  |
| Job / Retry / DAG  |      | Run status / replay  |
+---------+----------+      +----------------------+
          |
          v
+--------------------+
| News Ingestion     |
| RSS / Site Adapter |
+---------+----------+
          |
          v
+--------------------+
| Extraction & Clean |
| Parse / Normalize  |
+---------+----------+
          |
          v
+--------------------+
| Event Engine       |
| Dedup / Cluster    |
| Rank / Select      |
+---------+----------+
          |
          v
+--------------------+
| Research Service   |
| Context / Sources  |
+---------+----------+
          |
          v
+--------------------+
| Writing Service    |
| Long + Short Draft |
+---------+----------+
          |
          v
+--------------------+
| QA Service         |
| Claim Check        |
| Review / Scoring   |
+---------+----------+
          |
          v
+--------------------+
| Export Service     |
| Markdown / JSON    |
+--------------------+

Storage:
- PostgreSQL: structured metadata and run states
- Object Storage or local files: raw html, extracted text, artifacts
- Redis: queue, cache, locks
```

## 3. 模块拆解

### 3.1 Scheduler / Workflow Engine

职责：

- 每日定时触发主流程。
- 支持手动重跑某一天或某个选题。
- 管理任务重试、超时、并发限制、失败回滚。

建议：

- MVP 用 `Celery + Redis` 做异步任务和重试。
- 用单独的 `orchestrator` 服务编排任务状态，不把复杂流程直接写死在单个 worker 中。

原因：

- 这个项目本质上是一个有状态、可重试、可审计的批处理系统。
- 直接把所有逻辑堆在脚本里，后续很难定位“为什么某篇稿子被放行”。

### 3.2 News Ingestion

职责：

- 从固定高质量新闻源抓取候选内容。
- 支持两类来源：
  - 一级来源：公司博客、官方公告、官方 X/公众号/开发者博客。
  - 二级来源：科技媒体、产业媒体、聚合站。

输入：

- source 配置
- 抓取时间窗口，默认最近 `24` 小时

输出：

- `raw_documents`

建议来源策略：

- MVP 先接 `20-40` 个高质量来源，不要一开始追求覆盖面。
- 优先 RSS 和公开页面，减少对动态页面和登录态的依赖。
- 对必须渲染的页面再用浏览器抓取。

### 3.3 Extraction & Normalization

职责：

- 拉取页面正文。
- 提取标题、发布时间、作者、正文、canonical url。
- 清洗广告、导航、脚注、重复段落。
- 标准化时间、公司名、产品名、标签。

关键输出字段：

- `document_id`
- `source_id`
- `url`
- `canonical_url`
- `published_at`
- `title`
- `clean_text`
- `language`
- `entities`
- `source_type`

实现要求：

- 同时保留 `raw_html` 和 `clean_text`。
- 对正文提取失败的页面做降级标记，不进入主流程。

### 3.4 Event Engine

职责：

- 对文章做去重、聚类、候选事件合并、打分、选题。

拆分为四步：

1. `Dedup`
   - 基于 `canonical_url`、标题哈希、正文向量相似度去重。
2. `Cluster`
   - 将同一事件的多个来源聚成一个 `event_cluster`。
3. `Rank`
   - 对事件做重要性评分。
4. `Select`
   - 选出当天值得写的 `1-3` 个主题。

建议评分维度：

- `freshness`
- `source_authority`
- `company_importance`
- `technical_novelty`
- `business_impact`
- `debate_potential`
- `china_audience_relevance`

评分实现：

- 第一层用规则和特征打分。
- 第二层再用 LLM 做“是否值得深写”的补充判断。

不要反过来做。纯 LLM 选题会漂。

### 3.5 Research Service

职责：

- 给每个入选事件构建 `research_packet`，作为后续写作和校验的唯一事实底座。

内容包括：

- 事件摘要
- 一级来源摘要
- 关键时间线
- 相关公司/产品背景
- 历史相似事件
- 竞品或对照组
- 争议点和不确定点
- 明确不能下结论的地方

关键原则：

- Writer 不能直接自由联网找资料。
- Writer 只能消费 `research_packet`。
- 所有结论都要尽量能回指到来源片段。

### 3.6 Writing Service

职责：

- 基于同一个 `research_packet` 生成双版本内容。

生成顺序建议：

1. 先生成 `outline`
2. 再生成 `公众号长文`
3. 再从同一 `outline + claims` 压缩生成 `小红书短帖`

这样做的原因：

- 长短版本共享观点骨架，能减少内容冲突。
- 小红书短帖不应该是对长文的机械截断，而是同结论下的再表达。

长文结构建议：

- 标题
- 导语结论
- 事件发生了什么
- 为什么这次重要
- 对行业格局意味着什么
- 争议和风险
- 结尾判断

短帖结构建议：

- 结论先行标题
- 一句话概述
- 2-4 个核心信息点
- 一个判断句

生成要求：

- 输出必须是结构化 JSON，再渲染成 Markdown。
- 不能让模型直接输出“自由格式最终文案”作为唯一结果。

### 3.7 QA Service

QA 必须拆成三个独立子模块，不要只有一个“review agent”。

#### A. Claim Extraction

从草稿中抽取可验证断言，例如：

- 公司发布了什么
- 参数、价格、融资金额、日期
- 谁说了什么
- 因果判断中的事实前提

输出：

- `claims[]`

#### B. Fact Verification

对每条 claim 在 `research_packet` 的来源片段中检索证据，判断：

- `supported`
- `partially_supported`
- `unsupported`
- `conflicting`

硬规则：

- 只要存在 `unsupported` 或 `conflicting` 的高风险 claim，直接失败。

#### C. Editorial Review

审查：

- 逻辑是否完整
- 观点是否明确
- 是否有空话和套话
- 长文与短帖是否事实一致
- 是否符合平台表达习惯

### 3.8 Quality Gate

质量闸门不是“一个分数”，而是一组放行规则。

放行条件建议：

1. 来源校验通过。
2. 时间窗口正确。
3. Claim 校验无高风险失败。
4. 总分 `>= 80`。
5. `事实准确性 >= 90`。
6. `观点清晰度 >= 75`。
7. 长短稿事实一致。

失败处理：

- 第一次失败：针对失败原因定向重写。
- 第二次失败：只重写对应模块，不全链路重跑。
- 连续失败两轮后废弃该选题。

### 3.9 Export Service

输出产物：

- `final_long_article.md`
- `final_short_post.md`
- `metadata.json`
- `review_report.json`

其中 `metadata.json` 至少包含：

- event_id
- run_id
- title_long
- title_short
- summary
- tags
- source_urls
- scores
- generated_at
- prompt_versions
- model_versions

## 4. 状态机设计

建议把每个候选内容包建模成一个 `content_job`，状态如下：

```text
created
ingested
normalized
clustered
selected
researched
outlined
drafted
claims_extracted
verified
reviewed
accepted
rejected
exported
```

附加规则：

- 每次状态变化写入 `job_events`。
- 所有失败原因必须结构化落库。
- 支持从 `researched` 或 `drafted` 状态开始重跑，而不是每次全量重头开始。

## 5. 数据模型

建议 MVP 先用 PostgreSQL 单库，不拆微服务数据库。

核心表：

- `sources`
  - 来源配置、权重、抓取方式、可信度等级
- `raw_documents`
  - 原始抓取结果、原始 html、抓取时间
- `documents`
  - 清洗后的正文、发布时间、实体、摘要
- `event_clusters`
  - 事件聚类结果、聚类摘要、主题标签
- `event_scores`
  - 各类评分特征和总分
- `research_packets`
  - 入选事件的结构化研究资料
- `content_jobs`
  - 每个选题一次完整生产任务
- `drafts`
  - outline、长文、短帖、多轮重写版本
- `claims`
  - 从 draft 抽取出的断言
- `claim_verifications`
  - 每条断言的证据和校验结果
- `reviews`
  - review 评分和问题列表
- `assets`
  - 最终 markdown/json 产物路径
- `job_events`
  - 状态流转和错误日志

## 6. LLM 调用设计

### 6.1 角色拆分

MVP 不建议做“相互对话式 Agent”，而是做固定角色函数：

- `topic_ranker`
- `research_compiler`
- `outline_writer`
- `article_writer`
- `short_post_writer`
- `claim_extractor`
- `fact_checker`
- `editor_reviewer`
- `gatekeeper`

### 6.2 调用原则

- 所有 LLM 输出都使用结构化 schema。
- 提示词按角色版本化，写入数据库。
- 低温度用于抽取、校验、分类。
- 中温度用于写作和改写。
- 单个角色只做单一职责，避免“一步到位”大提示词。

### 6.3 模型路由

建议分三类模型能力：

- `cheap model`
  - 摘要、标签、去重辅助、标题备选
- `reasoning model`
  - 选题判断、研究整合、review、质量打分
- `writing model`
  - 长文和短帖生成、定向重写

原因：

- 成本更可控。
- 失败定位更清楚。
- 后续方便替换供应商。

## 7. 推荐技术栈

### 7.1 后端

- `Python 3.11+`
- `FastAPI`
- `SQLAlchemy`
- `Pydantic`
- `PostgreSQL`
- `Redis`
- `Celery`

理由：

- Python 生态适合抓取、NLP、LLM 编排。
- FastAPI 适合做管理 API、调试接口、内部控制台。
- Celery 足够覆盖 MVP 的异步队列、重试、定时任务编排需求。

### 7.2 抓取与解析

- `httpx`：静态页面抓取
- `feedparser`：RSS/Atom
- `Playwright`：少量动态页面抓取
- 正文提取：可选 `trafilatura` 或自定义抽取器

策略：

- 默认不用浏览器。
- 只有静态抓取失败或页面内容依赖前端渲染时才启用 Playwright。

### 7.3 存储与文件

- PostgreSQL：主数据
- 本地 `data/` 或对象存储：原始 html、文本快照、导出稿件

### 7.4 部署

MVP 建议单机 Docker Compose：

- `api`
- `worker`
- `scheduler`
- `postgres`
- `redis`

不要在 MVP 一开始就上 Kubernetes。

## 8. 目录建议

```text
ai-poster/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
      ingestion/
      extraction/
      events/
      research/
      writing/
      qa/
      export/
    workflows/
    prompts/
  data/
    raw/
    cleaned/
    exports/
  tests/
    unit/
    integration/
    e2e/
  docs/
    mvp-technical-plan.md
```

## 9. 可观测性与运维

必须记录：

- 每次 run 的开始时间、结束时间、耗时
- 每步输入 token、输出 token、成本估算
- 每个内容包的失败阶段和失败原因
- 被放行稿件的来源链路

建议：

- 应用日志结构化输出 JSON。
- 对每个 `content_job` 生成唯一追踪 ID。
- 所有 LLM 调用保留 prompt hash 和 response snapshot。

## 10. 测试策略

MVP 至少有三层测试：

### 10.1 Unit Test

- URL 规范化
- 文本清洗
- 去重规则
- 评分计算
- 质量闸门规则

### 10.2 Integration Test

- 一条新闻从抓取到聚类的完整链路
- 一份 research packet 到双稿生成的完整链路
- 一篇 draft 到 claim 校验和 review 的完整链路

### 10.3 Replay Test

- 固定一批历史真实事件，定期重放整条流水线
- 检查产出稳定性、分数漂移、失败率

对这个项目，`replay test` 很重要，因为 prompt 或模型切换会导致行为回归。

## 11. 风险与控制

### 11.1 最大风险

- 自动放行会把事实错误自动规模化。

控制手段：

- 强制 claim extraction + evidence verification
- 只允许基于 research packet 写作
- 长短稿一致性校验
- 高风险字段用规则二次检查

### 11.2 第二风险

- 选题质量不稳定，导致系统每天有产出但没价值。

控制手段：

- 初期收缩来源池
- 引入稳定的事件评分特征
- 对放行稿件做人工抽检和回灌

### 11.3 第三风险

- Writer 和 Reviewer 使用同类逻辑，容易“互相放过”。

控制手段：

- Reviewer 不接触写作提示词
- QA 拆成 claim 校验和 editorial review 两层
- Gatekeeper 独立判定，不复用 writer 输出结构

## 12. 分阶段落地

### Phase 1：基础闭环

- 来源抓取
- 正文清洗
- 去重聚类
- 单题 research packet
- 公众号长文生成
- 基础 review

### Phase 2：双版本与质量闸门

- 小红书短帖生成
- claim extraction
- fact verification
- quality gate
- 导出标准化产物

### Phase 3：稳定性与运营化

- 后台查看 run 状态
- 历史回放
- 指标看板
- 来源配置管理

## 13. 核心结论

这个项目的关键不是“多写几篇”，而是建立一条能稳定拒绝低质量稿件的流水线。

MVP 最正确的技术路线不是先做复杂 Agent，而是先做：

1. 可追溯的数据流
2. 可解释的选题评分
3. 可验证的事实底座
4. 可复现的质量闸门

只要这四件事做对，后面接自动发布、扩展财经赛道、增加多平台风格，都会顺很多。
