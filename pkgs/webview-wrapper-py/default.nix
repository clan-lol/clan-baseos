{ lib
, buildPythonPackage
, fetchFromGitHub

# build-system dependencies
, setuptools
, wheel
, webview-wrapper

}:

buildPythonPackage rec {
  pname = "python-webui";
  version = "main"; 

  src = fetchFromGitHub {
    owner = "webui-dev";
    repo = "python-webui";
    rev = "fa961b5ee0752c9408ac01519097f5481a0fcecf"; # Replace with specific commit hash for reproducibility
  #  sha256 = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="; # Replace with actual hash via nix-prefetch-git
  };

  sourceRoot = "PyPI/Package";

  # Indicate this is a recent Python project with PEP 517 support (pyproject.toml)
  pyproject = true;

  # Declare the build system (setuptools and wheel are common)
  buildInputs = [
    setuptools
    wheel
  ];

  # Declare required Python package dependencies
  propagatedBuildInputs = [

  ];

  # Native inputs for testing, if tests are included
  nativeCheckInputs = [

  ];

  # If tests don't work out of the box or need adjustments, patches can be applied here
  postPatch = ''
    # Example: Modify or patch some test files
    echo "No postPatch modifications applied yet."
  '';

  meta = with lib; {
    description = "A Python library for webui-dev";
    homepage = "https://github.com/webui-dev/python-webui";
    license = licenses.mit;
    maintainers = [ maintainers.yourname ];
  };
}