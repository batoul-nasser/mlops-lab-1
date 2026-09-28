Here are the Lab 4 answers Q1–Q11, based directly on your lab file and on what you actually observed while running it.
Q1. What happens to everything written to /mlflow-data if no volume is mounted?
If no volume is mounted, everything written to /mlflow-data stays inside that specific container’s writable filesystem.
If I stop and remove that container, then create a new container from the same image, the MLflow database and artifacts are gone. The new container starts with an empty MLflow UI.
So without a volume:
container removed
→ MLflow data removed

The lab uses /mlflow-data specifically so that the database and artifacts can be placed on persistent storage instead of the container layer.    lab4-compose
Q2. Why use a named volume instead of a bind mount? Would a bind mount also work?
A named volume is managed directly by Docker and is independent of a folder inside the repository.
It is convenient because Docker handles where the data is stored and preserves it across:
docker compose down
docker compose up

A bind mount would also work, but it would map MLflow storage to a specific folder on the host machine. That is often useful during local development, but it makes the setup more dependent on the host filesystem and paths.
The lab prefers a named volume because it provides persistent Docker-managed storage.    lab4-compose
Q3. Why does http://mlflow:5000 work in Compose when it did not work in Lab 3?
Docker Compose creates a private network for the services.
Inside that network, each service can be reached by its service name.
Because the service is called:
mlflow:

the inference container can use:
http://mlflow:5000

Docker Compose's internal DNS resolves mlflow to the MLflow container.
In Lab 3, the MLflow server was running on the Mac itself, not inside the same Docker network, so we had to use:
host.docker.internal

instead.    lab4-compose
Q4. Why does the frontend read INFERENCE_URL from an environment variable instead of hardcoding http://inference:8000?
Using an environment variable makes the frontend image reusable in different environments.
Inside Docker Compose, we set:
INFERENCE_URL=http://inference:8000

But if I run the frontend directly outside Compose, the default can be:
http://127.0.0.1:8000

If the Compose hostname were hardcoded in the code, the frontend would only work inside that Compose network.
So the environment variable makes the same image configurable without modifying the application code.    lab4-compose
Q5. Why doesn't the inference service publish a port? How does the frontend still reach it?
The inference service does not need to be accessed directly by the user.
The frontend communicates with it inside the private Docker Compose network using:
http://inference:8000

Therefore, the inference service only needs its internal container port.
In our docker compose ps, we saw:
frontend    0.0.0.0:8501->8501
mlflow      0.0.0.0:5001->5000
inference   8000/tcp

This is expected.
Only services that humans need to reach from the host should publish ports.    lab4-compose
Q6. What happens if MLflow is not ready when inference starts?
depends_on only guarantees that the MLflow container process is started before inference.
It does not guarantee that the MLflow server is already ready to accept requests.
If serve.py tries to load the model immediately and MLflow is unavailable or not ready, the model-loading step fails and the inference process exits.
We actually observed this behavior: the inference container started and then disappeared from:
docker compose ps

and we used:
docker compose logs inference

to inspect the failure.
So:
depends_on = startup order
not readiness

   lab4-compose    lab4-compose
Q7. Which services have published ports in docker compose ps?
In our final running stack:
frontend  → 8501 published
mlflow    → 5001 on host mapped to 5000 in container
inference → no published host port

This matches the Compose configuration.
The frontend needs a host port so the user can open the Streamlit page.
MLflow needs a host port so we can open its UI.
Inference does not need a host port because the frontend reaches it internally through the Compose network.    lab4-compose
Q8. After assigning the newer model version, does the running inference service immediately use it?
No.
The inference application loads the model once when the service starts.
So even if the registry alias is changed from:
champion → Version 1

to:
champion → Version 2

the already-running inference container keeps the model that was loaded at startup.
To make it load the new version, we run:
docker compose restart inference

That restarts only the inference service, causing it to resolve the alias again and load the current model version.    lab4-compose
Q9. Why does docker compose restart inference work without rebuilding?
Because the model itself is not baked into the Docker image.
The image contains:
Python
FastAPI
PyTorch
MLflow client
serve.py
dependencies

At startup, serve.py asks MLflow for:
models:/food11@champion

Therefore, when the alias changes, no Docker image needs to be rebuilt.
Restarting the service is enough because the application fetches the current registered model again during startup.
This shows the separation between:
image → application + dependencies
runtime → model loaded from MLflow

   lab4-compose
Q10. What happens after docker compose down compared with docker compose down -v?
With:
docker compose down
docker compose up

the containers are removed and recreated, but the named volume remains.
Therefore, the MLflow database, registered model versions, aliases, and artifacts remain available.
So we still expect to see things like:
food11
Version 1
Version 2
champion → Version 2

But with:
docker compose down -v

the -v also deletes the named volume.
That removes the MLflow database and artifacts.
When the stack starts again, MLflow is empty because the persistent storage was deleted.    lab4-compose
Q11. What would be needed to run three inference replicas or survive a machine failure?
Docker Compose is designed mainly for running services on a single machine.
If I want:
3 inference replicas
+ load balancing
+ failover
+ multi-machine deployment

I need an orchestration platform that supports clustering and scheduling across machines.
Examples include:
Kubernetes
Docker Swarm

For MLflow to survive a machine failure, its persistent data would also need to live in storage that survives the loss of a single host, such as an external database and shared or remote artifact storage.