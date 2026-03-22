# uwillberich 技能使用指南

_你的 A 股次日策略制定系统_

## 🚀 快速启动

### 基础命令

```bash
cd ~/.openclaw/skills/uwillberich

# 查看可用预设
./run.sh mx_toolkit.py list-presets

# 市场情绪快照
./run.sh market_sentiment.py

# 资金流向分析
./run.sh capital_flow.py

# 早盘简报 (核心 10 只)
./run.sh morning_brief.py --groups core10

# 开盘检查清单
./run.sh opening_window_checklist.py --groups tech_repair defensive_gauge policy_beta
```

---

## 📊 日常使用工作流

### 盘前准备 (08:30-09:00)

```bash
# 1. 政策扫描
./run.sh mx_toolkit.py preset --name preopen_policy

# 2. 全球风险扫描
./run.sh mx_toolkit.py preset --name preopen_global_risk

# 3. 市场快照
./run.sh fetch_market_snapshot.py --format markdown

# 4. 市场情绪
./run.sh market_sentiment.py

# 5. 早盘简报
./run.sh morning_brief.py --groups cross_cycle_anchor12
```

### 集合竞价 (09:20-09:25)

```bash
# 快速检查核心股票竞价情况
./run.sh fetch_quotes.py sz300502 sz300308 sz000977 sh688981
```

### 开盘确认 (09:30-10:00)

```bash
# 开盘检查清单
./run.sh opening_window_checklist.py --groups tech_repair defensive_gauge policy_beta

# 实时资金流向
./run.sh capital_flow.py --groups tech_repair defensive_gauge
```

---

## 🎯 核心预设场景

### 场景 1: 科技修复判断

```bash
# 光模块板块共振
./run.sh mx_toolkit.py preset --name board_optical_module

# 算力板块共振
./run.sh mx_toolkit.py preset --name board_compute_power

# 验证龙头个股
./run.sh mx_toolkit.py preset --name validate_inspur
./run.sh mx_toolkit.py preset --name validate_luxshare

# 产业链扩展
./run.sh industry_chain.py --groups tech_repair
```

### 场景 2: 防御风格判断

```bash
# 能源防御板块
./run.sh mx_toolkit.py preset --name board_energy_defense

# 检查防御指标
./run.sh morning_brief.py --groups defensive_gauge

# 产业链扩展
./run.sh industry_chain.py --groups defensive_gauge
```

### 场景 3: 政策驱动判断

```bash
# 政策扫描
./run.sh mx_toolkit.py preset --name preopen_policy

# 政策贝塔股票池
./run.sh morning_brief.py --groups policy_beta

# 资金流向确认
./run.sh mx_toolkit.py preset --name flow_main_force
```

### 场景 4: 完整工作流

```bash
# 一站式完整流程
./run.sh mx_toolkit.py preset --name preopen_repair_chain
```

---

## 📋 输出解读指南

### 市场情绪评分 (market_sentiment.py)

**状态分类**：
- `抱团行情`: 强度集中在少数龙头
- `科技修复`: 科技板块领涨且广度改善
- `修复扩散`: 多板块共同上涨
- `分化偏弱`: 广度差，反弹局部

**评分组成**：
- 市场广度：上涨/下跌股票数量
- 主力资金：净流入/流出金额
- 板块扩散：强势/弱势板块对比
- 观察池风格：成长/防御/混合

### 资金流向 (capital_flow.py)

**关键指标**：
- 全市场主力净流入：正值为好，负值为差
- 板块净流入排名：识别资金聚焦方向
- 个股净流入排名：识别龙头承接

**解读规则**：
- 主力大幅流出 + 指数下跌 = 真弱
- 主力流出 + 指数横盘 = 警惕
- 主力流入 + 指数上涨 = 真强
- 主力流入 + 指数下跌 = 背离 (可能机会)

### 早盘简报 (morning_brief.py)

**核心字段**：
- `strong_signal`: 强势信号 (站回昨收、接近昨高)
- `weak_signal`: 弱势信号 (跌破昨收、逼近昨低)

**使用方式**：
- 9:45 前观察哪些股票实现 `strong_signal`
- 警惕出现 `weak_signal` 的股票
- 对比不同组的相对强度

---

## 🧠 决策框架

### 市场分类决策树

```
1. 隔夜外部冲击层
   ├─ 石油/天然气价格冲击？
   ├─ 地缘政治事件？
   ├─ 美股/港股方向？
   └─ 利率决策？

2. 国内政策/流动性层
   ├─ LPR 发布日？(每月 20 日)
   ├─ 央行指导？
   └─ 财政/地产支持？

3. 内部市场结构层
   ├─ 指数位置
   ├─ 上涨/下跌广度
   ├─ 最强/最弱板块
   ├─ 龙头行为 vs 高贝塔落后者
   └─ 券商 vs 银行 (情绪交叉检查)
```

### 分类结果与应对

