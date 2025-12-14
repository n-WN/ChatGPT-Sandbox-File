# ChatGPT-Sandbox-File

## Use

Package the files within the ChatGPT Sandbox to see what new features are available and how the old features are implemented.

打包 ChatGPT Sandbox 内的文件，看看又有什么新功能，以及老功能是如何实现的

灵感来自: 

Inspiration from:
- https://x.com/elias_judin/status/1999479682190966852?s=20
- https://x.com/gasikaramada/status/1999836738009641138

> OpenAI 被抓到在产品内部使用 Skill 文件，这代表着Claude 的 Skills 已经成为事实标准。

[Goto Skills](home/oai/skills)

## Prompt

Analyze the entire sandbox to identify which files are present in standard Linux or not by default in Linux, and which operation tools are packaged within it.

分析整个 sandbox，有哪些常规linux或者说linux默认没有的文件，操作工具打包

<img width="1395" height="883" alt="截屏2025-12-14 22 51 44" src="https://github.com/user-attachments/assets/0ecac26b-4a13-4532-93d8-2070766f5f9e" />


## Code

最终使用了以下代码进行操作

```python
import os, zipfile, time, stat

start = time.time()

zip_path = "/mnt/data/sandbox_nondefault_curated_10M.zip"
report_path = "/mnt/data/sandbox_nondefault_curated_10M_report.txt"

targets = [
    "/.dockerenv",
    "/openai",
    "/opt/terminal-server",
    "/opt/novnc",
    "/opt/granola-cli",
    "/opt/entrypoint",
    "/opt/apply_patch",
    "/home/oai/skills",
    "/home/oai/share",
    "/home/oai/redirect.html",
]

runtime_dirs = [
    "/opt/nvm",
    "/opt/pyvenv",
    "/opt/pyvenv-python-tool",
    "/opt/python-tool",
    "/opt/imagemagick",
]

allow_ext = {
    ".sh",".bash",".zsh",
    ".py",".pyi",".pyc",
    ".js",".ts",".mjs",".cjs",".json",".yml",".yaml",".toml",
    ".ini",".cfg",".conf",".env",
    ".md",".txt",".rst",
    ".html",".css",
    ".lock",".npmrc",".nvmrc",
    ".xml"
}

allow_names = {
    "Dockerfile","Makefile","LICENSE","LICENSE.txt","LICENSE.md",
    "README","README.txt","README.md","NOTICE","NOTICE.txt","NOTICE.md",
    ".gitignore",".editorconfig"
}

exclude_dir_names = {
    ".git","__pycache__","node_modules",".venv","venv","site-packages",
    "dist","build",".cache",".npm",".pnpm-store",".yarn","yarn_cache",
    "bin","lib","lib64","include","share"
}

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

added = 0
skipped = 0
skip_reasons = []

def add_file(z, full_path):
    global added, skipped
    try:
        st = os.stat(full_path, follow_symlinks=False)
        if not stat.S_ISREG(st.st_mode):
            skipped += 1
            return
        if st.st_size > MAX_FILE_BYTES:
            skipped += 1
            skip_reasons.append((full_path, f"too large ({st.st_size})"))
            return
        arcname = full_path.lstrip("/")
        z.write(full_path, arcname)
        added += 1
    except Exception as e:
        skipped += 1
        skip_reasons.append((full_path, f"error: {e}"))

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as z:
    for t in targets:
        if not os.path.exists(t):
            continue
        if os.path.isfile(t):
            add_file(z, t)
        else:
            for root, dirs, files in os.walk(t, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_dir_names]
                for f in files:
                    add_file(z, os.path.join(root, f))

    for rd in runtime_dirs:
        if not os.path.exists(rd):
            continue
        for root, dirs, files in os.walk(rd, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude_dir_names]
            for f in files:
                path = os.path.join(root, f)
                base = os.path.basename(path)
                ext = os.path.splitext(base)[1]
                if base in allow_names or ext in allow_ext:
                    add_file(z, path)

elapsed = time.time() - start

with open(report_path, "w", encoding="utf-8") as rep:
    rep.write("Curated sandbox packaging report (10MB cap)\n")
    rep.write(f"ZIP: {zip_path}\n")
    rep.write(f"Added files: {added}\n")
    rep.write(f"Skipped files: {skipped}\n")
    rep.write(f"Max per-file size: {MAX_FILE_BYTES} bytes\n")
    rep.write(f"Elapsed: {elapsed:.2f}s\n\n")
    rep.write("Skipped examples:\n")
    for p, r in skip_reasons[:200]:
        rep.write(f"- {p}: {r}\n")

(zip_path, report_path, added, skipped, elapsed)
```

```python
import os, hashlib, pathlib, time

paths = [
    "/mnt/data/sandbox_nondefault_curated_10M.zip",
    "/mnt/data/sandbox_nondefault_curated_10M_report.txt",
]

info = {}
for p in paths:
    if os.path.exists(p):
        st = os.stat(p)
        # quick hash for integrity (stream)
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024*1024), b""):
                h.update(chunk)
        info[p] = {
            "size_bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
            "sha256": h.hexdigest(),
        }
    else:
        info[p] = None

info
```
