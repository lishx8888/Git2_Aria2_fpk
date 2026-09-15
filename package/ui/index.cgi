#!/bin/bash

# 本脚本位于 target/ui/index.cgi，安装根目录为其上一级
SELF_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
TARGET_DIR="$(cd "$SELF_DIR/.." 2>/dev/null && pwd)"

# 由 postinst 生成的路径配置（WWW_DIR/DATA_DIR/CONF_FILE/UI_CONF_FILE）
PATHS_CONF="$TARGET_DIR/conf/paths.conf"
WWW_DIR="$TARGET_DIR/www"
DATA_DIR=""
CONF_FILE=""
UI_CONF_FILE=""
[ -f "$PATHS_CONF" ] && . "$PATHS_CONF"
: "${CONF_FILE:=$DATA_DIR/aria2.conf}"
: "${UI_CONF_FILE:=$DATA_DIR/ui.conf}"

# 静态文件根目录（自研面板）
BASE_PATH="$WWW_DIR"

# aria2 RPC 查询用到的字段
KEYS_JSON='"gid","totalLength","completedLength","downloadSpeed","uploadSpeed","status","files","bittorrent","dir","connections","errorCode","errorMessage"'

# 如果 CGI 环境没有 QUERY_STRING，从 REQUEST_URI 兜底解析
if [ -z "${QUERY_STRING:-}" ]; then
    case "$REQUEST_URI" in
        *\?*) QUERY_STRING="${REQUEST_URI#*\?}" ;;
        *) QUERY_STRING="" ;;
    esac
fi

# URL 解码（+ 转空格，%XX 转字节）
url_decode() {
    local s="${1//+/ }"
    printf '%b' "${s//%/\\x}"
}

# 最小 JSON 字符串转义（转义反斜杠和双引号）
json_escape() {
    local s="${1}"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    printf '%s' "$s"
}

# 读取 conf 中的真实 RPC 端口与密钥
read_conf() {
    RPC_PORT=""
    RPC_SECRET=""
    DOWNLOAD_DIR=""
    if [ -f "$CONF_FILE" ]; then
        RPC_PORT=$(sed -n 's/^[[:space:]]*rpc-listen-port[[:space:]]*=[[:space:]]*//p' "$CONF_FILE" 2>/dev/null | head -n 1 | tr -d '[:space:]')
        RPC_SECRET=$(sed -n 's/^[[:space:]]*rpc-secret[[:space:]]*=[[:space:]]*//p' "$CONF_FILE" 2>/dev/null | head -n 1 | tr -d '\r')
        DOWNLOAD_DIR=$(sed -n 's/^[[:space:]]*dir[[:space:]]*=[[:space:]]*//p' "$CONF_FILE" 2>/dev/null | head -n 1 | tr -d '\r')
    fi
    RPC_PORT="${RPC_PORT:-6800}"
}

# 读取面板自定义配置（前缀 / 目录）
read_ui_conf() {
    UI_PREFIX=""
    UI_DIR=""
    if [ -f "$UI_CONF_FILE" ]; then
        UI_PREFIX=$(sed -n 's/^[[:space:]]*prefix[[:space:]]*=[[:space:]]*//p' "$UI_CONF_FILE" 2>/dev/null | head -n 1 | tr -d '\r')
        UI_DIR=$(sed -n 's/^[[:space:]]*dir[[:space:]]*=[[:space:]]*//p' "$UI_CONF_FILE" 2>/dev/null | head -n 1 | tr -d '\r')
    fi
}

# 写入面板自定义配置
write_ui_conf() {
    local prefix="$1"
    local dir="$2"
    mkdir -p "$(dirname "$UI_CONF_FILE")"
    : > "$UI_CONF_FILE"
    if [ -n "$prefix" ]; then printf 'prefix=%s\n' "$prefix" >> "$UI_CONF_FILE"; fi
    if [ -n "$dir" ]; then printf 'dir=%s\n' "$dir" >> "$UI_CONF_FILE"; fi
}

# 从 QUERY_STRING 中取指定 key 并解码
get_param() {
    local key="$1"
    local qs="${QUERY_STRING:-}"
    local pair val=""
    local oldIFS="$IFS"
    IFS='&'
    for pair in $qs; do
        case "$pair" in
            "${key}="*) val="${pair#${key}=}" ;;
        esac
    done
    IFS="$oldIFS"
    url_decode "$val"
}

# 调用 aria2 HTTP JSON-RPC
rpc_call() {
    local payload="$1"
    if command -v curl >/dev/null 2>&1; then
        curl -s --max-time 5 -X POST "http://127.0.0.1:${RPC_PORT}/jsonrpc" \
            -H "Content-Type: application/json" \
            --data-binary "$payload"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- --timeout=5 \
            --header="Content-Type: application/json" \
            --post-data="$payload" \
            "http://127.0.0.1:${RPC_PORT}/jsonrpc"
    else
        echo '{"jsonrpc":"2.0","id":"1","error":{"code":-1,"message":"no curl or wget available"}}'
    fi
}

emit_json_header() {
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
}

