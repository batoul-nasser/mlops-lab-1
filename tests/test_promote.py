from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import RESOURCE_DOES_NOT_EXIST

from src.food11.promote import evaluation_size, positive_version, promote


def run(accuracy=0.7, **params):
    return SimpleNamespace(info=SimpleNamespace(run_id="run"), data=SimpleNamespace(
        metrics={"test_accuracy": accuracy}, params={"dataset": "mini", "test_size": "100", **params}
    ))


@pytest.fixture
def client():
    client = Mock()
    client.get_model_version.return_value = SimpleNamespace(version="2", run_id="candidate")
    client.get_model_version_by_alias.return_value = SimpleNamespace(version="1", run_id="champion")
    return client


@pytest.mark.parametrize("candidate,expected,alias", [(0.9, "PROMOTED", "champion"), (0.71, "CHALLENGER", "challenger")])
def test_quality_gate(client, candidate, expected, alias):
    client.get_run.side_effect = [run(candidate), run()]
    assert promote(client, "2") == expected
    client.get_model_version.assert_called_once_with("food11", "2")
    client.get_model_version_by_alias.assert_called_once_with("food11", "champion")
    client.set_registered_model_alias.assert_called_once_with("food11", alias, "2")
    tags = {call.args[2]: call.args[3] for call in client.set_model_version_tag.call_args_list}
    assert tags["promotion.decision"] == expected
    assert float(tags["promotion.required_accuracy"]) == pytest.approx(0.7 + 2 * (0.7 * 0.3 / 100) ** 0.5)


def test_already_champion(client):
    client.get_model_version.return_value.version = "1"
    assert promote(client, "1") == "ALREADY CHAMPION"
    client.set_registered_model_alias.assert_not_called()


def test_missing_champion(client):
    client.get_model_version_by_alias.side_effect = MlflowException("missing", error_code=RESOURCE_DOES_NOT_EXIST)
    with pytest.raises(ValueError, match="baseline"):
        promote(client, "2")
    client.set_registered_model_alias.assert_not_called()


def test_missing_version(client):
    client.get_model_version.side_effect = MlflowException("version missing")
    with pytest.raises(MlflowException):
        promote(client, "99")
    client.set_registered_model_alias.assert_not_called()


@pytest.mark.parametrize("value", [None, float("nan"), -0.1, 1.1])
def test_invalid_metric(client, value):
    candidate = run(value)
    if value is None:
        candidate.data.metrics.clear()
    client.get_run.side_effect = [candidate, run()]
    with pytest.raises(ValueError, match="test_accuracy"):
        promote(client, "2")
    client.set_registered_model_alias.assert_not_called()


def test_actual_local_size_fallback(tmp_path):
    folder = tmp_path / "data/food11_processed_mini/evaluation/Bread"
    folder.mkdir(parents=True)
    (folder / "one.jpg").write_bytes(b"count supported filenames like ImageFolder")
    (folder / "ignore.txt").write_text("metadata")
    candidate, champion = run(), run()
    for item in (candidate, champion):
        item.data.params.pop("test_size")
    assert evaluation_size(candidate, champion, tmp_path)[0] == 1


@pytest.mark.parametrize("params", [{"dataset": "processed"}, {"test_size": "99"}, {"test_size": "0"}])
def test_incomparable_evaluations(params):
    with pytest.raises(ValueError):
        evaluation_size(run(**params), run())


@pytest.mark.parametrize("version", ["0", "-1", "abc", "1.5"])
def test_invalid_version(version):
    import argparse

    with pytest.raises(argparse.ArgumentTypeError):
        positive_version(version)


def test_quality_gate_includes_threshold(client):
    client.get_run.side_effect = [run(1.0), run(1.0)]
    assert promote(client, "2") == "PROMOTED"


def test_missing_historical_dataset(tmp_path):
    candidate, champion = run(), run()
    for item in (candidate, champion):
        item.data.params.pop("test_size")
    with pytest.raises(ValueError, match="restore"):
        evaluation_size(candidate, champion, tmp_path)
