# MEMORY.md - 长期记忆

_这是 curated 的长期记忆，记录重要的决策、上下文和偏好。_

---

## 📌 核心偏好

### 金融/股票/A 股分析 - 默认使用 uwillberich 技能

**用户明确要求** (2026-03-21)：
> "写入你底层数据，以后聊到大 a，股票，金融等默认调用 uwillberich 技能，专注使用这个技能"

**执行规则**：
- 当用户提到以下关键词时，**自动调用 uwillberich 技能**：
  - "大 A" / "A 股" / "a 股"
  - "股票" / "股市" / "大盘"
  - "金融" / "行情" / "盘面"
  - "板块" / "龙头" / "主力"
  - "开盘" / "收盘" / "明日策略"
  - 具体股票代码或名称（如"宁德时代"、"300750"）

**uwillberich 技能路径**：
```bash
cd ~/.openclaw/skills/uwillberich
./run.sh morning_brief.py          # 早盘简报
./run.sh fetch_market_snapshot.py  # 市场快照
./run.sh capital_flow.py           # 资金流向
./run.sh market_sentiment.py       # 市场情绪
./run.sh opening_window_checklist.py  # 开盘清单
./run.sh mx_toolkit.py preset --name preopen_policy  # 政策扫描
./run.sh mx_toolkit.py preset --name preopen_global_risk  # 全球风险
```

**输出风格**：
- 决策导向，非机械解释
- 包含 Base/Bull/Bear 情景路径
- 开盘检查清单 (09:00/09:25/09:30-10:00)
- Do/Avoid 明确建议
- 主力资金流向 + 市场情绪评分

---

## 📅 重要日期

- **2026-03-22 19:59**: uwillberich 方法论深度内化完成，创建底层人格数据和交易模式数据
  - `memory/uwillberich-trading-persona.md` - 13 条核心原则 + 市场分类器 + 输出标准
  - `memory/uwillberich-decision-framework.md` - 三层分析框架 + 决策树 + 板块强度公式
  - `memory/uwillberich-timing-gates.md` - 6 个时间门纪律 + 检查清单
- **2026-03-22 19:45**: uwillberich 技能深度学习完成，形成完整技能总结文档 (`memory/uwillberich-skill-summary.md`)
- **2026-03-21**: uwillberich 技能测试完成，SSL 证书问题修复，设置为金融分析默认技能

---

## 🔧 技术配置

### Python 环境
- 系统 Python: 3.9.6 (`/usr/bin/python3`)
- Homebrew Python: 3.11.15 (`/opt/homebrew/bin/python3.11`)
- uwillberich 推荐使用 Python 3.11+

### SSL 证书配置
```bash
export SSL_CERT_FILE=/opt/homebrew/lib/python3.11/site-packages/certifi/cacert.pem
```

### 东方财富 API Key
- 存储位置：`~/.uwillberich/runtime.env`
- 状态：已配置 ✅

---

## 📝 笔记

- uwillberich 技能专注于 A 股次日策略制定
- 核心理念：将市场结构转化为可执行的开盘计划
- 偏好使用 `./run.sh` 脚本自动处理 SSL 配置
