{
  fetchFromGitHub,
  buildPythonPackage,
  lib,
  poetry-core,
  pillow,
  beautifulsoup4,
  clipman,
  html2text,
  httpx,
  mastodon-py,
  python-dateutil,
  python-dotenv,
  requests,
  textual,
  textual-image,
  toml,
}:
buildPythonPackage (finalAttrs: {
  pname = "mastui";
  # this will need to be updated when the version changes via CI
  version = "1.14.2";
  pyproject = true;
  build-system = [ poetry-core ];

  src = ./.;

  pythonRelaxDeps = [
    "pillow"
    "html2text"
    "httpx"
    "textual-image"
  ];

  propagatedBuildInputs = [
    pillow
    html2text
    httpx
    textual-image
    poetry-core
    beautifulsoup4
    clipman
    mastodon-py
    python-dateutil
    python-dotenv
    requests
    textual
    toml
  ];

  meta = {
    description = "A TUI client for mastodon written in python";
    longDescription = "A powerful, feature-rich, and beautiful Mastodon TUI client.";
    homepage = "https://mastui.app/";
    mainProgram = "mastui";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ kimusan ];
  };
})
