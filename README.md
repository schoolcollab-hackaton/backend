### installation

- Installe poetry si ce n'est pas déjà fait: https://python-poetry.org/docs/

```bash
poetry env use python3.10
```

```bash
poetry install --no-root
```

### Run the app

```bash
poetry run uvicorn app.main:app 
```