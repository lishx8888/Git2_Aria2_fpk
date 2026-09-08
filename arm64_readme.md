# ARM64 打包说明

本文档说明将本 FPK 包从 x86-64 架构迁移到 ARM64 (aarch64) 架构需要修改的位置。

## 一、架构相关 vs 架构无关文件

| 文件 / 目录                     | 是否架构相关 | 说明                                    |
| ------------------------------- | ------------ | --------------------------------------- |
| `app/server/aria2c`           | **是** | ELF 可执行二进制，必须替换为 ARM64 版本 |
| `manifest`                    | **是** | `platform` 字段需改为 `arm64`       |
| `app/ui/index.cgi`            | 否           | Bash 脚本，与架构无关                   |
| `app/template/aria2.tpl`      | 否           | Aria2 配置模板，文本文件                |
| `app/www/*`                   | 否           | 前端 HTML/CSS/JS/图片，与架构无关       |
| `app/ui/images/*`             | 否           | 图标资源，与架构无关                    |
| `cmd/main`                    | 否           | 生命周期脚本，Bash                      |
| `cmd/install_callback`        | 否           | 安装回调，Bash                          |
| `cmd/config_callback`         | 否           | 配置回调，Bash                          |
| `cmd/uninstall_callback`      | 否           | 卸载回调，Bash                          |
| `cmd/upgrade_callback`        | 否           | 升级回调，Bash                          |
| `ICON.PNG` / `ICON_256.PNG` | 否           | 应用图标，与架构无关                    |

**结论：仅需修改 2 处**——`manifest` 中的 `platform` 字段和 `app/server/aria2c` 二进制文件。

## 二、需要替换的文件清单

### 1. `app/server/aria2c`（核心二进制）

**当前状态：**

- 架构：ELF 64-bit, x86-64 (机器类型 0x3E / EM_X86_64)
- 大小：43,480,904 字节（约 41 MB）
- 版本：aria2c 1.37.0

**替换方法：**

获取 aria2 的 ARM64 静态编译版本（建议选择 musl 静态链接版本以获得最佳兼容性）：

```bash
# 方式 A：从官方 release 下载
# 访问 https://github.com/aria2/aria2/releases
# 选择 aria2-1.37.0-aarch64-linux-musl 思路相近的静态构建包

# 方式 B：在 ARM64 设备上自行编译
# 需要依赖：libssl, libcares, libexpat, zlib, libcpp-allocator 等
git clone https://github.com/aria2/aria2.git
cd aria2
git checkout release-1.37.0
autoreconf -i
./configure --enable-static --disable-shared \
    --with-musl \
    --without-libgmp --without-libnettle \
    ARIA2_STATIC=yes
make -j$(nproc)

# 校验产物
file src/aria2c
# 期望输出包含：ELF 64-bit LSB executable, ARM aarch64

# 替换
cp src/aria2c /path/to/this/repo/app/server/aria2c
chmod +x /path/to/this/repo/app/server/aria2c
```

**替换后验证：**

```bash
# 检查 ELF 头
xxd app/server/aria2c | head -1
# ARM64 期望开头：7f 45 4c 46 02 01 01 03 ... 02 00 b7 00
#                       ELF magic     64-bit LE    EM_AARCH64 (0xB7)
```

ARM64 二进制 ELF 头特征：

- Byte 4: `02` (ELFCLASS64，64位)
- Byte 5: `01` (小端)
- Bytes 18-19: `B7 00` (0x00B7 = EM_AARCH64)

对比 x86-64 二进制：bytes 18-19 为 `3E 00` (0x003E = EM_X86_64)。

### 2. `manifest`（应用清单）

**当前内容（第 5 行）：**

```
platform                   = x86
```

**改为：**

```
platform                   = arm64
```

> 若飞牛 OS 文档对 `platform` 字段的命名规则不同（如使用 `aarch64`），请以飞牛 FPK 开发文档为准。参考：https://developer.fnnas.com/docs/category/开发指南/

