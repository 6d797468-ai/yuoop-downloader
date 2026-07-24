import tomllib


def test_version_file_matches_project_metadata():
    version = open("VERSION", encoding="utf-8").read().strip()
    with open("pyproject.toml", "rb") as f:
        metadata = tomllib.load(f)

    assert metadata["project"]["version"] == version
