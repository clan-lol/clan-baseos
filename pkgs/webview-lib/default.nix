{ pkgs, ... }:

pkgs.stdenv.mkDerivation {
  pname = "webview";
  version = "nigthly";

  src = pkgs.fetchFromGitHub {
    owner = "webview";
    repo = "webview";
    rev = "83a4b4a5bbcb4b0ba2ca3ee226c2da1414719106";
    sha256 = "sha256-5R8kllvP2EBuDANIl07fxv/EcbPpYgeav8Wfz7Kt13c=";
  };

  outputs = [
    "out"
    "dev"
  ];

  # Dependencies used during the build process, if any
  buildInputs =
    with pkgs;
    [
      gnumake
      cmake
      pkg-config
    ]
    ++ pkgs.lib.optionals stdenv.isLinux [
      webkitgtk_6_0
      gtk4
    ];

  meta = with pkgs.lib; {
    description = "Tiny cross-platform webview library for C/C++. Uses WebKit (GTK/Cocoa) and Edge WebView2 (Windows)";
    homepage = "https://github.com/webview/webview";
    license = licenses.mit;
    platforms = platforms.linux ++ platforms.darwin;
  };
}
