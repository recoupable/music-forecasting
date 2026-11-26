"""Run the public benchmark once on Modal with no deployment or credentials in the image."""
from pathlib import Path

import modal

ROOT = Path(__file__).parent
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(ROOT / "requirements.txt"))
    .add_local_python_source("forecasting")
    .add_local_dir(str(ROOT / "experiments"), remote_path="/experiments")
)
app = modal.App("recoup-music-forecasting-evaluation")


@app.function(image=image, cpu=1.0, memory=512, timeout=120)
def public_benchmark():
    from forecasting.benchmark import run

    data = Path("/experiments")
    return run(data / "attention-cohort.json", data / "pageviews.csv.gz")


@app.local_entrypoint()
def main():
    import json

    print(json.dumps(public_benchmark.remote(), indent=2, allow_nan=False))
