#!/bin/bash
# 每日晚上 9 点编程学习提醒

# 发送系统通知
osascript -e 'display notification "该看编程视频学习啦！建议学习 30 分钟～" with title "📚 编程学习提醒"'

# 自动打开编程学习文件夹
open ~/.openclaw/workspace/编程学习/

# 打开 B 站编程教程
open "https://www.bilibili.com/v/popular/all?keyword=Python 入门"
