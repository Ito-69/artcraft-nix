# artcraft-nix

Nix packages and a NixOS module for the [ArtCraft](https://github.com/storytold) apps,
open-source native alternatives to the Adobe suite, built from their official
release AppImages. Every release is verified and mirrored, so installs keep
working even if the upstream releases disappear.

| App | Category / Replaces | Package |
|---|---|---|
| PhotoCraft | Photoshop alternative | `photocraft` |
| VectorCraft | Illustrator alternative | `vectorcraft` |
| DesignCraft | InDesign alternative | `designcraft` |
| LightCraft | Lightroom alternative | `lightcraft` |
| FilmCraft | Premiere Pro alternative | `filmcraft` |
| EffectCraft | After Effects alternative | `effectcraft` |
| PdfCraft | Acrobat / PDF editor | `pdfcraft` |
| WordCraft | Documents & Word processing | `wordcraft` |
| DeckCraft | Presentations & Slides | `deckcraft` |
| GridCraft | Spreadsheets & Tables | `gridcraft` |
| CadCraft | 3D CAD & Modeling | `cadcraft` |
| SoundCraft | Digital Audio Workstation | `soundcraft` |
| FigCraft | Interface & UI Design | `figcraft` |
| TextureCraft | Substance Painter alternative | `texturecraft` |
| MaterialCraft | Substance Designer alternative | `materialcraft` |
| Craft Anything | Understand and craft software | `craft-anything` |
| SolidCraft | Parametric 3D CAD (by Tangency Labs) | `solidcraft` |

Unofficial: not affiliated with the ArtCraft authors. Fork of [ipeglin/artcraft-nix](https://github.com/ipeglin/artcraft-nix), extended with the full suite including office, CAD, audio, UI design and 3D texturing apps. x86_64-linux only for now.

## Try an app

```sh
nix run github:Ito-69/artcraft-nix#photocraft
```

Each package ships the GUI and its `<app>-cli` companion.

## Install on NixOS

```nix
# flake.nix
inputs.artcraft.url = "github:Ito-69/artcraft-nix";

# in your nixosSystem modules
modules = [
  inputs.artcraft.nixosModules.default
  { programs.artcraft.enable = true; }
];
```

The module installs every app, enables `fonts.fontDir` and links
`/usr/share/fonts` to the system fonts. The apps' text tools only look there,
not through fontconfig. Options:

```nix
programs.artcraft = {
  enable = true;
  apps = [ "photocraft" "vectorcraft" ];  # default: every app
  linkFonts = false;                     # if you manage /usr/share/fonts yourself
};
```

Alternatives: `inputs.artcraft.packages.x86_64-linux.<app>`, or
`overlays.default`, which adds `pkgs.artcraft.<app>` built against your
nixpkgs. `nix profile install github:Ito-69/artcraft-nix` installs all of them.

## Versions

- Only the newest stable release of each app is packaged, as `<app>`.
- `nix flake update artcraft` picks up new releases; until then your
  `flake.lock` keeps you where you are. To go back to an older version, pin
  the flake input to an older commit of this repo.

## Where the files come from

Each app lists two download sources, tried in order:

1. the upstream GitHub release
2. this repo's release `mirror-<app>`

Both serve byte-identical files, pinned by the sha256 that upstream
published, so the mirror cannot substitute anything.

Completely offline, from any copy of an AppImage with its original filename:

```sh
nix-store --add-fixed sha256 photocraft-0.3.0-linux-x86_64.AppImage
```

Nix then finds it in the store and never downloads it.

## How it stays current

[`.github/workflows/update.yml`](.github/workflows/update.yml) runs daily
([`scripts/update.py`](scripts/update.py)):

1. adds any new app from the owners under `discover`, then finds the newest
   stable release of each app and its published sha256
2. builds it, runs `<app>-cli --version`, and checks that the binary
   loads no library outside the set in [`package.nix`](package.nix)
3. replaces the previous version in [`versions.json`](versions.json) if it
   passes (if not, the previous version stays and it is retried the next day)
4. mirrors the AppImage to GitHub releases and deletes older ones there
5. on Mondays, bumps nixpkgs, and keeps it only if every app still builds

### Maintainer notes

- **"references unknown libraries":** upstream started loading something new.
  Add the nixpkgs package to `runtimeDependencies` in `package.nix` and the
  library name to `KNOWN_LIBS` in `scripts/verify.py`.
- **New app:** apps from the GitHub owners listed under `discover` in
  `versions.json` (now `storytold`) are added automatically once they publish
  a stable `<app>-<version>-linux-x86_64.AppImage`; the run summary says so,
  and the README table above is updated by hand. Apps from anyone else, such
  as SolidCraft, are added by hand: an entry under `apps` with an empty
  `versions` object; the next run fills it in.
- **Local run:** `python3 scripts/update.py --no-mirror` discovers and
  verifies without uploading.

## License

The packaging in this repo is MIT ([LICENSE](LICENSE)). The ArtCraft apps are
licensed MIT OR Apache-2.0 by their authors. Their license files are attached
to every mirror release.
