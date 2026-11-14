"""Promote a Food-11 version using the existing runs' test_accuracy metric."""

import argparse
import math
import os
from pathlib import Path

from mlflow.exceptions import MlflowException
from torchvision.datasets.folder import IMG_EXTENSIONS

from mlflow import MlflowClient

MODEL_NAME = "food11"
METRIC = "test_accuracy"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def positive_version(value):
    try:
        version = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("version must be a positive integer") from exc
    if version < 1:
        raise argparse.ArgumentTypeError("version must be a positive integer")
    return str(version)


def accuracy(run):
    value = run.data.metrics.get(METRIC)
    if value is None or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"run {run.info.run_id} needs a finite {METRIC} in [0, 1]")
    return value


def evaluation_size(candidate_run, champion_run, root=PROJECT_ROOT):
    """Prefer logged sizes; support historical runs using their actual local split."""
    params = [run.data.params for run in (candidate_run, champion_run)]
    dataset = params[0].get("dataset")
    if dataset not in {"mini", "processed"} or params[1].get("dataset") != dataset:
        raise ValueError("both runs must use the same known dataset (mini or processed)")
    sizes = [p.get("test_size") for p in params]
    if all(size is not None for size in sizes):
        if sizes[0] != sizes[1] or not sizes[0].isdigit() or int(sizes[0]) < 1:
            raise ValueError("runs must record the same positive test_size")
        return int(sizes[0]), "test_size logged by both runs"
    folder = "food11_processed_mini" if dataset == "mini" else "food11_processed"
    evaluation = root / "data" / folder / "evaluation"
    if not evaluation.is_dir():
        raise ValueError(f"historical runs have no test_size; restore the matching DVC data at {evaluation}")
    # Match ImageFolder's supported image extensions and class directories.
    count = sum(
        1 for category in evaluation.iterdir() if category.is_dir()
        for path in category.rglob("*")
        if path.is_file() and path.suffix.lower() in IMG_EXTENSIONS
    )
    if count < 1 or any(size is not None and size != str(count) for size in sizes):
        raise ValueError("local evaluation size is empty or disagrees with a logged test_size")
    return count, f"local {evaluation}; historical fallback: restore the runs' matching DVC revision"


def promote(client, version, root=PROJECT_ROOT):
    candidate = client.get_model_version(MODEL_NAME, version)
    try:
        champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException as exc:
        if exc.error_code == "RESOURCE_DOES_NOT_EXIST":
            raise ValueError("champion alias is missing; choose a reviewed baseline before promotion") from exc
        raise
    if str(candidate.version) == str(champion.version):
        print(f"Decision: ALREADY CHAMPION (version {version}); no aliases changed")
        return "ALREADY CHAMPION"
    if not candidate.run_id or not champion.run_id:
        raise ValueError("both model versions must reference their originating run")
    candidate_run = client.get_run(candidate.run_id)
    champion_run = client.get_run(champion.run_id)
    candidate_accuracy = accuracy(candidate_run)
    champion_accuracy = accuracy(champion_run)
    n, size_source = evaluation_size(candidate_run, champion_run, root)
    se = math.sqrt(champion_accuracy * (1 - champion_accuracy) / n)
    threshold = champion_accuracy + 2 * se
    decision = "PROMOTED" if candidate_accuracy >= threshold else "CHALLENGER"
    tags = {
        "promotion.decision": decision,
        "promotion.metric": METRIC,
        "promotion.candidate_accuracy": candidate_accuracy,
        "promotion.champion_accuracy": champion_accuracy,
        "promotion.champion_version": champion.version,
        "promotion.test_size": n,
        "promotion.test_size_source": size_source,
        "promotion.standard_error": se,
        "promotion.two_se": 2 * se,
        "promotion.required_accuracy": threshold,
    }
    for key, value in tags.items():
        client.set_model_version_tag(MODEL_NAME, version, key, str(value))
    alias = "champion" if decision == "PROMOTED" else "challenger"
    client.set_registered_model_alias(MODEL_NAME, alias, version)
    print(f"Champion version: {champion.version}")
    print(f"Candidate version: {version}")
    print(f"Champion accuracy: {champion_accuracy:.8f}")
    print(f"Candidate accuracy: {candidate_accuracy:.8f}")
    print(f"Test-set size: {n} ({size_source})")
    print(f"2*SE: {2 * se:.8f}")
    print(f"Required accuracy: {threshold:.8f}")
    print(f"Decision: {decision}; {alias} -> {version}")
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=positive_version, required=True)
    args = parser.parse_args()
    uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    try:
        promote(MlflowClient(tracking_uri=uri), args.version)
    except (MlflowException, ValueError, OSError) as exc:
        parser.exit(1, f"Promotion failed: {exc}\n")


if __name__ == "__main__":
    main()