## 三、其他可选修改

### 1. 版本号（可选）

若 ARM64 版本作为独立发布版本，建议在 [manifest](manifest) 中更新：

```
version                    = 1.0.1-arm64
```

或保持版本号一致，仅通过 `platform` 字段区分。

### 2. changelog（可选）

```
changelog                  = 新增 ARM64 (aarch64) 架构支持
```

### 3. checksum（重要）

飞牛 FPK 打包工具会根据最终生成的包计算校验和并填入 `manifest` 的 `checksum` 字段。**修改二进制后必须重新打包并重新生成 checksum**，否则安装时会校验失败。

打包流程通常为：

```bash
# 在飞牛打包环境中执行
fpk-build /path/to/this/repo
# 打包工具会自动更新 checksum 字段
```

## 四、配置文件路径与架构无关

以下路径在所有架构下保持一致（飞牛 OS 标准路径）：

| 用途           | 路径                                                   |
| -------------- | ------------------------------------------------------ |
| 应用安装目录   | `/var/apps/Aria2/target`                             |
| 应用数据目录   | `/var/apps/Aria2/shares/data`                        |
| aria2 配置文件 | `/var/apps/Aria2/shares/data/aria2.conf`             |
| aria2 会话文件 | `/var/apps/Aria2/shares/data/aria2.session`          |
| DHT 数据       | `/var/apps/Aria2/shares/data/dht.dat` / `dht6.dat` |
| 日志文件       | `/var/apps/Aria2/shares/data/aria2.log`              |
| 面板自定义配置 | `/var/apps/Aria2/shares/data/ui.conf`                |
| 静态资源       | `/var/apps/Aria2/target/www`                         |

这些路径在 [app/template/aria2.tpl](app/template/aria2.tpl)、[app/ui/index.cgi](app/ui/index.cgi) 和 [cmd/main](cmd/main) 中硬编码引用，ARM64 版本无需修改。

## 五、验证清单

打包前请按以下步骤验证：

- [ ] `app/server/aria2c` 已替换为 ARM64 (aarch64) 二进制
- [ ] 通过 `file` 或 `xxd` 命令确认新二进制的机器类型为 `0xB7` (EM_AARCH64)
- [ ] `app/server/aria2c` 具有可执行权限（`chmod +x`）
- [ ] [manifest](manifest) 中 `platform` 字段已改为 `arm64`
- [ ] 在 ARM64 设备上实测：`/path/to/aria2c --version` 正常输出
- [ ] 在 ARM64 设备上实测：`aria2c --conf-path=...` 可正常启动 RPC
- [ ] 重新打包并生成新的 `checksum`
- [ ] 在飞牛 OS ARM64 设备上安装并验证应用可启动
- [ ] 验证面板 UI、GitHub 加速、任务管理、配置持久化等功能正常

## 六、常见问题

**Q：能否使用 glibc 动态链接版本的 aria2c？**
A：建议优先使用 musl 静态链接版本，避免对飞牛 OS 系统库版本的依赖，兼容性更好。若使用动态链接版本，需确认飞牛 OS 的 glibc 版本满足要求。

**Q：ARM64 二进制大小为何与 x86-64 不同？**
A：不同架构的指令集不同，二进制大小会有差异，这是正常现象。功能完全一致。

**Q：是否需要修改 `aria2.tpl` 中的 `file-allocation=falloc`？**
A：不需要。falloc 是 aria2 的功能选项，与底层文件系统相关，与 CPU 架构无关。只要目标文件系统（ext4/xfs 等）支持 fallocate 系统调用即可，ARM64 设备通常都支持。

**Q：BT-Tracker 列表、DHT 节点是否需要修改？**
A：不需要。这些是网络资源，与架构无关。

**Q：前端 UI 资源是否需要重新构建？**
A：不需要。[app/www/](app/www/) 下都是纯 HTML/CSS/JS，浏览器渲染，与服务器架构无关。
