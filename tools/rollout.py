#!/usr/bin/env python3
"""Edit the staged-rollout manifests in manifests/v2/ (see docs/ota-staged-rollout.md
in the firmware repo).

  tools/rollout.py --hw2 show
  tools/rollout.py --hw2 release 1.2.0 firmware-v1.2.0-v2.bin.enc <asset-url>   # canaries only
  tools/rollout.py --hw2 percent 5
  tools/rollout.py --hw2 canary add A1B2C3D4E5F6
  tools/rollout.py --hw2 canary remove A1B2C3D4E5F6
  tools/rollout.py --hw2 block 1.2.0      # devices on 1.2.0 install the manifest version
  tools/rollout.py --hw2 unblock 1.2.0

Add --push to commit and push the change. Raw GitHub caches for ~5 minutes.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFESTS = {"hw1": REPO / "manifests/v2/stable.json", "hw2": REPO / "manifests/v2/stable-hw2.json"}
KEY_ORDER = ["version", "url", "size", "sha256", "rollout_percent", "canary_devices", "blocked_versions"]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
MAC_RE = re.compile(r"^[0-9A-F]{12}$")


def fail(msg):
    sys.exit(f"error: {msg}")


def load(path):
    m = json.loads(path.read_text())
    m.setdefault("rollout_percent", 100)
    m.setdefault("canary_devices", [])
    m.setdefault("blocked_versions", [])
    return m


def save(path, m):
    ordered = {k: m[k] for k in KEY_ORDER if k in m}
    ordered.update({k: v for k, v in m.items() if k not in ordered})
    path.write_text(json.dumps(ordered, indent=2) + "\n")


def version(s):
    if not VERSION_RE.match(s):
        fail(f"version must look like 1.2.3, got {s!r}")
    return s


def mac(s):
    s = s.replace(":", "").upper()
    if not MAC_RE.match(s):
        fail(f"device ID must be 12 hex characters, got {s!r}")
    return s


def show(m):
    print(json.dumps(m, indent=2))
    who = f"{m['rollout_percent']}% of devices"
    if m["canary_devices"]:
        who += f" + {len(m['canary_devices'])} canaries"
    print(f"\n{m['version']} goes to {who}.")
    if m["blocked_versions"]:
        print(f"Devices on {', '.join(m['blocked_versions'])} install {m['version']} regardless.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    hw = ap.add_mutually_exclusive_group(required=True)
    hw.add_argument("--hw1", action="store_const", dest="hw", const="hw1")
    hw.add_argument("--hw2", action="store_const", dest="hw", const="hw2")
    ap.add_argument("--push", action="store_true", help="commit and push the manifest")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("show")
    rel = sub.add_parser("release", help="point at a new build and restart at 0%% (canaries only)")
    rel.add_argument("version", type=version)
    rel.add_argument("bin", type=Path, help="the .bin.enc uploaded to the release")
    rel.add_argument("url", help="release asset URL")
    pct = sub.add_parser("percent")
    pct.add_argument("value", type=int)
    can = sub.add_parser("canary")
    can.add_argument("action", choices=["add", "remove"])
    can.add_argument("device", type=mac)
    blk = sub.add_parser("block")
    blk.add_argument("version", type=version)
    unb = sub.add_parser("unblock")
    unb.add_argument("version", type=version)
    args = ap.parse_args()

    path = MANIFESTS[args.hw]
    m = load(path)

    if args.cmd == "show":
        show(m)
        return
    if args.cmd == "release":
        if not args.bin.is_file():
            fail(f"{args.bin} not found")
        data = args.bin.read_bytes()
        m.update(version=args.version, url=args.url, size=len(data),
                 sha256=hashlib.sha256(data).hexdigest(), rollout_percent=0)
        if args.version in m["blocked_versions"]:
            fail(f"{args.version} is in blocked_versions; unblock it first")
        message = f"{args.hw}: release {args.version} to canaries"
    elif args.cmd == "percent":
        if not 0 <= args.value <= 100:
            fail("percent must be 0-100")
        m["rollout_percent"] = args.value
        message = f"{args.hw}: roll out {m['version']} to {args.value}%"
    elif args.cmd == "canary":
        devices = set(m["canary_devices"])
        (devices.add if args.action == "add" else devices.discard)(args.device)
        m["canary_devices"] = sorted(devices)
        message = f"{args.hw}: canary {args.action} {args.device}"
    elif args.cmd == "block":
        if args.version == m["version"]:
            fail("can't block the version the manifest points at; release a good build first")
        m["blocked_versions"] = sorted(set(m["blocked_versions"]) | {args.version})
        message = f"{args.hw}: block {args.version}"
    else:
        m["blocked_versions"] = [v for v in m["blocked_versions"] if v != args.version]
        message = f"{args.hw}: unblock {args.version}"

    save(path, m)
    show(m)

    if args.push:
        rel_path = str(path.relative_to(REPO))
        subprocess.run(["git", "-C", str(REPO), "add", rel_path], check=True)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", str(REPO), "push"], check=True)


if __name__ == "__main__":
    main()
