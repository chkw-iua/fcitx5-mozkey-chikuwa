#!/usr/bin/env python3
"""Linux equivalent of upstream/tools/dictionary/prepare_daily_dictionary.ps1.

Prepares SHA256-pinned external dictionaries locally for Mozkey, builds the
daily profile, and optionally toggles upstream/src/data/dictionary_oss/BUILD.bazel
between mozcdic_ut_sample (default) and mozcdic_ut_daily_local.
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request

OSS_BUILD_SAMPLE = '"//data/dictionary_koyasi:mozcdic_ut_sample"'
OSS_BUILD_DAILY = '"//data/dictionary_koyasi:mozcdic_ut_daily_local"'


def run(cmd: list[str], cwd: pathlib.Path | None = None, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, check=True)
    return proc.stdout or ""


def capture(cmd: list[str], cwd: pathlib.Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def download_verified(url: str, dest: pathlib.Path, expected_bytes: int, expected_sha256: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp", dir=dest.parent)
    os.close(fd)
    tmp_path = pathlib.Path(tmp_name)
    try:
        print(f"Downloading: {url}")
        urllib.request.urlretrieve(url, tmp_path)
        actual_bytes = tmp_path.stat().st_size
        if actual_bytes != expected_bytes:
            raise RuntimeError(f"Byte count mismatch for {dest.name}: expected {expected_bytes}, got {actual_bytes}")
        actual_hash = sha256_file(tmp_path)
        if actual_hash != expected_sha256.upper():
            raise RuntimeError(f"SHA256 mismatch for {dest.name}: expected {expected_sha256}, got {actual_hash}")
        tmp_path.replace(dest)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def import_nico_pixiv(repo_root: pathlib.Path, lock: dict) -> None:
    np_lock = lock["nico_pixiv"]
    repository = np_lock["repository"]
    revision = np_lock["revision"]
    url = f"https://raw.githubusercontent.com/{repository}/{revision}/{np_lock['path']}"
    out_file = repo_root / "src/data/dictionary_koyasi/generated/nico_pixiv/dic-nico-intersection-pixiv-google.txt"
    download_verified(url, out_file, int(np_lock["bytes"]), str(np_lock["sha256"]))
    print(f"Verified nico/pixiv dictionary: {out_file}")


def import_personal_names(repo_root: pathlib.Path, lock: dict, skip_download: bool) -> None:
    pn_lock = lock["personal_names"]
    out_dir = repo_root / "src/data/dictionary_koyasi/generated/personal_names"
    bz2_path = out_dir / "mozcdic-ut-personal-names.txt.bz2"
    txt_path = out_dir / "mozcdic-ut-personal-names.txt"
    if not skip_download:
        url = f"https://raw.githubusercontent.com/{pn_lock['repository']}/{pn_lock['revision']}/{pn_lock['path']}"
        download_verified(url, bz2_path, int(pn_lock["bytes"]), str(pn_lock["sha256"]))
    else:
        if not bz2_path.is_file():
            raise RuntimeError(f"Missing {bz2_path} with --skip-download")
        if bz2_path.stat().st_size != int(pn_lock["bytes"]) or sha256_file(bz2_path) != str(pn_lock["sha256"]).upper():
            raise RuntimeError(f"Pinned personal names archive differs from lock: {bz2_path}")
    txt_path.write_bytes(bz2.decompress(bz2_path.read_bytes()))
    print(f"Unpacked personal names dictionary: {txt_path}")


def import_merge_ut(repo_root: pathlib.Path, lock: dict, lock_file: pathlib.Path, sample_lines: int) -> None:
    pin_tool = repo_root / "tools/dictionary/pin_dictionary_inputs.py"
    patch_path = repo_root / "tools/dictionary/patches/merge_ut_mozkey_local.patch"
    out_dir = repo_root / "src/data/dictionary_koyasi/generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    wiki_index_path = capture(["python3", str(pin_tool), "--lock", str(lock_file), "stage-wiki", "--repo-root", str(repo_root)])
    mu_lock = lock["merge_ut"]
    upstream_rev = mu_lock["revision"]
    upstream_url = "https://github.com/utuhiro78/merge-ut-dictionaries.git"

    with tempfile.TemporaryDirectory(prefix="mozkey-merge-ut-") as tmp_dir:
        merge_repo = pathlib.Path(tmp_dir) / "merge-ut-dictionaries"
        run(["git", "-c", "core.autocrlf=false", "init", "-q", str(merge_repo)])
        run(["git", "-C", str(merge_repo), "remote", "add", "origin", upstream_url])
        run(["git", "-C", str(merge_repo), "-c", "core.autocrlf=false", "fetch", "--depth", "1", "origin", upstream_rev])
        run(["git", "-C", str(merge_repo), "-c", "core.autocrlf=false", "checkout", "-q", "--detach", "FETCH_HEAD"])

        actual_rev = capture(["git", "-C", str(merge_repo), "rev-parse", "HEAD"])
        if actual_rev != upstream_rev:
            raise RuntimeError(f"merge-ut revision mismatch: expected {upstream_rev}, got {actual_rev}")

        run(["git", "-C", str(merge_repo), "apply", "--unidiff-zero", "--check", str(patch_path)])
        run(["git", "-C", str(merge_repo), "apply", "--unidiff-zero", str(patch_path)])

        make_path = merge_repo / "src/merge/make.sh"
        merge_script = merge_repo / "src/merge/merge_dictionaries.py"
        make_text = make_path.read_text(encoding="utf-8")
        first_nl = make_text.find("\n")
        if first_nl >= 0:
            make_text = make_text[: first_nl + 1] + "set -eo pipefail\n" + make_text[first_nl + 1 :]
        make_path.write_text(make_text, encoding="utf-8", newline="\n")

        run([
            "python3",
            str(pin_tool),
            "--lock",
            str(lock_file),
            "patch-staged-merge",
            "--make",
            str(make_path),
            "--merge-script",
            str(merge_script),
        ])

        shim_bin = pathlib.Path(tmp_dir) / "shim_bin"
        shim_bin.mkdir(exist_ok=True)
        python_shim = shim_bin / "python"
        if not python_shim.exists():
            python_shim.symlink_to(sys.executable)

        env = os.environ.copy()
        env["PATH"] = f"{shim_bin}:{env.get('PATH', '')}"
        env["MOZKEY_JAWIKI_INDEX_BZ2"] = wiki_index_path
        env["MOZKEY_DICTIONARY_OSS_DIR"] = str((repo_root / "src/data/dictionary_oss").resolve())
        run(["bash", "--noprofile", "--norc", "./make.sh"], cwd=merge_repo / "src/merge", env=env)

        for child in mu_lock["children"]:
            child_rev = capture(["git", "-C", str(merge_repo / "src/merge" / child["name"]), "rev-parse", "HEAD"])
            if child_rev != child["revision"]:
                raise RuntimeError(f"Child revision mismatch for {child['name']}: {child_rev}")

        generated = merge_repo / "src/merge/mozcdic-ut.txt"
        if not generated.is_file() or generated.stat().st_size == 0:
            raise RuntimeError(f"Generated dictionary is missing or empty: {generated}")

        out_full = out_dir / "mozcdic-ut-safe.txt"
        out_sample = out_dir / "mozcdic-ut-sample.txt"
        shutil.copy2(generated, out_full)
        if sample_lines > 0:
            with out_full.open("r", encoding="utf-8") as src, out_sample.open("w", encoding="utf-8", newline="\n") as dst:
                for i, line in enumerate(src):
                    if i >= sample_lines:
                        break
                    dst.write(line)
        print(f"Generated merge-ut base dictionary: {out_full}")


def switch_profile(repo_root: pathlib.Path, profile: str) -> None:
    build_file = repo_root / "src/data/dictionary_oss/BUILD.bazel"
    text = build_file.read_text(encoding="utf-8")
    target = OSS_BUILD_DAILY if profile == "daily" else OSS_BUILD_SAMPLE
    other = OSS_BUILD_SAMPLE if profile == "daily" else OSS_BUILD_DAILY
    if target in text:
        print(f"Profile already set to {profile}: {build_file}")
        return
    if other not in text:
        raise RuntimeError(f"Could not locate dictionary target in {build_file}")
    build_file.write_text(text.replace(other, target, 1), encoding="utf-8")
    print(f"Switched active dictionary profile to {profile} in {build_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Mozkey daily dictionary on Linux")
    parser.add_argument("--profile", choices=["daily", "sample"], default="daily", help="Target profile to activate (default: daily)")
    parser.add_argument("--sample-lines", type=int, default=5000)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--switch-only", action="store_true", help="Only switch BUILD.bazel between daily and sample")
    args = parser.parse_args()

    workspace_root = pathlib.Path(__file__).resolve().parent.parent
    repo_root = workspace_root / "upstream"
    lock_file = repo_root / "tools/dictionary/locks/daily_sources.json"
    pin_tool = repo_root / "tools/dictionary/pin_dictionary_inputs.py"

    if args.switch_only:
        switch_profile(repo_root, args.profile)
        return

    run(["python3", str(pin_tool), "--lock", str(lock_file), "validate"])
    lock = json.loads(lock_file.read_text(encoding="utf-8"))

    if not args.skip_download:
        import_merge_ut(repo_root, lock, lock_file, args.sample_lines)
        import_nico_pixiv(repo_root, lock)
    import_personal_names(repo_root, lock, args.skip_download)

    for script, extra in [
        ("profile_merge_ut.py", ["--profile", "daily"]),
        ("convert_nico_pixiv.py", []),
        ("profile_personal_names.py", []),
        ("check_merge_ut_profile.py", ["--profile", "daily"]),
        ("generate_syntax_guard_dictionary.py", []),
    ]:
        run(["python3", str(repo_root / "tools/dictionary" / script), *extra], cwd=repo_root)

    switch_profile(repo_root, args.profile)
    print("\nDaily dictionary is ready. Rebuild with bazelisk and packaging/build_deb.sh.")
    print("To switch back to the tracked sample profile before committing:")
    print("  python3 packaging/prepare_daily_dictionary_linux.py --switch-only --profile sample")


if __name__ == "__main__":
    main()
