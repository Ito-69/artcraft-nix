# Every ArtCraft app at its newest release: `<app>`, and `default` bundles all.
# Versions and hashes live in versions.json, maintained by scripts/update.py.
{ pkgs }:

let
  inherit (pkgs) lib;
  data = lib.importJSON ./versions.json;

  # Newer nixpkgs renamed the xorg libraries to top-level attributes.
  xlibs = {
    libx11 = pkgs.libx11 or pkgs.xorg.libX11;
    libxcb = pkgs.libxcb or pkgs.xorg.libxcb;
    libxcursor = pkgs.libxcursor or pkgs.xorg.libXcursor;
    libxi = pkgs.libxi or pkgs.xorg.libXi;
  };

  build = app: version:
    pkgs.callPackage ./package.nix (xlibs // {
      inherit app version;
      info = data.apps.${app};
      release = data.apps.${app}.versions.${version};
      inherit (data) mirrors;
    });

  newest = versions: lib.last (lib.sort lib.versionOlder versions);

  perApp = app: info:
    let versions = lib.attrNames info.versions;
    in
    lib.optionalAttrs (versions != [ ]) { ${app} = build app (newest versions); };

  packages = lib.concatMapAttrs perApp data.apps;
in
packages // {
  default = pkgs.symlinkJoin {
    name = "artcraft";
    paths = map (app: packages.${app}) (lib.filter (app: packages ? ${app}) (lib.attrNames data.apps));
  };
}
