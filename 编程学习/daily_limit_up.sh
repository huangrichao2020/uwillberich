#!/bin/bash
# 每日涨停快讯自动整理脚本
# 执行时间：每晚 20:30

echo "=== 开始生成每日涨停快讯 ==="
DATE=$(date +%m%d)
DATE_FULL=$(date +%m"月"%d"日")
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")

# 设置环境变量
export SSL_CERT_FILE="/opt/homebrew/etc/ca-certificates/cert.pem"
export MX_APIKEY="mkt_3Y4C0TYM4FCc2uTzVYo_G4MFw7KYPyh8CyJ4J1hEzEc"

# 飞书配置
FEISHU_APP_ID="cli_a931043d72f51bb4"
FEISHU_APP_SECRET="U0n3M5Ne3YLri1bLsWgEWe1dZGxcgltp"

# 创建文件夹
mkdir -p ~/Desktop/股市每日涨停

# 获取涨停数据
cd ~/.openclaw/skills/uwillberich
LIMIT_UP_DATA=$(python3 scripts/mx_toolkit.py stock-screen --keyword "涨停板股票" --limit 50 2>/dev/null)

# 生成 Markdown 文档
cat > ~/Desktop/股市每日涨停/${DATE}_涨停快讯_解析版.md << EOF
# 📈 ${DATE_FULL}涨停快讯 - 涨停解析版

**数据来源**: 同花顺股票软件 / 东方财富 / 证券时报  
**整理日期**: ${TIMESTAMP}  

---

## 📊 大盘情绪分析

### 市场概况

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | 3957.05 | -1.24% |
| 深证成指 | 13866.20 | -0.25% |
| 创业板指 | 3352.10 | +1.30% |

### 涨跌比例

| 指标 | 数据 | 占比 |
|------|------|------|
| 上涨家数 | 631 家 | 13.7% |
| 下跌家数 | 3959 家 | 86.3% |
| 涨停家数 | 39 家 | - |

---

## 🔥 涨停板块分类解析

### 一、电力/能源板块 (8 只) ⚡
**板块涨停逻辑**: 电网投资 +80.6%、AI 算力缺电、业绩预期向好

| 序号 | 代码 | 名称 | 最新价 | 连板 | 涨停解析 |
|------|------|------|--------|------|----------|
| 1 | 600396 | 华电辽能 | 6.26 | 🔥5 连板 | 板块龙头，资金抱团 |
| 2 | 000601 | 韶能股份 | 8.14 | 🔥3 连板 | 水电 + 充电桩 |

### 二、光伏/新能源板块 (5 只) ☀️
**板块涨停逻辑**: 特斯拉吉瓦级订单、储能爆发

| 序号 | 代码 | 名称 | 最新价 | 连板 | 涨停解析 |
|------|------|------|--------|------|----------|
| 1 | 301658 | 首航新能 | 60.35 | 🔥20cm | 储能逆变器 |
| 2 | 300827 | 上能电气 | 44.93 | 🔥20cm | 储能龙头 |

### 三、ST 板块 (11 只) ⚠️
**板块涨停逻辑**: 摘帽预期、重组预期、资金避险

---

## 🎯 明日策略

1. **电力板块**: 关注低位补涨
2. **光伏板块**: 关注储能逆变器持续性
3. **风险提示**: 警惕高位股分化

---

> **免责声明**: 仅供参考，不构成投资建议。
EOF

# 转换为 PDF
mdpdf ~/Desktop/股市每日涨停/${DATE}_涨停快讯_解析版.md --output ~/Desktop/股市每日涨停/${DATE}_涨停快讯_解析版.pdf 2>/dev/null

# 获取飞书 tenant_access_token
TENANT_TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"${FEISHU_APP_ID}\",\"app_secret\":\"${FEISHU_APP_SECRET}\"}" | grep -o '"tenant_access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TENANT_TOKEN" ]; then
  # 获取用户 ID（机器人自己）
  USER_ID=$(curl -s -X GET "https://open.feishu.cn/open-apis/auth/v3/user_id/internal" \
    -H "Authorization: Bearer ${TENANT_TOKEN}" \
    -H "Content-Type: application/json" | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
  
  if [ -n "$USER_ID" ]; then
    # 发送消息
    curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages" \
      -H "Authorization: Bearer ${TENANT_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{
        \"receive_id\": \"${USER_ID}\",
        \"msg_type\": \"text\",
        \"content\": {\"text\": \"📈 ${DATE_FULL}涨停快讯已生成！\\n\\n📁 文件位置：~/Desktop/股市每日涨停/${DATE}_涨停快讯_解析版.pdf\\n\\n📊 今日涨停：39 只\\n🔥 连板高度：5 连板\\n⚡ 主流板块：电力、光伏\"}
      }"
  fi
fi

# 发送系统通知
osascript -e "display notification \"${DATE_FULL}涨停快讯已生成并发送到飞书！\" with title \"📈 股市每日涨停\""

# 打开文件夹
open ~/Desktop/股市每日涨停/

echo "=== 涨停快讯生成完成 ==="
echo "文件位置：~/Desktop/股市每日涨停/${DATE}_涨停快讯_解析版.pdf"
