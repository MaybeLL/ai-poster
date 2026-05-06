# AI Poster

`AI Poster` 是一个面向 AI 科技赛道的自动化内容生产系统。当前仓库已经落下第一批可执行骨架代码，重点覆盖：

- `content_job` 状态机
- `quality_gate` 放行规则
- `mvp_workflow` 最小工作流 runner
- 本地 demo 入口
- `settings` 环境配置加载
- `sources.json` 来源目录
- `rss_adapter` RSS 抓取与时间窗口过滤
- `ingestion_service` 多来源聚合
- `event_engine` 候选事件聚类、规则评分和 top-N 选择
- `research_service` 结构化事实底座汇编
- `writing_service` 模板化长文/短帖草稿生成
- `qa_service` 规则审稿与质量门输入
- `pipeline` 从来源到候选成稿的本地闭环
- `agent provider` 抽象，支持把智能能力挂到外部进程

## 当前状态

这还是第一条可运行的垂直切片，已经接入本地来源配置、RSS ingestion、事件聚类、research packet、模板化写作和规则 QA，但还没有接入真实 LLM 写作、数据库和 API 服务。当前目标是先把核心领域模型、来源入口和流水线宿主搭起来。

## 本地运行

直接运行 demo：

```bash
python3 -m app --mode demo-workflow --topic "OpenAI releases a new coding model"
```

运行 ingestion 摘要：

```bash
python3 -m app --mode ingest --lookback-hours 24
```

运行事件排序摘要：

```bash
python3 -m app --mode rank-events --lookback-hours 24 --limit 3
```

运行 research packet 摘要：

```bash
python3 -m app --mode research --lookback-hours 24 --limit 3
```

运行完整 pipeline 摘要：

```bash
python3 -m app --mode pipeline --lookback-hours 24 --limit 1
```

探测智能后端配置：

```bash
python3 -m app --mode agent-probe
AI_POSTER_INTELLIGENCE_BACKEND=codex python3 -m app --mode agent-probe
AI_POSTER_INTELLIGENCE_BACKEND=claude-code python3 -m app --mode agent-probe
```

运行智能后端最小烟测：

```bash
AI_POSTER_INTELLIGENCE_BACKEND=codex python3 -m app --mode agent-smoke
AI_POSTER_INTELLIGENCE_BACKEND=claude-code python3 -m app --mode agent-smoke
```

运行测试：

```bash
python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

## 环境变量

- `AI_POSTER_ENV`：运行环境，默认 `development`
- `AI_POSTER_DATA_DIR`：数据目录，默认 `data`
- `AI_POSTER_INTELLIGENCE_BACKEND`：`rule`、`codex`、`claude-code`
- `AI_POSTER_CODEX_COMMAND`：覆盖 `codex` 进程命令，默认 `codex exec`
- `AI_POSTER_CLAUDE_CODE_COMMAND`：覆盖 `claude code` 进程命令，默认 `claude`
- `AI_POSTER_CODEX_ENV_JSON`：给 `codex` 进程注入环境变量，值为 JSON 对象
- `AI_POSTER_CLAUDE_CODE_ENV_JSON`：给 `claude` 进程注入环境变量，值为 JSON 对象

## 智能层解耦

当前智能层边界已经拆成三层：

- `pipeline/service` 只关心 research、writing、qa 的输入输出契约
- `content service` 负责把业务对象转成 prompt 和结构化结果
- `agent provider` 负责真正调用外部进程

这意味着后续你要切换实现时，改动面很小：

- 从 `codex` 切到 `claude code`：改 `AI_POSTER_INTELLIGENCE_BACKEND`
- 改命令参数：改 `AI_POSTER_CODEX_COMMAND` 或 `AI_POSTER_CLAUDE_CODE_COMMAND`
- 改进程环境：改 `AI_POSTER_CODEX_ENV_JSON` 或 `AI_POSTER_CLAUDE_CODE_ENV_JSON`
- 改成 API 调用、远程 worker、消息队列：实现新的 `AgentProvider`，不动 pipeline

当前代码入口：

- provider 抽象在 [app/agents/provider.py](/Users/maybell/Documents/Code/ai-poster/app/agents/provider.py:1)
- CLI 协议 profile 在 [app/agents/profiles.py](/Users/maybell/Documents/Code/ai-poster/app/agents/profiles.py:1)
- provider 装配在 [app/agents/factory.py](/Users/maybell/Documents/Code/ai-poster/app/agents/factory.py:1)
- 内容服务装配在 [app/services/factory.py](/Users/maybell/Documents/Code/ai-poster/app/services/factory.py:1)

## 当前限制

- 默认仍使用 `rule` backend，只有显式设置 `AI_POSTER_INTELLIGENCE_BACKEND` 才会走外部进程。
- `AgentResearchService`、`AgentWritingService`、`AgentQaService` 都已支持外部进程，但还没做真实模型调用烟测。
- RSS 拉取失败时会降级为 `error_count`，CLI 不会直接崩溃。
- 默认数据源还需要后续人工校准和扩充。

## 后续实现顺序

1. 用真实 `research -> writing -> review` Agent 替换当前规则模板
2. 接数据库和可追溯 run 存储
3. FastAPI 管理接口和任务调度
