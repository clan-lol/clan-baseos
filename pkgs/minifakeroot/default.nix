{ stdenv }:
let
  varName = if stdenv.isDarwin then "DYLD_INSERT_LIBRARIES" else "LD_PRELOAD";
  linkerFlags = if stdenv.isDarwin then "-dynamiclib" else "-shared";
  sharedLibrary = stdenv.hostPlatform.extensions.sharedLibrary;
in
stdenv.mkDerivation {
  name = "minifakeroot";
  dontUnpack = true;
  installPhase = ''
    mkdir -p $out/lib
    $CC ${linkerFlags} -o $out/lib/libfakeroot${sharedLibrary} ${./main.c}
    mkdir -p $out/share/minifakeroot
    cat > $out/share/minifakeroot/rc <<EOF
    export ${varName}=$out/lib/libfakeroot${sharedLibrary}
    EOF
  '';
}
