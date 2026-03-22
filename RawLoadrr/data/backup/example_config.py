import pathlib

_example_path = pathlib.Path(__file__).parent.parent / "config.py.example"
_ns = {}
exec(compile(_example_path.read_text(), str(_example_path), "exec"), _ns)
config = _ns["config"]
