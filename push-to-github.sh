#!/bin/bash
# GitHub 推送脚本
# 2026-03-22 创建

set -e

echo "========================================"
echo "GitHub 推送脚本"
echo "========================================"
echo ""

cd /Users/macbook/.openclaw/workspace

echo "📊 当前状态:"
git status --short
echo ""

echo "📝 待推送的提交:"
git log origin/main..main --oneline
echo ""

echo "🔐 推送需要 GitHub 认证"
echo ""
echo "请选择认证方式:"
echo ""
echo "1️⃣  使用 GitHub Personal Access Token (推荐)"
echo "   步骤:"
echo "   1. 访问：https://github.com/settings/tokens"
echo "   2. Generate new token (classic)"
echo "   3. Scopes: 勾选 repo"
echo "   4. 复制生成的 token"
echo "   5. 运行：git push origin main"
echo "   6. 用户名：huangrichao2020"
echo "   7. 密码：[粘贴 token]"
echo ""
echo "2️⃣  使用 SSH Key"
echo "   需要将 huangrichao2020 的 SSH key 添加到 GitHub"
echo "   当前 SSH key 关联的是 munn111，没有权限"
echo ""
echo "3️⃣  使用 GitHub Desktop"
echo "   下载：https://desktop.github.com"
echo "   登录后添加本地仓库推送"
echo ""
echo "========================================"
echo "🚀 执行推送 (需要手动输入 token)"
echo "========================================"
echo ""

# 切换回 HTTPS
git remote set-url origin https://github.com/huangrichao2020/uwillberich.git

echo "远程仓库：$(git remote get-url origin)"
echo ""
echo "准备推送..."
echo ""

# 尝试推送
if git push origin main; then
    echo ""
    echo "✅ 推送成功!"
else
    echo ""
    echo "❌ 推送失败，需要认证"
    echo ""
    echo "请执行以下命令手动推送:"
    echo ""
    echo "  cd /Users/macbook/.openclaw/workspace"
    echo "  git push origin main"
    echo ""
    echo "然后:"
    echo "  - 用户名输入：huangrichao2020"
    echo "  - 密码输入：[GitHub Personal Access Token]"
    echo ""
    echo "Token 获取地址:"
    echo "  https://github.com/settings/tokens"
    echo ""
fi

echo ""
echo "========================================"
