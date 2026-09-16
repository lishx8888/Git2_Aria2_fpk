#!/bin/bash
# 在 Linux / WSL / macOS / Git Bash 下执行：./build.sh
# 产物：Aria2G-<arch>-<version>.spk（可在套件中心「手动安装」）
# 打包结构对齐 spksrc 框架（SynoCommunity 生产环境验证过的形态）：
#   外层为非压缩 tar，成员为普通文件与目录：
#     conf/ INFO PACKAGE_ICON*.PNG package.tgz scripts/ WIZARD_UIFILES/
#   package.tgz 为 gzip tar（payload），成员裸文件名
#   scripts / conf / WIZARD_UIFILES 为普通目录
#   INFO 必须含 support_conf_folder="yes"，否则 DSM 不解析 conf/privilege，
#   会将套件判定为 root 运行而拒绝安装
set -e
cd "$(dirname "$0")"

# 确保脚本与 CGI 具备可执行位
chmod +x scripts/* package/ui/index.cgi package/server/aria2c

# 从 INFO 读取版本与架构
VER=$(sed -n 's/^version="\(.*\)"$/\1/p' INFO)
ARCH=$(sed -n 's/^arch="\(.*\)"$/\1/p' INFO)
ROOT="$(pwd)"
OUT="$ROOT/Aria2G-${ARCH}-${VER}.spk"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# package.tgz：gzip tar，成员名不带 ./ 前缀
ls -A package > "$STAGE/package.list"
tar -C package -czf "$STAGE/package.tgz" -T "$STAGE/package.list"

# scripts / conf / WIZARD_UIFILES：以普通目录形态放入 SPK（与 spksrc 一致）
mkdir -p "$STAGE/scripts" "$STAGE/conf" "$STAGE/WIZARD_UIFILES"
cp scripts/common scripts/preinst scripts/postinst scripts/postupgrade \
   scripts/preuninst scripts/postuninst scripts/start-stop-status "$STAGE/scripts/"
cp conf/privilege conf/resource "$STAGE/conf/"
cp WIZARD_UIFILES/install_uifile "$STAGE/WIZARD_UIFILES/"
chmod 755 "$STAGE/scripts/"*
chmod 644 "$STAGE/conf/"* "$STAGE/WIZARD_UIFILES/"*

# 图标与 INFO（INFO 追加 extractsize 单位 KB，checksum 为 package.tgz 的 md5）
cp PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG "$STAGE/"
cp INFO "$STAGE/INFO"
echo "extractsize=$(du -sk package | awk '{print $1}')" >> "$STAGE/INFO"
echo "checksum=$(md5sum "$STAGE/package.tgz" | awk '{print $1}')" >> "$STAGE/INFO"

# 外层：非压缩 tar，成员名裸名，统一属主 root（与 spksrc `tar cpf $@ --owner=root --group=root` 一致）
rm -f "$OUT"
tar --owner=root --group=root -cf "$OUT" -C "$STAGE" \
    conf INFO PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG \
    package.tgz scripts WIZARD_UIFILES

# ===== 打包后自检：任一关键项不合规则删除产物退出 =====
CHECK_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE" "$CHECK_DIR"' EXIT
tar xf "$OUT" -C "$CHECK_DIR"
PRIV="$CHECK_DIR/conf/privilege"
echo "----------------------------------------"
echo "产物内 conf/privilege 实际内容："
cat "$PRIV"
echo "----------------------------------------"
FAIL=0
grep -q '"run-as"[[:space:]]*:[[:space:]]*"package"' "$PRIV" \
    || { echo "错误：privilege 不是 run-as=package" >&2; FAIL=1; }
grep -q '^support_conf_folder="yes"$' "$CHECK_DIR/INFO" \
    || { echo "错误：INFO 缺少 support_conf_folder=\"yes\"（DSM 将忽略 conf/privilege 并判定为 root 套件）" >&2; FAIL=1; }
grep -q '^checksum=' "$CHECK_DIR/INFO" \
    || { echo "错误：INFO 缺少 checksum" >&2; FAIL=1; }
grep -q '"subitems"' "$CHECK_DIR/WIZARD_UIFILES/install_uifile" \
    || { echo "错误：install_uifile 缺少 subitems 结构（向导会渲染为空白页）" >&2; FAIL=1; }
if [ "$(tar tzf "$CHECK_DIR/package.tgz" | grep -c '^\./')" -ne 0 ]; then
    echo "错误：package.tgz 成员名带 ./ 前缀" >&2
    FAIL=1
fi
if [ "$FAIL" -ne 0 ]; then
    rm -f "$OUT"
    exit 1
fi
echo "自检通过（run-as=package、support_conf_folder、checksum、向导结构、成员名合规）"
echo "已生成：$OUT"
