#!/bin/bash

# 简约风景壁纸列表（使用实际 HEIC 图片文件）
WALLPAPERS=(
    "/System/Library/Desktop Pictures/.thumbnails/Catalina Coast.heic"
    "/System/Library/Desktop Pictures/.thumbnails/Catalina Sunset.heic"
    "/System/Library/Desktop Pictures/.thumbnails/Catalina Morning.heic"
    "/System/Library/Desktop Pictures/.thumbnails/Big Sur Horizon.heic"
    "/System/Library/Desktop Pictures/.thumbnails/Big Sur Shore Rocks.heic"
    "/System/Library/Desktop Pictures/.thumbnails/Big Sur Mountains.heic"
)

# 获取当前时间的小时数
HOUR=$(date +%H)
INDEX=$((HOUR % ${#WALLPAPERS[@]}))

WALLPAPER="${WALLPAPERS[$INDEX]}"

# 使用 AppleScript 设置壁纸
osascript -e "tell application \"Finder\" to set desktop picture to POSIX file \"$WALLPAPER\""

echo "已切换壁纸：$WALLPAPER"
