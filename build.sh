#!/bin/bash
# 在 Linux / WSL / macOS / Git Bash 下执行：./build.sh
# 产物：Aria2-<arch>-<version>.spk（可在套件中心「手动安装」）
# 打包结构对齐 Synology 官方 pkgscripts：
#   package.tgz  —— gzip tar，成员为裸文件名（无 ./ 前缀）
#   scripts/conf —— gzip tar 流，成员为 ./<name>
#   WIZARD_UIFILES —— gzip tar 流，成员带 WIZARD_UIFILES/ 目录前缀
#   外层为非压缩 tar
set -e
cd "$(dirname "$0")"

# 确保脚本与 CGI 具备可执行位
chmod +x scripts/* package/ui/index.cgi package/server/aria2c

# 从 INFO 读取版本与架构
VER=$(sed -n 's/^version="\(.*\)"$/\1/p' INFO)
ARCH=$(sed -n 's/^arch="\(.*\)"$/\1/p' INFO)
ROOT="$(pwd)"
OUT="$ROOT/Aria2-${ARCH}-${VER}.spk"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# package.tgz：成员名不带 ./ 前缀（与官方 ls | tar -T - 行为一致）
ls -A package > "$STAGE/package.list"
tar -C package -czf "$STAGE/package.tgz" -T "$STAGE/package.list"

# scripts / conf：gzip tar 流
tar -C scripts -czf "$STAGE/scripts" .
tar -C conf    -czf "$STAGE/conf" .

# WIZARD_UIFILES：成员保留 WIZARD_UIFILES/ 目录前缀
mkdir -p "$STAGE/wizroot/WIZARD_UIFILES"
cp WIZARD_UIFILES/install_uifile "$STAGE/wizroot/WIZARD_UIFILES/"
tar -C "$STAGE/wizroot" -czf "$STAGE/WIZARD_UIFILES" WIZARD_UIFILES

# 图标与 INFO（INFO 追加 extractsize，单位 KB）
cp PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG "$STAGE/"
cp INFO "$STAGE/INFO"
echo "extractsize=$(du -sk package | awk '{print $1}')" >> "$STAGE/INFO"

rm -f "$OUT"
tar -cf "$OUT" -C "$STAGE" \
    INFO PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG \
    package.tgz scripts conf WIZARD_UIFILES

echo "已生成：$OUT"
