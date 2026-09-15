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
ROOT="$(pwd)"
OUT="$ROOT/Aria2-${ARCH}-${VER}.spk"

# 在独立暂存目录中组装，避免 scripts/ 输出名与源码目录冲突
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# SPK 内部约定：package 内容打成 package.tgz；scripts/conf 为 gzip tar 流（成员名固定，不带 ./ 前缀）
tar -C package -czf "$STAGE/package.tgz" .
tar -C scripts -czf "$STAGE/scripts" common installer preinst postinst postupgrade preuninst postuninst start-stop-status
tar -C conf    -czf "$STAGE/conf" privilege resource
cp INFO PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG "$STAGE/"

rm -f "$OUT"
tar -cf "$OUT" -C "$STAGE" INFO PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG package.tgz scripts conf

echo "已生成：$OUT"
