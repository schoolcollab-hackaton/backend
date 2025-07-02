### installation

- Installe poetry si ce n'est pas déjà fait: https://python-poetry.org/docs/

```bash
poetry env use python3.12
```

```bash
poetry install --no-root
```

### Run the app

```bash
poetry run uvicorn app.main:app --reload
```


### Si vous voulez utiliser docker

- Build the Docker image:

```bash
  docker build -t backend-schoolcollab .
```

- Run the container:

```bash
  docker run -d -p 8000:8000 --name schoolcollab-api backend-schoolcollab
```

- Boom voila. Vous pouvez maintenant accéder à l'API à l'adresse http://localhost:8000/docs pour voir la documentation interactive de l'API.