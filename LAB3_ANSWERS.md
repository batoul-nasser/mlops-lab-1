### Q1. What version number was your model given? What is the difference between a logged model artifact and a registered model?

My model was registered as **Version 1** of the `food11` model.

A **logged model artifact** belongs to a specific MLflow training run. It is the model file/output produced by that run. A **registered model** gives the model a stable name, such as `food11`, and manages different model versions independently from the training runs that created them. 

### Q2. What aliases replaced the old built-in stages? Why version a model separately, and why is an alias more flexible?

Current MLflow uses **aliases**, such as:

```text
champion
challenger
```

instead of the deprecated stages such as `Staging` and `Production`.

Versioning the model separately is useful because several training runs may create different candidate models, while the registry keeps them organized as versions of the same model.

An alias such as `champion` is more flexible because it is a **mutable pointer**. For example:

```text
food11 version 1 → champion
```

Later, if version 2 is better, I can move:

```text
champion → version 2
```

without changing my serving code. 

### Q3. Why use `models:/food11@champion` instead of directly loading a `.pth` file? What changes for a newer model?

Using:

```python
models:/food11@champion
```

decouples the API from a particular file path or run ID. The application asks MLflow for whichever registered model version currently has the `champion` alias.

If a newer model becomes the preferred model, I only need to move the `champion` alias to the new version. The serving code does not need to contain a new `.pth` path or model version number. 

### Q4. Why copy `pyproject.toml` and `uv.lock` before the source code?

Docker caches image layers.

The dependencies are installed from:

```text
pyproject.toml
uv.lock
```

before copying the application source. This means that if I only modify something small in `serve.py`, Docker can reuse the already-built dependency layer instead of reinstalling all packages.

In our case, when we modified `serve.py` and rebuilt, the rebuild was much faster because the dependency layers were cached. 

### Q5. What is the size difference between a naive single-stage image and your multi-stage image? Which layers are biggest?

My final multi-stage Docker image is:

```text
1.98 GB
```

From `docker history`, the largest layer is:

```text
COPY /app/.venv /app/.venv → 1.41 GB
```

The application source itself is only approximately:

```text
49.2 KB
```

The large size mainly comes from the Python virtual environment and machine-learning libraries such as PyTorch and MLflow.

The benefit of the multi-stage build is that tools needed only during the build stage, such as `uv`, are not copied unnecessarily into the runtime image.

I did not create a separate naive single-stage image, so I cannot provide an exact measured size difference between the two. 

### Q6. What happens if you forget `.dockerignore`? Which excluded folders could cause problems?

Without `.dockerignore`, Docker may send unnecessary files into the build context, such as:

```text
.venv/
data/
mlruns/
mlflow.db
.git/
__pycache__/
```

This can make builds slower and unnecessarily increase the amount of data Docker processes.

Some folders can be especially problematic. For example, `.venv/` may contain packages built specifically for the host operating system, while the Docker container runs Linux. Including local environments or generated files can therefore create conflicts or unnecessary image contents.

Large folders such as `data/` and `mlruns/` can also make the build context much larger even though they are not required inside the image. 

### Q7. Why can't the container use `127.0.0.1:5000` to access MLflow? What is `host.docker.internal`?

A Docker container has its own isolated network environment.

Inside the container:

```text
127.0.0.1
```

means **the container itself**, not my Mac.

Therefore, using:

```text
http://127.0.0.1:5000
```

inside the container would make it look for MLflow inside that container.

On Mac and Windows, Docker provides:

```text
host.docker.internal
```

which resolves to the host machine so the container can access services running on the computer, such as the MLflow tracking server. 

In our implementation, because port `5000` was already occupied on my Mac, we used:

```text
host.docker.internal:5001
```

instead.

### Q8. Does the model still load after restarting the same image? What does that tell you?

Yes. I stopped the container, started another container from the same Docker image, and the prediction still worked.

The API returned:

```json
{
  "category": "Bread",
  "confidence": 0.9435761570930481
}
```

This shows that the application code and Python dependencies are packaged in the Docker image, while the model is resolved from MLflow at runtime through the registered model alias.

In our local setup, the MLflow artifacts were stored in the host `mlruns` directory, so we mounted that directory into the container as well. 

### Q9. What is still missing before another machine or Kubernetes cluster can reliably run the exact image?

The Dockerfile is stored in Git, but the built Docker image currently exists only on my local computer.

To let another machine, CI runner, or Kubernetes cluster run the exact same image, I would need to push the image to a **container registry**, such as Docker Hub or GitHub Container Registry.

I should also use a specific immutable version tag or image digest, for example:

```text
food11-api:v1
```

rather than depending only on:

```text
latest
```

This would let another machine pull the exact Docker image that was tested. 