| 市场状态 | 特征 | 默认应对 |
|---------|------|---------|
| **主线市场** | 国家级催化剂、板块共振、多龙头、广度强 | 聚焦核心板块，偏好龙头，允许积极跟进 |
| **独立龙头** | 1-3 只股票脱离、板块弱、公司层面催化剂 | 交易特定龙头，保持短周期 |
| **区间/防御** | 无主线、无持久龙头、广度差、低贝塔强 | 缩短周期，避免追涨，偏好观察 |

---

## ⏰ 时间门检查清单

### 09:00 - 政策门
- [ ] LPR 是否发布？(每月 20 日)
- [ ] 5Y LPR 是否降息？→ 升级地产链、家电、建材、券商
- [ ] 是否需要重新排序政策敏感板块？

### 09:20-09:25 - 集合竞价
- [ ] 哪个组领先？(成长修复 / 政策贝塔 / 防御集中 / 孤立挤压)
- [ ] 券商/多元金融/银行给出什么情绪信号？
- [ ] 是多个龙头还是只有 1-3 只股票？

### 09:30-10:00 - 开盘窗口
- [ ] 指数是否守住关键位？
- [ ] 龙头是否收复昨收？
- [ ] 风险偏好代理 (如券商) 是否改善？
- [ ] 市场足够宽 (主线) 还是足够窄 (独立龙头)？

### 10:00-10:30 - 广度窗口
- [ ] 广度是否扩散？
- [ ] 修复是否超出前 2-3 只龙头？
- [ ] 大龙头是否继续推进还是停滞？
- [ ] 小盘股轮动是否伴随大龙头停滞 (派发信号)？

### 14:00-14:30 - 下午确认
- [ ] 是持续修复还是技术反弹？
- [ ] 龙头是否停滞而小盘股轮动 (派发)？

---

## 🎭 输出模板

使用以下模板生成决策笔记：

```markdown
## 决策摘要
[一句话：市场状态 + 核心策略]

## 市场状态
- 分类：主线 / 独立龙头 / 区间防御
- 理由：[广度、龙头行为、板块共振]

## 情景路径
- **Base (60%)**: [基准情景]
- **Bull (25%)**: [乐观情景，触发条件]
- **Bear (15%)**: [悲观情景，失效条件]

## 最可能修复板块
1. [板块 1] - [理由]
2. [板块 2] - [理由]

## 仅防御板块
- [板块] - [仅在防御情景下配置]

## 关键观察股票
| 股票 | 角色 | 强势信号 | 弱势信号 |
|------|------|---------|---------|
| XXX  | ...  | ...     | ...     |

## 开盘检查清单
- [ ] 09:00 政策检查
- [ ] 09:25 集合竞价检查
- [ ] 09:30-10:00 开盘确认
- [ ] 10:00-10:30 广度确认

## Do / Avoid
**Do**:
- [具体行动 1]
- [具体行动 2]

**Avoid**:
- [避免行动 1]
- [避免行动 2]

## 失效条件
- [什么情况下当前判断失效]
```

---

## 🔧 高级功能

### 记忆层持久化

```bash
# 记录重要交互
./run.sh memory_layer.py touch --role user --summary '请求次日策略'

# 保存开放项目
./run.sh memory_layer.py remember --scope open_item --key next_step --value '09:00 前刷新预开盘笔记'

# 构建交接文档
./run.sh memory_layer.py build-handoff --force
```

### 新闻迭代器 (持续监控)

```bash
# 手动轮询
./run.sh news_iterator.py poll

# 生成报告
./run.sh news_iterator.py report --hours 12

# 安装为 launchd 服务 (macOS)
./run.sh install_news_iterator_launchd.py install --interval-seconds 300
```

### 记忆交接自动化 (每小时刷新)

```bash
# 安装为 launchd 服务
./run.sh install_memory_handoff_launchd.py install
```

---

## 📛 常见问题

### Q: 网络连接失败
**A**: 检查 SSL 证书配置，使用 `./run.sh` 脚本自动处理：
```bash
export SSL_CERT_FILE=/opt/homebrew/lib/python3.11/site-packages/certifi/cacert.pem
```

### Q: API Key 未配置
**A**: 运行配置检查：
```bash
./run.sh runtime_config.py status
```
如需设置：
```bash
printf '%s' 'your_key' | ./run.sh runtime_config.py set-em-key --stdin
```

### Q: 如何判断是主线还是独立龙头？
**A**: 关键看三点：
1. 催化剂级别 (国家级 vs 公司级)
2. 龙头数量 (多个 vs 1-3 个)
3. 广度扩散 (全市场 vs 局部)

### Q: 什么时候使用 cross_cycle_anchor12 vs core10？
**A**:
- `core10`: 快速快照，日常使用
- `cross_cycle_anchor12`: 更全面的每日锚点，包含更多高质量龙头

---

## 📚 参考文档

- `references/methodology.md` - 交易哲学和决策树
- `references/data-sources.md` - 数据源端点
- `references/trading-mode-prompt.md` - 交易模式提示词
- `references/opening-window-template.md` - 开盘窗口模板
- `references/cross-cycle-watchlist.md` - 跨周期股票池使用指南

---

_记住：这不是长期投资组合系统，而是次日战术决策工具。核心是将市场结构转化为可执行的开盘计划。_
