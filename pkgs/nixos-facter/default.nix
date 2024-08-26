{
  buildGoModule,
  hwinfo,
  libusb1,
  util-linux,
  pciutils,
  pkg-config,
  lib,
  fetchFromGitHub,
  stdenv,
}:
let
  hwinfo' = hwinfo.overrideAttrs {
    src = fetchFromGitHub {
      owner = "numtide";
      repo = "hwinfo";
      rev = "6944732764aecd701f807cd746ff605d2b749549";
      hash = "sha256-onJQPVp12hJig56KoXTvps7DzO/7/VBbD5auzxMLNTY=";
    };
  };
in
buildGoModule rec {
  pname = "nixos-facter";
  version = "0-unstable-2024-08-26";

  src = fetchFromGitHub {
    owner = "numtide";
    repo = "nixos-facter";
    rev = "30a01d3771d4d3d7f44e3f33d589f2c389ebcc63";
    hash = "sha256-mbfYJbrqCASsNW6mMtyf4aIpzME9jgaNToWyI0OlPt8=";
  };

  vendorHash = "sha256-8yQO7topYvXL6bP0oSVN1rApiPjse4Q2bjFNM5jVl8c=";

  buildInputs = [
    libusb1
    hwinfo'
  ];

  nativeBuildInputs = [ pkg-config ];

  runtimeInputs = [
    libusb1
    util-linux
    pciutils
  ];

  ldflags = [
    "-s"
    "-w"
    "-X github.com/numtide/nixos-facter/pkg/build.Name=nixos-facter"
    "-X github.com/numtide/nixos-facter/pkg/build.Version=v${version}"
    "-X github.com/numtide/nixos-facter/pkg/build.System=${stdenv.hostPlatform.system}"
  ];

  meta = with lib; {
    description = "nixos-facter: declarative nixos-generate-config";
    homepage = "https://github.com/numtide/nixos-facter";
    license = licenses.mit;
    platforms = platforms.linux;
    mainProgram = "nixos-facter";
  };
}
