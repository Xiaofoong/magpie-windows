# Magpie Windows WorkBuddy

Windows x64 和 ARM64 定制版，基于 MIT 许可的 [yetone/magpie](https://github.com/yetone/magpie)。供应商页提供 WorkBuddy 和 CodeBuddy 账号 JSON 导入、导出。

## 下载和使用

在 [Releases](https://github.com/Xiaofoong/magpie-windows/releases/latest) 下载 Windows GUI。Intel / AMD 电脑下载 `magpie-windows-amd64.exe`，ARM 电脑下载 `magpie-windows-arm64.exe`。

从托盘退出正在运行的 Magpie，再双击下载的 EXE。程序直接打开「供应商」页，可看到导入和导出。EXE 会在自己的目录中更新，并使用当前 Windows 用户的 Magpie 配置。

## 自动更新

Actions 每 5 分钟检查官方稳定版。有新核心时应用 WorkBuddy 补丁，测试、构建并校验发布文件。客户端在 **设置 → 版本** 检查这个仓库的发布版本。下载完成后可点重启更新，也可以在设置中开启自动重启。上游改动导致补丁或测试失败时，保留上一版。

GitHub 可能延迟定时任务，公开仓库长期无活动时也可能停用定时任务。可在 Actions 重新启用并手动运行。

## 账号迁移

进入 **供应商 → 导出 WorkBuddy 账号**，勾选账号或全选，选择保存文件夹。输出 `workbuddy-accounts.json`，已有同名文件时使用新文件名。该文件含选中账号的登录凭证，请妥善保管。

导入支持手机版相同格式，只保存还有效的访问令牌。原设备刷新令牌保留在原设备的登录中。已有账号会跳过。

## 维护

`workbuddy.patch` 相对于官方 `v0.1.3908`。修改定制代码后更新补丁并递增 `release.py` 的 `REVISION`，以便同一核心也能发出新版本。发布已经存在的版本应使用新的修订号。Windows EXE 沿用上游原生更新流程，文件未做 Authenticode 签名。
