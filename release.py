#!/usr/bin/env python3
"""Plan, package and verify Windows releases for the WorkBuddy edition."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parent
BASE = "v0.1.3908"
REVISION = 7
UPSTREAM = "yetone/magpie-releases"
CUSTOM = re.compile(r"v(\d+)\.(\d+)\.(\d+)-workbuddy\.([1-9]\d*)")
STABLE = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
ARCHES = {"amd64": ("x64", 0x8664), "arm64": ("ARM64", 0xAA64)}
PARITY_TEST = "TestEveryRouteHasACommandOrIsNamed"
CLI_PACKAGE = "github.com/yetone/magpie/internal/cli"
MISSING_ROUTE = re.compile(
    r"\s*settings_parity_test\.go:\d+: ([A-Z]+ /api/\S+) has no command: "
    r"name the one that does what it does in cliForRoute, or say why there's none yet in notYet\s*"
)


def retry(command, **kwargs):
    for delay in (5, 15, None):
        try:
            return subprocess.run(command, check=True, **kwargs)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            if delay is None:
                raise
            print(f"{error}; retrying in {delay}s", file=sys.stderr, flush=True)
            time.sleep(delay)


def gh_api(endpoint):
    result = retry(["gh", "api", endpoint], stdout=subprocess.PIPE, text=True, timeout=120)
    return json.loads(result.stdout)


def parity(source):
    command = ["go", "test", "-json", "-tags", "nogui", "./internal/cli",
               "-run", f"^{PARITY_TEST}$", "-count=1"]
    result = subprocess.run(command, cwd=source, stdout=subprocess.PIPE, text=True)
    missing = set()
    unexpected = []
    ran = False
    failed = False
    for line in result.stdout.splitlines():
        event = json.loads(line)
        output = event.get("Output", "")
        print(output, end="", flush=True)
        if event.get("Action") == "build-fail" or event.get("FailedBuild"):
            unexpected.append(event)
        if event.get("Package") != CLI_PACKAGE or event.get("Test") != PARITY_TEST:
            continue
        ran |= event["Action"] == "run"
        failed |= event["Action"] == "fail"
        if output and not output.startswith((f"=== RUN   {PARITY_TEST}\n", f"--- FAIL: {PARITY_TEST} (")):
            route = MISSING_ROUTE.fullmatch(output)
            if route:
                missing.add(route[1])
            else:
                unexpected.append(event)
    if result.returncode == 0 and ran:
        return set()
    if result.returncode == 1 and ran and failed and missing and not unexpected:
        return missing
    raise ValueError(f"Could not isolate missing route registrations in {source}")


def check_parity(source):
    patched_missing = parity(source)
    if not patched_missing:
        return
    print("Comparing route parity with the untouched upstream commit.", flush=True)
    with tempfile.TemporaryDirectory(prefix="magpie-upstream-") as temp:
        clean = Path(temp) / "source"
        subprocess.run(["git", "-C", source, "worktree", "add", "--detach", clean, "HEAD"], check=True)
        try:
            upstream_missing = parity(clean)
        finally:
            subprocess.run(["git", "-C", source, "worktree", "remove", clean], check=True)
    new_missing = patched_missing - upstream_missing
    if new_missing:
        raise ValueError(f"Windows patch introduced missing route registrations: {', '.join(sorted(new_missing))}")
    print("::warning::Missing route registrations reproduced in upstream: " + ", ".join(sorted(patched_missing)))


def version(tag, pattern):
    match = pattern.fullmatch(tag)
    if not match:
        raise ValueError(f"Unexpected release tag {tag!r}")
    fields = tuple(map(int, match.groups()))
    if any(n > 65535 for n in fields):
        raise ValueError("Release version does not fit Windows file metadata")
    return fields


def plan(repo):
    latest = gh_api(f"repos/{UPSTREAM}/releases/latest")
    if latest["draft"] or latest["prerelease"]:
        raise ValueError("The upstream release must be stable")
    core = latest["tag_name"]
    fields = version(core, STABLE)
    if fields < version(BASE, STABLE):
        core, fields = BASE, version(BASE, STABLE)
    tag = f"{core}-workbuddy.{REVISION}"
    releases = gh_api(f"repos/{repo}/releases?per_page=100")
    current = [version(r["tag_name"], CUSTOM) for r in releases
               if not r["draft"] and not r["prerelease"] and CUSTOM.fullmatch(r["tag_name"])]
    if any(not CUSTOM.fullmatch(r["tag_name"]) for r in releases if not r["draft"]):
        raise ValueError("Use a dedicated Windows release repository")
    changed = not current or max(current) < (*fields, REVISION)
    outputs = {"tag": tag, "core": core, "winver": ".".join(map(str, (*fields, REVISION))),
               "changed": str(changed).lower()}
    print(json.dumps(outputs))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        for name, value in outputs.items():
            print(f"{name}={value}", file=out)


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def assets():
    for arch, (title, _) in ARCHES.items():
        yield f"magpie-windows-{arch}.exe"
        yield f"Magpie-Windows-{title}.zip"
    yield "SHA256SUMS.txt"


def check_exe(path, arch):
    with path.open("rb") as stream:
        header = stream.read(64)
        if header[:2] != b"MZ":
            raise ValueError(f"{path.name} is not a Windows executable")
        stream.seek(struct.unpack_from("<I", header, 60)[0])
        if stream.read(6) != b"PE\0\0" + struct.pack("<H", ARCHES[arch][1]):
            raise ValueError(f"{path.name} has the wrong architecture")


def package(source, target, tag, repo):
    version(tag, CUSTOM)
    target.mkdir(parents=True, exist_ok=True)
    for arch, (title, _) in ARCHES.items():
        name = f"Magpie-Windows-{title}"
        exe = source / "dist" / f"magpie-windows-{arch}.exe"
        check_exe(exe, arch)
        local_exe = target / exe.name
        local_exe.write_bytes(exe.read_bytes())
        instructions = (
            f"Magpie Windows {tag.split('-', 1)[0]} ({title})\n\n"
            "1. 从 Windows 托盘退出旧版 Magpie。\n"
            "2. 完整解压，打开解压出的文件夹，双击 magpie.exe。\n"
            "3. 在供应商页使用导入或导出 WorkBuddy 账号。\n"
            "4. 在设置里检查更新或开启自动检查。\n\n"
            f"更新渠道：https://github.com/{repo}/releases\n"
            "程序会验证 GitHub 提供的 SHA-256，再安装更新。\n"
            "导出的 JSON 含账号登录凭证，请妥善保管。\n"
            "程序未签名，Windows 可能显示未知发布者。\n"
        )
        zip_path = target / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(exe, f"{name}/magpie.exe")
            z.write(source / "LICENSE", f"{name}/LICENSE.txt")
            z.writestr(f"{name}/README.txt", ("\ufeff" + instructions).replace("\n", "\r\n").encode())
        with zipfile.ZipFile(zip_path) as z:
            if z.testzip() is not None:
                raise ValueError(f"{zip_path.name} failed ZIP validation")
    names = [name for name in assets() if name != "SHA256SUMS.txt"]
    (target / "SHA256SUMS.txt").write_text(
        "".join(f"{file_hash(target / name)}  {name}\n" for name in names), encoding="ascii"
    )


def verify(repo, tag, directory):
    version(tag, CUSTOM)
    matching = [r for r in gh_api(f"repos/{repo}/releases?per_page=100") if r["tag_name"] == tag]
    if len(matching) != 1:
        raise ValueError("Could not resolve the release draft")
    release = matching[0]
    expected = set(assets())
    uploaded = release["assets"]
    if not release["draft"] or release["prerelease"] or release["tag_name"] != tag:
        raise ValueError("Release is not the expected draft")
    if {a["name"] for a in uploaded} != expected or len(uploaded) != len(expected):
        raise ValueError("Draft has unexpected or missing files")
    for asset in uploaded:
        path = directory / asset["name"]
        if (asset["state"] != "uploaded" or asset["size"] != path.stat().st_size
                or asset.get("digest") != "sha256:" + file_hash(path)):
            raise ValueError(f"GitHub digest or size does not match {path.name}")


def main():
    command, *args = sys.argv[1:]
    if command == "plan":
        plan(*args)
    elif command == "retry":
        retry(args)
    elif command == "check-parity":
        check_parity(Path(args[0]).resolve())
    elif command == "package":
        source, target, tag, repo = args
        package(Path(source), Path(target), tag, repo)
    elif command == "verify":
        repo, tag, directory = args
        verify(repo, tag, Path(directory))
    else:
        raise ValueError(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
