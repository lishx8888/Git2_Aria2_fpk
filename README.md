# Aria2（群晖 DSM SPK 应用）

群晖 DSM 第三方套件（SPK），提供 Aria2 下载管理面板：支持 HTTP/FTP、BT/磁力下载，内置 BT-Tracker 与 DHT 网络，并集成 GitHub 链接加速下载。

- **内置 aria2c**：随包携带 aria2c 1.37.0（x86-64 静态编译），不依赖系统/社群套件，开箱即用
- **RPC 服务端代理**：前端不直连 aria2c，RPC 请求由 Bash CGI 转发，密钥不下发浏览器
- **桌面入口**：安装后在 DSM 主菜单出现 Aria2 图标，点击直接打开面板

> 架构：本包 `arch="x86_64"`，适用于 Intel/AMD CPU 的群晖（及绝大多数 x86 兼容 NAS）。ARM 机型需替换 `package/server/aria2c` 为 armv8 静态二进制并修改 `INFO` 的 `arch`。

## 功能特性

- HTTP/FTP、BT、磁力链下载，内置 BT-Tracker 列表，启用 DHT/DHT6、PEX、强制加密
- GitHub 加速：自动为 GitHub 链接添加加速前缀后提交下载，前缀可在面板「设置」中自定义
- 任务管理：查看下载中/等待中/已停止任务，暂停、继续、删除任务，清空已完成任务
- 自定义默认下载目录，配置持久化保存
- 安装向导弹窗设置 RPC 密钥与监听端口（端口占用会在安装前拦截）
- 下载完成自动把文件属主修正为下载目录属主

## 目录结构（SPK 源码布局）

```
Aria2/
├── INFO                        # 套件清单（套件名、版本、arch、入口等）
├── PACKAGE_ICON.PNG            # 套件图标（72px）
├── PACKAGE_ICON_256.PNG        # 套件图标（256px）
├── build.sh                    # 本地打包脚本，生成 .spk
├── conf/
│   ├── privilege               # 运行身份（run-as: root）
│   └── resource                # DSM 桌面入口注册（.url → 3rdparty CGI）
├── scripts/                    # 生命周期脚本
│   ├── common                  # 公共路径与函数（被各脚本 source）
│   ├── installer               # 安装向导（-e/-g/-s 协议，设置 RPC 密钥/端口）
│   ├── preinst                 # 安装前：端口占用检查
│   ├── postinst                # 安装后：建目录、渲染 aria2.conf、写钩子
│   ├── postupgrade             # 升级后：保留用户配置，刷新钩子/路径
│   ├── preuninst               # 卸载前：停止服务
│   ├── postuninst              # 卸载后：删除 @appdata 数据（保留下载文件）
│   └── start-stop-status       # 套件中心 start/stop/status
└── package/                    # 安装后展开到 /var/packages/Aria2/target
    ├── ui/
    │   ├── index.cgi           # Bash CGI：静态服务 + RPC 代理 + 面板配置接口
    │   └── images/             # 桌面入口图标（icon_64/icon_256）
    ├── www/                    # 前端面板（单文件 index.html）
    ├── template/
    │   └── aria2.tpl           # aria2.conf 模板，postinst 变量替换
    └── server/
        └── aria2c              # aria2c 1.37.0 x86-64 静态二进制
```

## 工作原理

```
浏览器 (package/www/index.html)
   │  /webman/3rdparty/Aria2/index.cgi/api/*
   ▼
package/ui/index.cgi (Bash CGI，DSM webman 执行)
   │  读取 @appdata/Aria2/aria2.conf 获取端口与密钥，注入 token:secret
   │  转发到 http://127.0.0.1:<rpc_port>/jsonrpc
   ▼
aria2c (target/server/aria2c，套件自管守护进程)
   │  配置：/volumeX/@appdata/Aria2/aria2.conf（由 aria2.tpl 渲染）
   ▼
下载目录 /volumeX/downloads（可在面板设置中修改）
```

1. 安装时 [scripts/](scripts/) 依次执行向导 → preinst（端口检查）→ 文件展开 → postinst（建目录、渲染配置、写钩子）
2. 套件中心通过 `start-stop-status` 启停 aria2c，PID 记录在 `@appdata/Aria2/aria2.pid`
3. 面板配置（加速前缀、下载目录）保存在 `@appdata/Aria2/ui.conf`

## 路径说明

| 用途 | 路径（以 /volume1 为例） |
| --- | --- |
| 安装目录 | `/var/packages/Aria2/target`（软链到 `/volume1/@appstore/Aria2`） |
| 数据目录 | `/volume1/@appdata/Aria2` |
| aria2 配置 | `@appdata/Aria2/aria2.conf` |
| 会话 / DHT | `@appdata/Aria2/aria2.session`、`dht.dat`、`dht6.dat` |
| aria2 日志 | `@appdata/Aria2/aria2.log`、`service.log` |
| 面板配置 | `@appdata/Aria2/ui.conf` |
| 默认下载目录 | `/volume1/downloads` |

