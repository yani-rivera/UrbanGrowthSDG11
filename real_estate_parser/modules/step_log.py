import json
from pathlib import Path


def save_step_log(
    log_dir,
    run_id,
    step_name,
    metrics
):
    run_path = Path(log_dir) / run_id

    run_path.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        run_path /
        f"step_{step_name}.json"
    )

    payload = {
        "step": step_name,
        "metrics": metrics
    }

    with open(
        output_file,
        "w",
        encoding="utf-8-sig"
    ) as f:
        json.dump(
            payload,
            f,
            indent=2,
            ensure_ascii=False
        )

    return output_file