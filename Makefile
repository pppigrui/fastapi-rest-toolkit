run-demo:
	uv run demo/main.py

format:
	uvx ruff format . && uvx ruff check --fix .


build-pypi:
	uv build --no-sources

publish-pypi:
	uv publish