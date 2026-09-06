#!/usr/bin/env python3
"""Package committed runtime code only; never include credentials or account data."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tarfile


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_absolute():
        raise SystemExit("Usage: package_release.py /absolute/output/directory")
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo)
    if git("status", "--porcelain").strip():
        raise SystemExit("Commit reviewed changes first; packaging requires a clean worktree.")
    sha = git("rev-parse", "HEAD").decode().strip()
    paths = ("app", "static", "free_engine", "schemas", "fixtures", "requirements.txt")
    source = git("archive", "--format=tar", "HEAD", *paths)
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    package = output / ("quantradar-" + sha + ".tar.gz")
    with package.open("xb") as handle, tarfile.open(fileobj=handle, mode="w:gz") as target:
        checksums = []
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o644
            target.addfile(info, io.BytesIO(data))
            checksums.append(hashlib.sha256(data).hexdigest() + "  " + name)
        with tarfile.open(fileobj=io.BytesIO(source)) as archive:
            for entry in archive.getmembers():
                if entry.isdir():
                    continue
                assert entry.isfile(), "Release must not contain symlinks or special files"
                assert not any(part in {".env", "data", ".cache", "__pycache__"} for part in Path(entry.name).parts)
                add(entry.name, archive.extractfile(entry).read())
        add("SOURCE_HEAD", (sha + "\n").encode())
        add("SHA256SUMS", ("\n".join(checksums) + "\n").encode())
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix(package.suffix + ".sha256").write_text(digest + "  " + package.name + "\n")
    print(str(package))
    print("sha256=" + digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
