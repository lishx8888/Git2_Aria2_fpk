#!/bin/bash
# 在 Linux / WSL / macOS / Git Bash 下执行：./build.sh
# 产物：Aria2-<arch>-<version>.spk（可在套件中心「手动安装」）
set -e
cd "$(dirname "$0")"

# 确保脚本与 CGI 具备可执行位
chmod +x scripts/* package/ui/index.cgi package/server/aria2c

# 从 INFO 读取版本与架构
VER=$(sed -n 's/^version="\(.*\)"$/\1/p' INFO)
ARCH=$(sed -n 's/^arch="\(.*\)"$/\1/p' INFO)
OUT="Aria2-${ARCH}-${VER}.spk"

rm -f package.tgz scripts.tgz conf.tgz "$OUT"

# SPK 内部约定：package 内容打成 package.tgz；scripts/conf 为 gzip tar 流（成员名固定）
tar -C package -czf package.tgz .
tar -C scripts -czf scripts .
tar -C conf    -czf conf .

tar cf "$OUT" INFO PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG package.tgz scripts conf
rm -f package.tgz scripts.tgz conf.tgz scripts conf

echo "已生成：$OUT"
