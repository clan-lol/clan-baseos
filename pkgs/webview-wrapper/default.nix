{ pkgs }:

pkgs.stdenv.mkDerivation rec {
  pname = "webui";
  version = "nigthly";

  src = pkgs.fetchFromGitHub {
    owner = "webui-dev";
    repo = "python-webui";
    rev = "0ff3b1351b9e24be4463b1baf2c26966caeae74a"; # Use a specific commit sha or tag for reproducibility
    sha256 = "sha256-xSOnCkW4iZkSSLKzk6r3hewC3bPJlV7L6aoGEchyEys="; # Replace with actual sha256
  };

  outputs = [ "out" "dev" ];

  # Dependencies used during the build process, if any
  buildInputs = [
    pkgs.gnumake
  ];

  # Commands to build and install the project
  buildPhase = ''
    make
  '';

  installPhase = ''
    mkdir -p $out/lib
    mkdir -p $out/include
    cp -r dist/* $out/lib
    cp -r include/* $out/include
  '';

  meta = with pkgs.lib; {
    description = "Webui is a UI library for C/C++/Go/Rust to build portable desktop/web apps using WebView";
    homepage = "https://github.com/webui-dev/webui";
    license = licenses.mit;
    platforms = platforms.linux ++ platforms.darwin; # Adjust if needed
  };
}