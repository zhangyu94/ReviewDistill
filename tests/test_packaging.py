from pathlib import Path
import tomllib


def _pyproject() -> dict:
    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    return tomllib.loads(path.read_text())


def test_pyproject_builds_client_into_package_data():
    pyproject = _pyproject()
    data = pyproject["tool"]["setuptools"]["package-data"]["reviewdistill"]
    assert any("web/static" in item for item in data)
    cmdclass = pyproject["tool"]["setuptools"]["cmdclass"]
    assert cmdclass["build_py"] == "client_build.build_py"
    assert cmdclass["sdist"] == "client_build.sdist"
    assert cmdclass["editable_wheel"] == "client_build.editable_wheel"
