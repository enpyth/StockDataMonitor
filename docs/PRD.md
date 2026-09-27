# Product Requirements Document / 产品需求文档

## 1. Product Summary / 产品概述

### English
Quant v1 is a stock data collection and monitoring platform. It collects company profile data, daily OHLCV data, and latest quote snapshots for a configured stock universe using `yfinance`, stores the data in Supabase, and exposes it through a FastAPI API and TanStack Start web dashboard.

### 中文
Quant v1 是一个股票数据采集与监控平台。系统通过 `yfinance` 采集配置股票池中的公司基础信息、日线 OHLCV 数据和最新价格快照，写入 Supabase，并通过 FastAPI API 和 TanStack Start 前端仪表盘展示。

## 2. Goals / 目标

### English
- Collect stock metadata, daily OHLCV, and latest quote snapshots for selected NASDAQ, NYSE, TSE, and ASX stocks.
- Keep the stock universe configurable without code changes.
- Store normalized market data in Supabase Postgres.
- Provide authenticated API and web access through Supabase Auth.
- Support manual ingestion in v1, with daily batch scheduling as the intended operating model.

### 中文
- 采集 NASDAQ、NYSE、TSE、ASX 中选定股票的基础信息、日线 OHLCV 和最新价格快照。
- 股票池通过配置文件管理，不需要改代码。
- 将标准化后的市场数据存储到 Supabase Postgres。
- 通过 Supabase Auth 提供受保护的 API 和前端访问。
- v1 支持手动触发采集，目标运维模式是每日批处理。

## 3. Non-Goals / 非目标

### English
- No real-time streaming or high-frequency intraday trading feed.
- No trading, brokerage, order management, or portfolio execution.
- No paid market data provider integration in v1.
- No investment advice or recommendation engine.

### 中文
- 不提供实时流式行情或高频日内行情。
- 不支持交易、券商接入、订单管理或组合执行。
- v1 不接入付费行情供应商。
- 不提供投资建议或推荐引擎。

## 4. Users and Use Cases / 用户与使用场景

### English
- **Admin/operator**: configures the stock universe, runs ingestion, checks ingestion health, and verifies stored data.
- **Analyst/user**: signs in, reviews latest quote snapshots, checks recent OHLCV history, and monitors supported exchanges.

### 中文
- **管理员/运维人员**：配置股票池、执行数据采集、检查采集状态、确认数据是否成功入库。
- **分析用户**：登录系统，查看最新价格快照、近期 OHLCV 历史和支持的交易所数据。

## 5. Functional Requirements / 功能需求

### English
- Stock universe is defined in `apps/api/config/stocks.json`.
- Default configured symbols:
  - NASDAQ: `AAPL`, `MSFT`, `NVDA`
  - NYSE: `JPM`, `JNJ`, `KO`
  - TSE: `7203.T`, `6758.T`, `8306.T`
  - ASX: `BHP.AX`, `CBA.AX`, `CSL.AX`
- API supports:
  - health check
  - list active securities
  - get one security
  - get OHLCV history
  - get latest quote snapshots
  - list ingestion runs
  - trigger ingestion
- Web app supports:
  - Supabase Google OAuth and email magic-link login
  - stock universe table
  - selected stock detail panel
  - OHLCV mini chart
  - recent ingestion status
  - manual ingestion trigger

### 中文
- 股票池定义在 `apps/api/config/stocks.json`。
- 默认股票配置：
  - NASDAQ: `AAPL`, `MSFT`, `NVDA`
  - NYSE: `JPM`, `JNJ`, `KO`
  - TSE: `7203.T`, `6758.T`, `8306.T`
  - ASX: `BHP.AX`, `CBA.AX`, `CSL.AX`
- API 支持：
  - 健康检查
  - 查询启用的股票列表
  - 查询单只股票
  - 查询 OHLCV 历史
  - 查询最新价格快照
  - 查询采集运行记录
  - 手动触发采集
- 前端支持：
  - Supabase Google OAuth 和邮箱 magic link 登录
  - 股票池表格
  - 当前选中股票详情
  - OHLCV 小型图表
  - 最近采集状态
  - 手动触发采集

## 6. Data Model / 数据模型

### English
Supabase tables:
- `exchanges`: exchange code, name, timezone, and currency.
- `securities`: stock identity, Yahoo Finance symbol, company metadata, and active flag.
- `ohlcv_daily`: daily open, high, low, close, adjusted close, and volume.
- `quote_snapshots`: point-in-time quote snapshots.
- `ingestion_runs`: ingestion status, counts, timestamps, and symbol-level errors.

### 中文
Supabase 数据表：
- `exchanges`：交易所代码、名称、时区和币种。
- `securities`：股票身份、Yahoo Finance symbol、公司元数据和启用状态。
- `ohlcv_daily`：每日开盘价、最高价、最低价、收盘价、复权收盘价和成交量。
- `quote_snapshots`：某一时刻的价格快照。
- `ingestion_runs`：采集状态、数量统计、时间戳和单 symbol 错误信息。

## 7. Security and Access / 安全与访问控制

### English
- Supabase Auth is the identity provider.
- Protected API routes require a Supabase bearer token.
- Supabase RLS allows authenticated users to read stock data.
- API server uses `SUPABASE_SERVICE_ROLE_KEY`; this key must never be exposed to the browser.
- Web app only uses `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_BASE_URL`.

### 中文
- Supabase Auth 是身份认证提供方。
- 受保护 API 路由需要 Supabase bearer token。
- Supabase RLS 允许 authenticated 用户读取股票数据。
- API 服务端使用 `SUPABASE_SERVICE_ROLE_KEY`；该 key 绝不能暴露给浏览器。
- 前端只使用 `VITE_SUPABASE_URL`、`VITE_SUPABASE_ANON_KEY`、`VITE_API_BASE_URL`。

## 8. Acceptance Criteria / 验收标准

### English
- `bun run api:test` passes.
- `bun run api:lint` passes.
- `bun run test` passes.
- `bun run build` passes.
- `bun run api:ingest` completes with `symbols_succeeded = 12` and `symbols_failed = 0` after Supabase is configured.
- Web users can sign in and view stocks, quotes, OHLCV, and ingestion runs.

### 中文
- `bun run api:test` 通过。
- `bun run api:lint` 通过。
- `bun run test` 通过。
- `bun run build` 通过。
- 配置 Supabase 后，`bun run api:ingest` 返回 `symbols_succeeded = 12` 且 `symbols_failed = 0`。
- 前端用户可以登录并查看股票、价格快照、OHLCV 和采集运行记录。
