# Aria2（飞牛 fnOS FPK 应用）

飞牛 fnOS 第三方应用包（FPK），提供 Aria2 下载管理面板：支持 HTTP/FTP、BT/磁力下载，内置 BT-Tracker 与 DHT 网络，并集成 GitHub 链接加速下载。

- **不内置二进制**：通过软链接复用飞牛系统自带的 `/usr/bin/aria2c`，包体积极小且随系统升级
- **RPC 服务端代理**：前端不直接连接 aria2c，RPC 请求由服务端 CGI 转发，RPC 密钥不下发浏览器，局域网与 fnConnect 远程访问均可使用
- **零端口配置**：无需手动填写地址/密钥，打开面板即用

## 功能特性

- HTTP/FTP、BT、磁力链下载，内置 BT-Tracker 列表，启用 DHT/DHT6、PEX、强制加密
- GitHub 加速：自动为 GitHub 链接添加加速前缀后提交下载，前缀可在面板「设置」中自定义
- 任务管理：查看下载中/等待中/已停止任务，暂停、继续、删除任务，清空已完成任务
- 自定义默认下载目录，配置持久化保存
- 安装向导可自定义 RPC 密钥与监听端口
- 卸载向导支持「保留数据 / 删除数据」二选一
- 软链接自愈：启动时若发现 aria2c 软链接缺失会自动重建

## 工作原理

```
浏览器 (app/www/index.html)
   │  /cgi/ThirdParty/Aria2/index.cgi/api/*
   ▼
app/ui/index.cgi (Bash CGI)
   │  读取 aria2.conf 获取端口与密钥，注入 token:secret
   │  转发到 http://127.0.0.1:<rpc_port>/jsonrpc
   ▼
aria2c (系统 /usr/bin/aria2c 的软链接)
   │  配置：shares/data/aria2.conf（由 aria2.tpl 渲染生成）
   ▼
下载目录 shares/Download
```

1. 安装/修改配置时，[cmd/install_callback](cmd/install_callback)、[cmd/config_callback](cmd/config_callback) 负责：
   - 创建软链接 `app/server/aria2c -> /usr/bin/aria2c`
   - 用 `sed` 将 [app/template/aria2.tpl](app/template/aria2.tpl) 中的变量替换后生成 `aria2.conf`
   - 创建下载目录及 `aria2.session`、`dht.dat`、`dht6.dat` 等空文件
2. [cmd/main](cmd/main) 负责进程启停（start/stop/status），启动前校验软链接，缺失则重建；PID 记录在 `app.pid`
3. [app/ui/index.cgi](app/ui/index.cgi) 同时承担静态文件服务（`app/www`）与 RPC 代理，面板配置（加速前缀、下载目录）保存在 `ui.conf`

## 目录结构

```
Aria2/
├── manifest                # FPK 应用清单（应用名、版本、platform 等）
├── ICON.PNG / ICON_256.PNG # 应用图标
├── app/
│   ├── ui/
│   │   ├── index.cgi       # Bash CGI：静态服务 + RPC 代理 + 面板配置接口
│   │   ├── config          # 桌面入口配置（iframe 指向 index.cgi）
│   │   └── images/         # 桌面图标
│   ├── www/                # 前端面板（单文件 index.html，浏览器直出）
│   ├── server/             # 安装时生成 aria2c 软链接（包内仅占位 README.txt）
│   └── template/
│       └── aria2.tpl       # aria2.conf 模板，安装时变量替换
├── cmd/                    # 生命周期脚本（Bash）
│   ├── main                # 启动/停止/状态，含软链接自愈
│   ├── install_callback    # 安装后：建软链接、生成配置、初始化数据文件
│   ├── config_callback     # 配置变更后：重建软链接、重新生成配置
│   ├── uninstall_callback  # 卸载后：按向导选择保留或删除数据
│   └── *_init / upgrade_*  # 预留钩子（当前为空实现）
├── config/
│   ├── privilege           # 运行身份（run-as: package）
│   └── resource            # 数据共享目录声明（data、Download）
└── wizard/                 # 安装/配置/卸载向导弹单
    ├── install             # RPC 密钥、RPC 端口
    ├── config              # 同上
    └── uninstall           # 保留 / 删除数据
```

## 打包与多架构

本包不含任何架构相关二进制，全部脚本与前端均与 CPU 架构无关。

**打不同架构的包时，只需修改 [manifest](manifest) 中的 `platform` 字段：**

```
platform = x86      # x86-64 设备
platform = arm      # ARM64 (aarch64) 设备（飞牛枚举值为 arm，不是 arm64）
```

> 注意：不要填 `all`。飞牛规范中 `all` 标注为"适用于 Docker 应用，即将支持"，原生 FPK 应用填写后安装端可能报"应用包不符合系统要求"。当前需分别打 x86、arm 两个包（除该字段外内容完全相同）。

前提条件：目标设备的飞牛系统需自带 `/usr/bin/aria2c`（x86 固件已确认自带，ARM 固件请在实机用 `ls -l /usr/bin/aria2c` 确认）。若目标系统不自带，需回退为内置对应架构静态编译二进制的方案。

