# 金融分析技能配置

## 默认技能：uwillberich

**触发条件** (满足任一即调用)：
- 大 A / A 股 / a 股
- 股票 / 股市 / 大盘 / 盘面
- 金融 / 行情 / 板块
- 龙头 / 主力 / 资金流向
- 开盘 / 收盘 / 明日策略 / 后市展望
- 具体股票代码 (如 300750) 或名称 (如 宁德时代)

## 核心脚本

| 脚本 | 用途 | 使用场景 |
| --- | --- | --- |
| `morning_brief.py` | 早盘简报 | 每日市场概览 |
| `fetch_market_snapshot.py` | 市场快照 | 指数/板块数据 |
| `capital_flow.py` | 资金流向 | 主力进出分析 |
| `market_sentiment.py` | 市场情绪 | 情绪评分 |
| `opening_window_checklist.py` | 开盘清单 | 次日策略 |
| `mx_toolkit.py preset` | 预设扫描 | 政策/全球风险 |

## 输出标准

1. **决策摘要** - 一句话核心判断
2. **情景路径** - Base/Bull/Bear 三种情况
3. **修复板块** - 最可能领涨的方向
4. **防御板块** - 仅避险非修复
5. **开盘清单** - 09:00/09:25/09:30-10:00 检查点
6. **Do/Avoid** - 明确操作建议

## 运行方式

```bash
cd ~/.openclaw/skills/uwillberich
./run.sh <脚本名>
```

## API 配置

- API Key: `~/.uwillberich/runtime.env`
- SSL 证书：自动配置 (run.sh 处理)
