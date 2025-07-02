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

- Boom voila. Vous pouvez maintenant accéder à l'API à l'adresse http://localhost:8000/docs pour voir la documentation interactive de l'API.