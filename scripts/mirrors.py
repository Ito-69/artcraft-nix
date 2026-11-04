"""Keep each app's manifest version mirrored on GitHub releases.

One release per app, tag `mirror-<app>`, holding the AppImage of the version
in versions.json plus upstream's license files (MIT, Apache-2.0, NOTICE).
AppImages of older versions are deleted once the manifest no longer lists them.
"""

import subprocess
import tempfile
import urllib.error
from pathlib import Path

import common

LICENSE_FILES = ["LICENSE-MIT", "LICENSE-APACHE", "NOTICE"]


def urls(data, app, version):
    """Download URLs for one version: upstream, then the GitHub mirror."""
    info, entry, mirrors = data["apps"][app], data["apps"][app]["versions"][version], data["mirrors"]
    return [
        f"https://github.com/{info['repo']}/releases/download/{entry['tag']}/{entry['file']}",
        f"https://github.com/{mirrors['github']}/releases/download/mirror-{app}/{entry['file']}",
    ]


def fetch_verified(candidates, sri, dest):
    """Download from the first candidate URL whose file matches sri."""
    for url in candidates:
        try:
            common.download(url, dest)
        except (urllib.error.URLError, OSError):
            continue
        if common.sha256_file(dest) == common.from_sri(sri):
            return dest
    raise RuntimeError(f"no source has a copy matching {sri}")


def license_files(data, app, workdir):
    """Fetch upstream license files."""
    repo = data["apps"][app]["repo"]
    # The authenticated API, not raw.githubusercontent.com, which rate-limits
    # the shared Actions runner IPs.
    api = {**common.github_headers(), "Accept": "application/vnd.github.raw"}
    found = []
    for name in LICENSE_FILES:
        dest = Path(workdir) / name
        try:
            common.download(f"https://api.github.com/repos/{repo}/contents/{name}", dest, api)
            found.append(dest)
        except urllib.error.URLError:
            continue
    return found


def github_assets(repo, app):
    """Asset names on the app's mirror release; None if the release is missing."""
    rel = common.get_json(f"https://api.github.com/repos/{repo}/releases/tags/mirror-{app}", common.github_headers())
    if rel is None:
        return None
    assets = common.get_pages(f"https://api.github.com/repos/{repo}/releases/{rel['id']}/assets", common.github_headers())
    return {a["name"] for a in assets}


def github_create(data, app, licenses):
    info, repo = data["apps"][app], data["mirrors"]["github"]
    notes = (f"Mirror of the latest {info['title']} release from https://github.com/{info['repo']}, "
             "byte-identical (checked against upstream's published sha256).\n\n"
             f"{info['title']} is licensed MIT OR Apache-2.0 by its authors; the license files are attached. "
             "Not affiliated with the upstream project.")
    subprocess.run(["gh", "release", "create", f"mirror-{app}", "-R", repo, "--title", f"{info['title']} mirror",
                    "--notes", notes, "--latest=false", *map(str, licenses)], check=True)


def ensure(data, apps, report):
    """Upload the manifest version of every app and delete older AppImages."""
    gh_repo = data["mirrors"]["github"]
    for app in apps:
        with tempfile.TemporaryDirectory() as tmp:
            licenses = license_files(data, app, tmp)
            if not licenses:
                report.fail(f"{app}: no license files found upstream or on the source mirror")
            on_github = github_assets(gh_repo, app)
            if on_github is None:
                github_create(data, app, licenses)
                on_github = {p.name for p in licenses}
            missing = [str(p) for p in licenses if p.name not in on_github]
            if missing:
                subprocess.run(["gh", "release", "upload", f"mirror-{app}", *missing, "-R", gh_repo, "--clobber"],
                               check=True)
                report.info(f"attached license files to mirror-{app}")
            for version, entry in data["apps"][app]["versions"].items():
                if entry["file"] in on_github:
                    continue
                try:
                    path = fetch_verified(urls(data, app, version), entry["hash"], Path(tmp) / entry["file"])
                    subprocess.run(["gh", "release", "upload", f"mirror-{app}", str(path), "-R", gh_repo,
                                    "--clobber"], check=True)
                    report.info(f"mirrored {entry['file']} to GitHub")
                    path.unlink()
                except Exception as err:  # one bad file must not stop the rest
                    report.fail(f"mirroring {app} {version}: {err}")
            wanted = {entry["file"] for entry in data["apps"][app]["versions"].values()}
            for name in sorted(on_github):
                if name.endswith(".AppImage") and name not in wanted:
                    subprocess.run(["gh", "release", "delete-asset", f"mirror-{app}", name, "-R", gh_repo, "--yes"],
                                   check=True)
                    report.info(f"removed {name} from mirror-{app}")