打包在飞牛打包环境中执行，`checksum` 字段由打包工具自动计算，无需手动维护：

```bash
fpk-build /path/to/this/repo
```

## 配置说明

### 向导变量（安装/配置页）

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `rpc_secret` | RPC 访问密钥，仅服务端使用，不暴露给前端 | `aria2rpc_secret` |
| `rpc_port` | aria2c RPC 监听端口 | `6800` |

### 模板变量（aria2.tpl → aria2.conf）

[app/template/aria2.tpl](app/template/aria2.tpl) 中以下占位符在安装/配置时被替换：

| 占位符 | 来源 |
| --- | --- |
| `${PRC_SECRET}` | 向导变量 `rpc_secret` |
| `${RPC_PORT}` | 向导变量 `rpc_port` |
| `${DOWNLOAD_DIR}` | 数据共享目录下的 `Download` |
| `${SCRIPT_PATH}` | `on-download-complete` 钩子脚本路径 |

### 文件所有权

aria2c 以 root 身份运行（`config/privilege` 中 `run-as: root`），下载完成后通过 `on-download-complete` 钩子脚本自动将文件 chown 为下载目录属主（即飞牛登录用户）。脚本逻辑：钩子与配置文件同目录，运行时从自身位置定位 `ui.conf`（面板自定义目录优先）与 `aria2.conf`（默认目录兜底），读取 `dir=` 后用 `stat -c %u:%g` 查询数字 uid:gid（保留用户组，如 `td:Users`），属主非 root 即执行 `chown -R`。同时 aria2.conf 设置 `umask=000` 确保文件创建时所有用户可访问。

### 面板配置（ui.conf）

面板右上角「设置」中的两项保存在 `shares/data/ui.conf`：

| 键 | 说明 |
| --- | --- |
| `prefix` | GitHub 加速前缀，提交 GitHub 链接时自动拼接 |
| `dir` | 默认下载目录，留空时回退为 aria2.conf 中的 `dir` |

## HTTP 接口（index.cgi）

所有接口经 `/cgi/ThirdParty/Aria2/index.cgi` 访问，均为 GET：

| 路径 | 说明 | 对应 aria2 RPC |
| --- | --- | --- |
| `/api/stat` | 全局统计（速度、任务数等） | `aria2.getGlobalStat` |
| `/api/active` | 下载中任务 | `aria2.tellActive` |
| `/api/waiting` | 等待中任务 | `aria2.tellWaiting` |
| `/api/stopped` | 已停止任务 | `aria2.tellStopped` |
| `/api/add?url=&dir=` | 新建下载（dir 可选） | `aria2.addUri` |
| `/api/pause?gid=` | 暂停任务 | `aria2.pause` |
| `/api/unpause?gid=` | 继续任务 | `aria2.unpause` |
| `/api/remove?gid=` | 移除已完成/出错/已移除任务 | `aria2.removeDownloadResult` |
| `/api/forceRemove?gid=` | 强制移除进行中任务 | `aria2.forceRemove` |
| `/api/purge` | 清空已完成任务结果 | `aria2.purgeDownloadResult` |
| `/api/config` | 读取面板配置（前缀、目录） | — |
| `/api/config/save?prefix=&dir=` | 保存面板配置 | — |
| 其他路径 | 静态文件服务（`app/www`），含目录穿越防护 | — |

## 数据与路径

应用安装后使用飞牛标准路径（脚本中通过 `TRIM_APPDEST`、`TRIM_DATA_SHARE_PATHS`、`TRIM_PKGVAR` 环境变量获取）：

| 用途 | 路径 |
| --- | --- |
| 应用安装目录 | `/var/apps/Aria2/target` |
| 数据目录 | `/var/apps/Aria2/shares/data` |
| 下载目录 | `/var/apps/Aria2/shares/Download` |
| aria2 配置 | `shares/data/aria2.conf` |
| 会话 / DHT | `shares/data/aria2.session`、`dht.dat`、`dht6.dat` |
| aria2 日志 | `shares/data/aria2.log` |
| 面板配置 | `shares/data/ui.conf` |
| 启停日志 | `shares/info.log` |
| 进程 PID | `TRIM_PKGVAR/app.pid` |

## 常见问题

**Q：面板打不开 / 任务列表加载失败？**
查看 `shares/info.log` 与 `shares/data/aria2.log`。先确认软链接是否存在且可执行：`ls -l /var/apps/Aria2/target/server/aria2c`，应为指向 `/usr/bin/aria2c` 的软链接；缺失时重启应用会自动重建。

**Q：aria2c 启动失败，提示端口占用？**
RPC 默认端口 6800、BT/DHT 端口 6881-6999 可能被其他实例（如 Docker 中的 aria2 容器）占用。停止冲突服务，或在应用配置页修改 RPC 端口后重新生成配置。

**Q：换架构需要重新准备二进制吗？**
不需要。包内不含二进制，切换架构只需改 `manifest` 的 `platform` 字段，详见上文「打包与多架构」。

**Q：RPC 密钥会泄露到浏览器吗？**
不会。前端只调用 `/api/*`，由 CGI 在服务端读取 `aria2.conf` 中的密钥并注入 `token:secret`，密钥始终不离开设备。
