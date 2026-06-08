from multiprocessing import Process
import multiprocessing as mp

from app.workers.ml_observer import run as ml_run
from app.workers.risk_engine import run as risk_run
from app.workers.sandbox_executor_v2 import run as sandbox_run
from app.workers.telemetry_writer import run as telemetry_run
from app.workers.classification_writer import run as classification_run
from app.workers.risk_writer import run as risk_writer_run


def main():
    mp.set_start_method("spawn", force=True)

    processes = [
        Process(target=ml_run),
        Process(target=risk_run),
        Process(target=sandbox_run),
        Process(target=telemetry_run),
        Process(target=classification_run),
        Process(target=risk_writer_run),
    ]

    for p in processes:
        p.start()

    for p in processes:
        p.join()


if __name__ == "__main__":
    main()