emit_error() {
    local msg="$1"
    emit_json_header
    echo "{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"error\":{\"code\":-1,\"message\":\"$(json_escape "$msg")\"}}"
    exit 0
}

# 统一的 RPC 输出：$1=method，$2=token 之后的 params 片段（可为空）
rpc_emit() {
    local method="$1"
    local rest="$2"
    read_conf
    local token
    if [ -n "$RPC_SECRET" ]; then
        token="\"token:$(json_escape "$RPC_SECRET")\""
    else
        token="\"\""
    fi

    local payload
    if [ -n "$rest" ]; then
        payload="{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"$method\",\"params\":[$token,$rest]}"
    else
        payload="{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"$method\",\"params\":[$token]}"
    fi

    emit_json_header
    rpc_call "$payload"
    exit 0
}

# 静态文件服务（沿用原逻辑）
serve_static() {
    local rel="$1"
    if [ -z "$rel" ] || [ "$rel" = "/" ]; then
        rel="/index.html"
    fi

    local target="${BASE_PATH}${rel}"

    if echo "$target" | grep -q '\.\.'; then
        echo "Status: 400 Bad Request"
        echo "Content-Type: text/plain; charset=utf-8"
        echo ""
        echo "Bad Request"
        exit 0
    fi

    if [ ! -f "$target" ]; then
        echo "Status: 404 Not Found"
        echo "Content-Type: text/plain; charset=utf-8"
        echo ""
        echo "404 Not Found: ${rel}"
        exit 0
    fi

    local ext mime
    ext="${target##*.}"
    case "$ext" in
        html|htm) mime="text/html; charset=utf-8" ;;
        css) mime="text/css; charset=utf-8" ;;
        js) mime="application/javascript; charset=utf-8" ;;
        jpg|jpeg) mime="image/jpeg" ;;
        png) mime="image/png" ;;
        gif) mime="image/gif" ;;
        svg) mime="image/svg+xml" ;;
        txt|log) mime="text/plain; charset=utf-8" ;;
        *) mime="application/octet-stream" ;;
    esac

    echo "Content-Type: $mime"
    echo ""
    cat "$target"
    exit 0
}

# 解析 index.cgi 后面的路径
URI_NO_QUERY="${REQUEST_URI%%\?*}"
REL_PATH="/"
case "$URI_NO_QUERY" in
    *index.cgi*) REL_PATH="${URI_NO_QUERY#*index.cgi}" ;;
esac

case "$REL_PATH" in
    /api/stat)         rpc_emit aria2.getGlobalStat "" ;;
    /api/config)
        read_conf
        read_ui_conf
        emit_json_header
        P="$UI_PREFIX"
        D="$UI_DIR"
        if [ -z "$D" ]; then D="$DOWNLOAD_DIR"; fi
        echo "{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"result\":{\"prefix\":\"$(json_escape "$P")\",\"dir\":\"$(json_escape "$D")\"}}"
        exit 0 ;;
    /api/config/save)
        P="$(get_param prefix)"
        D="$(get_param dir)"
        write_ui_conf "$P" "$D"
        emit_json_header
        echo "{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"result\":{\"ok\":true}}"
        exit 0 ;;
    /api/active)       rpc_emit aria2.tellActive "[$KEYS_JSON]" ;;
    /api/waiting)      rpc_emit aria2.tellWaiting "0,1000,[$KEYS_JSON]" ;;
    /api/stopped)      rpc_emit aria2.tellStopped "0,1000,[$KEYS_JSON]" ;;
    /api/purge)        rpc_emit aria2.purgeDownloadResult "" ;;
    /api/add)
        URL="$(get_param url)"
        if [ -z "$URL" ]; then emit_error "缺少 url 参数"; fi
        DIR="$(get_param dir)"
        if [ -n "$DIR" ]; then
            rpc_emit aria2.addUri "[\"$(json_escape "$URL")\"],{\"dir\":\"$(json_escape "$DIR")\"}"
        else
            rpc_emit aria2.addUri "[\"$(json_escape "$URL")\"],{}"
        fi ;;
    /api/pause)
        GID="$(get_param gid)"
        if [ -z "$GID" ]; then emit_error "缺少 gid 参数"; fi
        rpc_emit aria2.pause "\"$(json_escape "$GID")\"" ;;
    /api/unpause)
        GID="$(get_param gid)"
        if [ -z "$GID" ]; then emit_error "缺少 gid 参数"; fi
        rpc_emit aria2.unpause "\"$(json_escape "$GID")\"" ;;
    /api/remove)
        GID="$(get_param gid)"
        if [ -z "$GID" ]; then emit_error "缺少 gid 参数"; fi
        rpc_emit aria2.removeDownloadResult "\"$(json_escape "$GID")\"" ;;
    /api/forceRemove)
        GID="$(get_param gid)"
        if [ -z "$GID" ]; then emit_error "缺少 gid 参数"; fi
        rpc_emit aria2.forceRemove "\"$(json_escape "$GID")\"" ;;
    *)
        serve_static "$REL_PATH" ;;
esac
