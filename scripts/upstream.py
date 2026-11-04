"""Discover upstream ArtCraft releases and their GitHub-published checksums."""

import re

import common

ASSET = re.compile(r"^(?P<bin>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<version>\d+\.\d+\.\d+)-linux-x86_64\.AppImage$")


def discover(repo):
    """Map version -> manifest entry for every stable x86_64 AppImage in repo.

    None when the repo is gone. Releases without a sha256 digest are skipped:
    the digest is what lets mirrors be trusted without trusting the mirror.
    """
    releases = common.get_pages(f"https://api.github.com/repos/{repo}/releases", common.github_headers())
    if releases is None:
        return None
    found = {}
    for rel in releases:
        if rel["draft"] or rel["prerelease"]:
            continue
        for asset in rel["assets"]:
            m = ASSET.match(asset["name"])
            digest = asset.get("digest") or ""
            if m and digest.startswith("sha256:"):
                found[m["version"]] = {
                    "tag": rel["tag_name"],
                    "file": asset["name"],
                    "bin": m["bin"],
                    "hash": common.to_sri(digest.removeprefix("sha256:")),
                }
    return found


def title_from(repo_name):
    """`texturecraft` -> `TextureCraft`, `craft-anything` -> `Craft Anything`."""
    words = []
    for part in repo_name.split("-"):
        if part.lower().endswith("craft") and len(part) > len("craft"):
            words.append(part[: -len("craft")].capitalize() + "Craft")
        else:
            words.append(part.capitalize())
    return " ".join(words)


def summary_from(description):
    """The part of a repo description after `Name:`, up to the first period."""
    text = (description or "").split(":", 1)[-1].strip()
    return text.split(". ")[0].rstrip(".")


def new_apps(owner, tracked_repos):
    """Repos of owner, not yet tracked, that publish stable x86_64 AppImages.

    Yields (app, info) with the manifest entry for each; versions are left
    empty for update_versions to fill in.
    """
    repos = common.get_pages(f"https://api.github.com/users/{owner}/repos?type=owner", common.github_headers())
    for repo in repos or []:
        name = repo["full_name"]
        if repo["fork"] or repo["archived"] or name.lower() in tracked_repos:
            continue
        found = discover(name)
        if not found:
            continue
        newest = found[max(found, key=common.vkey)]
        yield newest["bin"], {
            "title": title_from(repo["name"]),
            "summary": summary_from(repo["description"]) or title_from(repo["name"]),
            "repo": name,
            "versions": {},
        }
