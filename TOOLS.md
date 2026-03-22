# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Feishu/Lark

- App ID: `cli_a931043d72f51bb4`
- App Name: sorcerer
- App Token: `tuYagQS1zh5MrGzXg4f3ScU1VHqMu0Jm`
- Status: 待授权 (need_user_authorization)

## Feishu Bot (机器人)

- Bot ID: `cli_a931076628761bc3`
- App Secret: `U0n3M5Ne3YLri1bLsWgEWe1dZGxcgltp`
- Status: 配置完成，待测试

## Python Environment

- Python: `/opt/homebrew/bin/python3.11` (v3.11.15)
- pip: `/opt/homebrew/bin/pip3.11`

## MX API Key (东方财富妙想)

- `MX_APIKEY`: `mkt_3Y4C0TYM4FCc2uTzVYo_G4MFw7KYPyh8CyJ4J1hEzEc`

## 桌面文件夹位置规则

| 文件夹 | 位置 | 存放内容 |
|--------|------|---------|
| 涨停复盘日报 | ~/Desktop/涨停复盘日报/ | 每日涨停复盘的 PDF 和 HTML 文件 |
| 股市每日涨停 | ~/Desktop/股市每日涨停/ | 每日自动生成的涨停快讯 (每晚 20:30) |
| 股市每日资讯 | ~/Desktop/股市每日资讯/ | 个股分析报告、行业资讯 |
| AI 编程学习 | ~/Desktop/AI 编程学习/ | 编程和 AI 学习资料 |

### 文件存放规则
- 涨停复盘日报 PDF/HTML → 涨停复盘日报
- 每日涨停快讯 → 股市每日涨停
- 个股分析报告 → 股市每日资讯
- 学习资料 → AI 编程学习
