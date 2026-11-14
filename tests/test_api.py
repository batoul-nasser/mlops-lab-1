from pathlib import Path
from unittest.mock import Mock

import pytest
import torch
from fastapi.testclient import TestClient

from src.food11 import serve

FIXTURE = Path(__file__).parent / "fixtures" / "bread.jpg"


class FakeModel:
    def __call__(self, x):
        assert x.shape == (1, 3, 128, 128)
        assert not torch.is_grad_enabled()
        return torch.tensor([[5.0] + [0.0] * 10])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SKIP_MODEL", "1")
    monkeypatch.setattr(serve, "model", None)

    def unexpected_load(*args, **kwargs):
        pytest.fail("unit tests must not load the real MLflow model")

    monkeypatch.setattr(serve.mlflow.pytorch, "load_model", unexpected_load)
    with TestClient(serve.app) as test_client:
        yield test_client


def test_health_without_model(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict(client, monkeypatch):
    monkeypatch.setattr(serve, "model", FakeModel())
    with FIXTURE.open("rb") as image:
        response = client.post("/predict", files={"file": ("bread.jpg", image, "image/jpeg")})
    assert response.status_code == 200
    result = response.json()
    assert result["category"] == "Bread"
    assert 0 <= result["confidence"] <= 1
    assert result["confidence"] == pytest.approx(torch.softmax(torch.tensor([5.0] + [0.0] * 10), 0)[0].item())


def test_predict_without_model(client):
    response = client.post("/predict", files={"file": ("bread.jpg", FIXTURE.read_bytes(), "image/jpeg")})
    assert response.status_code == 503


def test_startup_loads_pytorch_champion(monkeypatch):
    monkeypatch.delenv("SKIP_MODEL", raising=False)
    monkeypatch.setattr(serve, "model", None)
    fake = Mock()
    loader = Mock(return_value=fake)
    monkeypatch.setattr(serve.mlflow.pytorch, "load_model", loader)
    monkeypatch.setattr(serve.mlflow, "set_tracking_uri", Mock())
    with TestClient(serve.app):
        loader.assert_called_once_with("models:/food11@champion", map_location="cpu")
        fake.eval.assert_called_once()
        assert serve.model is fake