卷号由 `SYNOPKG_PKGDEST_VOL` 自动推导，多卷环境也能正确定位。

## 打包

需要 Linux / WSL / macOS / Git Bash 环境（依赖 tar/gzip）：

```bash
chmod +x build.sh
./build.sh
# 产物：Aria2-x86_64-1.0.1-001.spk
```

SPK 为未签名包，安装方式：

1. DSM → 套件中心 → 右上角设置 → 「套件来源」信任等级设为「任何发行者」（或安装时勾选仍要安装）
2. 套件中心 → 手动安装 → 选择 `.spk` → 按向导设置 RPC 密钥/端口 → 完成
3. DSM 主菜单点击 Aria2 图标打开面板

## 配置说明

### 安装向导变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `rpc_secret` | RPC 访问密钥，仅服务端使用，不暴露给前端 | `aria2rpc_secret` |
| `rpc_port` | aria2c RPC 监听端口 | `6800` |

升级安装不弹向导，保留既有配置；如需修改密钥/端口，可 SSH 编辑 `@appdata/Aria2/aria2.conf` 后在套件中心重启 Aria2。

### 模板变量（aria2.tpl → aria2.conf）

| 占位符 | 来源 |
| --- | --- |
| `${PRC_SECRET}` | 向导变量 `rpc_secret` |
| `${RPC_PORT}` | 向导变量 `rpc_port` |
| `${DATA_DIR}` | `/volumeX/@appdata/Aria2` |
| `${DOWNLOAD_DIR}` | `/volumeX/downloads` |
| `${SCRIPT_PATH}` | `on-download-complete` 钩子路径 |

### 文件所有权

aria2c 以 root 运行，下载完成后 `on-download-complete` 钩子读取面板自定义目录（ui.conf 优先）或 aria2.conf 的 `dir=`，用 `stat -c %u:%g` 查询数字 uid:gid，属主非 root 即执行 `chown -R`，让下载文件归属共享文件夹属主；aria2.conf 同时设置 `umask=000` 兜底保证可访问。

## HTTP 接口（index.cgi）

经 `/webman/3rdparty/Aria2/index.cgi` 访问，均为 GET：

| 路径 | 说明 | 对应 aria2 RPC |
| --- | --- | --- |
| `/api/stat` | 全局统计（速度、任务数等） | `aria2.getGlobalStat` |
| `/api/active` | 下载中任务 | `aria2.tellActive` |
| `/api/waiting` | 等待中任务 | `aria2.tellWaiting` |
| `/api/stopped` | 已停止任务 | `aria2.tellStopped` |
| `/api/add?url=&dir=` | 新建下载（dir 可选） | `aria2.addUri` |
| `/api/pause?gid=` | 暂停任务 | `aria2.pause` |
| `/api/unpause?gid=` | 继续任务 | `aria2.unpause` |
| `/api/remove?gid=` | 移除已完成/出错任务 | `aria2.removeDownloadResult` |
| `/api/forceRemove?gid=` | 强制移除进行中任务 | `aria2.forceRemove` |
| `/api/purge` | 清空已完成任务结果 | `aria2.purgeDownloadResult` |
| `/api/config` | 读取面板配置（前缀、目录） | — |
| `/api/config/save?prefix=&dir=` | 保存面板配置 | — |
| 其他路径 | 静态文件服务（`www`），含目录穿越防护 | — |

## 卸载行为

卸载会删除 `/volumeX/@appdata/Aria2`（任务列表、会话、配置），**不会删除** `/volumeX/downloads` 中已下载的文件。

## 常见问题

**Q：安装时报端口被占用？**
RPC 默认端口 6800、BT/DHT 端口 6881-6999 可能被其他下载工具/Docker 容器占用。停止冲突服务，或在安装向导中更换 RPC 端口。

**Q：面板打不开？**
查看 `/volumeX/@appdata/Aria2/service.log` 与 `aria2.log`；确认套件状态为「运行中」。CGI 需读取同目录 `aria2.conf`，文件权限由 postinst 自动设置，请勿手工改为 600。

**Q：可以在 ARM 群晖上安装吗？**
不可以直接安装（`arch="x86_64"`）。需用 armv8 静态编译的 aria2c 替换 `package/server/aria2c`，并把 `INFO` 的 `arch` 改为 `armv8` 后重新 `./build.sh`。

**Q：RPC 密钥会泄露到浏览器吗？**
不会。前端只调用 `/api/*`，由 CGI 在服务端读取密钥并注入 `token:secret`，密钥始终不离开 NAS。

## 开源致谢

本应用基于以下开源项目：

- [aria2](https://github.com/aria2/aria2) — 下载内核 aria2c（HTTP/FTP/BT/磁力，支持 RPC 与 DHT）
- [CF-GitHub-Proxy](https://github.com/hubporg/CF-GitHub-Proxy) — GitHub 加速服务，面板默认/自定义加速前缀即基于该类公共代理实现

感谢上述项目作者与社区的贡献。
