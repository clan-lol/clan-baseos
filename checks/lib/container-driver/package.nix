{
  extraPythonPackages,
  python3Packages,
  buildPythonApplication,
  setuptools,
  util-linux,
  systemd,
  colorama,
  junit-xml,
}:
buildPythonApplication {
  pname = "test-driver";
  version = "0.0.1";
  propagatedBuildInputs = [
    util-linux
    systemd
    colorama
    junit-xml
  ] ++ extraPythonPackages python3Packages;
  nativeBuildInputs = [ setuptools ];
  format = "pyproject";
  src = ./.;
}
