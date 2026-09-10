from reviewdistill.cli.serve import build_uvicorn_args


def test_build_uvicorn_args_defaults():
    args = build_uvicorn_args(host="127.0.0.1", port=8765)
    assert args["app"] == "reviewdistill.web.app:app"
    assert args["host"] == "127.0.0.1"
    assert args["port"] == 8765
