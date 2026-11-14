Lab 5 – CI/CD with GitHub Actions

Q1. Why should unit tests not load the real MLflow model?

Unit tests should be fast, isolated, and reproducible. Loading the real model from MLflow would make the test depend on external services.

The test could fail even if the code is correct because:

the MLflow server may be offline or unreachable;

the network may fail;

the model or champion alias may not exist;

downloading the model may take a long time;

the CI runner may not have access to the required model artifacts.

For this reason, the tests use SKIP_MODEL=1 and replace the real model with a fake model.

Q2. What does the fake-model API test prove?

The API test proves that the serving code works correctly around the model.

It checks that:

an image can be uploaded;

the image can be decoded and transformed;

the /predict endpoint works;

the predicted class is converted correctly to a category;

the response contains a confidence between 0 and 1;

the API returns a valid JSON response with HTTP 200.

It does not prove that the real Food-11 model is accurate. The fake model always produces a known result, so the test checks the API logic rather than model quality.

Q3. Which validation check detected the duplicated image?

The cross-split duplicate check detected it.

The validator computes an MD5 hash of every image and compares the hashes between the training, validation, and evaluation splits.

A duplicated image is more dangerous than a corrupted image because a corrupted image usually causes an obvious error during loading or training. A duplicated image may not cause any error at all.

Instead, it creates data leakage. If an evaluation image was also seen during training, the measured accuracy may be artificially high and no longer represent real generalization performance.

During the lab, existing duplicates in the mini dataset were also detected and repaired before the final validation.

Q4. Where can validate_data.py run if GitHub Actions cannot access the DVC dataset?

Two suitable places are:

The data preparation pipeline, immediately after preprocessing and before publishing the new dataset with DVC.

A self-hosted runner or training machine that already has access to the DVC remote and its credentials.

The normal GitHub Actions unit-test workflow should remain independent from the full DVC dataset.

Q5. What does needs: test do for the smoke job?

The workflow contains:

smoke:
  needs: test

This means the smoke job runs only if the test job succeeds.

If a unit test fails, the smoke test is skipped. This avoids wasting time building a Docker image when the code has already failed its basic checks.

Without needs: test, the jobs could run independently or in parallel.

Q6. How long did the two CI runs take?

First CI run

Job

Duration

Test

25 s

Smoke

1 min 48 s

Push

3 min 56 s

Total

6 min 16 s

Second CI run

Job

Duration

Test

26 s

Smoke

1 min 49 s

Push

22 s

Total

2 min 44 s

The main improvement was in the push job, which decreased from 3 min 56 s to 22 s.

The reason is caching. On the second run, GitHub Actions could reuse previously built Docker layers instead of rebuilding and uploading everything again.

The test and smoke jobs stayed almost unchanged.

Q7. Why tag Docker images with the commit SHA instead of latest?

A commit SHA identifies one exact version of the source code.

For example:

ghcr.io/batoul-nasser/mlops-lab-1:d842aaf...

points to the image produced from that exact Git commit.

Using only latest is ambiguous because the tag can change over time.

For example, Machine A could pull latest in the morning, then a new image could be published, and Machine B could pull latest later. Both machines would say they are running latest, but they could actually be running different code.

Using the commit SHA makes deployments reproducible and traceable.

Q8. Why does the push job declare permissions explicitly?

The workflow uses:

permissions:
  contents: read
  packages: write

This follows the principle of least privilege.

The job only needs:

read access to the repository;

write access to GitHub Packages so it can push the Docker image to GHCR.

Giving the token more permissions than necessary would increase the security risk. If a compromised action had broad write permissions, it could potentially modify repository content, packages, releases, or other resources.

Q9. What happens when a test is broken in a pull request?

If a test is deliberately broken, GitHub Actions shows a failed check on the pull request.

Because smoke depends on test, the pipeline stops before continuing to the later stages.

With branch protection configured to require the test and smoke checks, the pull request cannot be merged until the required checks pass.

After the code is fixed and pushed again, GitHub reruns the workflow automatically. Once the required checks are green, the pull request can be merged.

This is better than relying on every developer to manually run tests before pushing because the checks are automatic, consistent, visible, and enforceable.

The branch-protection experiment should be updated with the actual observed result once it is performed on GitHub.

Q10. What did the model promotion gate decide?

The current champion accuracy was 74.9088%.

The test-set size was:

n = 1096

The promotion rule was:

candidate accuracy >= champion accuracy + 2 × SE

where:

SE = sqrt(p × (1 - p) / n)

The resulting required accuracy was 77.5279%.

Therefore:

2 × SE ≈ 2.6191 percentage points

Candidate 1

Accuracy: 16.9708%

Since:

16.9708% < 77.5279%

the candidate was not promoted.

Decision: challenger

Candidate 2

Accuracy: 75.1825%

Since:

75.1825% < 77.5279%

this candidate was also not promoted.

Decision: challenger

Final model aliases:

champion   → Version 1
challenger → Version 3

These accuracy values came from the original dataset before the mini-dataset duplicate repair. A future comparison should evaluate all candidates using the same repaired evaluation split.

Q11. How could promote.py run automatically if MLflow is currently on the laptop?

Two possible solutions are:

1. Use a hosted MLflow server

The MLflow tracking server could be hosted remotely, for example using DagsHub.

GitHub Actions could then connect to it using the server URL and credentials stored as GitHub secrets.

2. Use a self-hosted GitHub Actions runner

A self-hosted runner could run on a machine that can access the local MLflow server.

That runner could execute:

uv run python src/food11/promote.py --version <version>

after a new model is trained and registered.

Another valid approach would be to execute the promotion script directly from the training infrastructure.

Q12. CI/CD pipeline

Code pipeline

git push
   │
   ▼
GitHub Actions
   │
   ▼
test
   ├── Ruff
   └── Pytest
   │
   ▼
smoke
   ├── Docker build
   └── /health check
   │
   ▼
main branch only
   │
   ▼
Push image to GHCR
   │
   ▼
Image tagged with Git commit SHA

Most of this pipeline is automatic.

The code version is determined by the Git commit SHA, which is also used as the Docker image tag.

Model pipeline

Training
   │
   ▼
MLflow run
   │
   ▼
Registered model version
   │
   ▼
Promotion quality gate
   │
   ├── Pass → champion
   └── Fail → challenger

The model version is selected independently from the code version.

The Docker image contains the serving application and its dependencies, while the MLflow alias determines which registered model version should be served.

Final Summary

The final CI/CD flow is:

git push
   ↓
GitHub Actions
   ↓
Ruff + Pytest
   ↓
Docker build
   ↓
Container health smoke test
   ↓
Push to GHCR on main
   ↓
Docker image tagged with Git commit SHA

The model lifecycle is separate:

Train model
   ↓
Register in MLflow
   ↓
Run promotion quality gate
   ↓
champion or challenger

This gives independent versioning for the two main artifacts:

Code version  → Git commit SHA / Docker image
Model version → MLflow model version / alias