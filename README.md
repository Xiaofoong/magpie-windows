# Magpie Windows WorkBuddy

Windows x64 和 ARM64 定制版，基于 MIT 许可的 [yetone/magpie](https://github.com/yetone/magpie)。供应商页提供 WorkBuddy 和 CodeBuddy 账号 JSON 导入、导出。

## 下载和使用

在 [Releases](https://github.com/Xiaofoong/magpie-windows/releases/latest) 下载 Windows 安装程序。Intel / AMD 电脑下载 `Magpie-Windows-x64-Setup.exe`，ARM 电脑下载 `Magpie-Windows-ARM64-Setup.exe`。先从托盘退出旧版 Magpie，再运行安装程序。

默认安装在当前用户的 `%LOCALAPPDATA%\Programs\magpie`，提供开始菜单和桌面快捷方式。以后从快捷方式打开。同一 Windows 用户的账号、设置和会话数据继续由 Magpie 保存在 `%USERPROFILE%\.config\magpie`，自定义了 `XDG_CONFIG_HOME` 时使用该目录。WebView2 的浏览器记录沿用安装前已有的配置目录，安装程序会检测 `magpie.exe` 和对应架构的下载版 EXE 数据目录。重装、升级和卸载均保留用户数据。

如果旧版使用程序旁边的 `data` 文件夹或 `.portable` 标记，请先备份该文件夹。安装版读取用户目录，需要迁移原来的便携版数据才能看到其中的记录。安装程序无法恢复已经删除的文件，意外断电时尚未保存的内容也可能丢失。

原有的独立 EXE 和 ZIP 也继续提供下载。程序直接打开「供应商」页，可看到导入和导出。安装后仍可在设置里检查更新。

## 自动更新

Actions 每 5 分钟检查官方稳定版。最新版有补丁冲突时，会依次尝试最多四个较早的官方稳定版，候选版本必须比已发布的 Windows 版更新。都不兼容时，本轮跳过发布，Actions 摘要会列出冲突版本和文件，已发布的版本仍可下载。

补丁成功应用后，必须通过测试、构建和文件校验才会发布。源码、依赖和发布文件的传输失败时最多重试两次。CLI 路由测试发现漏登记时，会在同一版官方原码上复测。官方已有的漏登记会记录为警告，定制版引入的问题仍会停止发布。构建配置提交后也会验证已发布的当前版本，验证通过时无需重复发版。

客户端在 **设置 → 版本** 检查这个仓库的发布版本。下载完成后可点重启更新，也可以在设置中开启自动重启。

GitHub 可能延迟定时任务，公开仓库长期无活动时也可能停用定时任务。可在 Actions 重新启用并手动运行。

## 账号迁移

进入 **供应商 → 导出 WorkBuddy 账号**，勾选账号或全选，选择保存文件夹。输出 `workbuddy-accounts.json`，已有同名文件时使用新文件名。该文件含选中账号的登录凭证，请妥善保管。

导入支持手机版相同格式，默认勾选「迁移到此电脑并自动续期」。文件需要包含有效的刷新凭据。确认后通过 WorkBuddy 插件验证并轮换凭据，保存可自动续期的登录。原设备可能需要重新登录。预览阶段不会续期或写入凭据。

取消勾选时只导入当前仍有效的访问授权，已有账号会跳过。仅含访问授权的文件无法自动续期，可在此电脑直接登录。账号记录会保留，授权被 WorkBuddy 撤销或刷新凭据失效时仍可能需要重新登录。

## 维护

`workbuddy.patch` 相对于官方 `v0.1.3908`。修改定制代码后更新补丁并递增 `release.py` 的 `REVISION`，以便同一核心也能发出新版本。发布已经存在的版本应使用新的修订号。Windows EXE 沿用上游原生更新流程，文件未做 Authenticode 签名。
