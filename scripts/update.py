"""Track upstream ArtCraft releases: verify, mirror and record them in versions.json.

Run daily by .github/workflows/update.yml. Needs GH_TOKEN (contents: write on
this repo). Exits non-zero
when something needs attention (see the report). Only a run that finished
writes `completed=true` to $GITHUB_OUTPUT; a crash restores versions.json and
flake.lock, so the workflow commits nothing half-done.
"""

import argparse
import os
import subprocess
import sys

import common
import mirrors
import upstream
import verify


def bump_nixpkgs(apps, report):
    """Update flake.lock; keep it only if the newest of every app still builds."""
    lock = common.ROOT / "flake.lock"
    old = lock.read_text()
    subprocess.run(["nix", "flake", "update", "--flake", str(common.ROOT)], check=True)
    if lock.read_text() == old:
        return
    broken = [p for app in apps for p in verify.check(verify.attr(app))]
    if broken:
        lock.write_text(old)
        report.info("nixpkgs bump kept back, it broke: " + "; ".join(broken))
    else:
        report.info("bumped nixpkgs")


def update_versions(data, apps, report):
    """Keep only the newest upstream version of each app, once it builds and checks out.

    If the newest release fails the checks, the version already in the
    manifest stays until a newer one passes.
    """
    for app in apps:
        info = data["apps"][app]
        found = upstream.discover(info["repo"])
        if found is None:
            report.fail(f"{app}: upstream {info['repo']} is gone; the mirror keeps serving the known version")
            continue
        if not found:
            continue
        newest = max(found, key=common.vkey)
        previous = info["versions"]
        current = max(previous, key=common.vkey) if previous else None
        if current is not None and common.vkey(current) >= common.vkey(newest):
            info["versions"] = {current: previous[current]}  # drop any older ones
            continue
        info["versions"] = {newest: found[newest]}
        common.save(data)  # nix builds from the file on disk
        problems = verify.check(verify.attr(app))
        if problems:
            info["versions"] = {current: previous[current]} if current else {}
            common.save(data)
            report.fail(f"{app} {newest} not published: " + "; ".join(problems))
        else:
            report.info(f"{app} {current} -> {newest}" if current else f"added {app} {newest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bump-nixpkgs", action="store_true", help="also update flake.lock (weekly)")
    parser.add_argument("--no-mirror", action="store_true", help="discover and verify only")
    parser.add_argument("--only", nargs="+", metavar="APP", help="limit to these apps")
    args = parser.parse_args()

    report, data = common.Report(), common.load()
    apps = args.only or list(data["apps"])
    lock = common.ROOT / "flake.lock"
    originals = {path: path.read_text() for path in (common.MANIFEST, lock)}
    try:
        if args.bump_nixpkgs:
            bump_nixpkgs(apps, report)
        update_versions(data, apps, report)
        if not args.no_mirror:
            mirrors.ensure(data, apps, report)
    except BaseException:
        for path, text in originals.items():
            path.write_text(text)
        raise
    report.write()
    if out := os.environ.get("GITHUB_OUTPUT"):
        changes = [line for line in report.lines if line.startswith(("added", "bumped"))]
        with open(out, "a") as f:
            f.write("completed=true\n")
            f.write(f"message={'; '.join(changes) or 'refresh mirrors'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
