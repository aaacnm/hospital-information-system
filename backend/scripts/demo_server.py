"""Run the local classroom demo and accept a private file-based stop signal."""

import argparse
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path


def write_state(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".pending")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--instance", required=True)
    args = parser.parse_args()
    state_path = args.state_dir / "running.json"
    stop_path = args.state_dir / f"stop-{args.instance}.signal"
    state = {
        "project_root": str(Path(__file__).resolve().parents[2]),
        "pid": os.getpid(),
        "parent_pid": os.getppid(),
        "instance_id": args.instance,
        "python_path": sys.executable,
        "port": args.port,
        "url": f"http://127.0.0.1:{args.port}",
        "started_at": datetime.now().isoformat(),
        "status": "starting",
    }
    args.state_dir.mkdir(parents=True, exist_ok=True)
    # The lock is released by Windows even when the previous process was interrupted.
    import msvcrt

    with (args.state_dir / "server.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        write_state(state_path, state)
        try:
            from scripts.init_db import main as migrate
            from scripts.seed import main as seed
            from scripts.seed_showcase import main as showcase

            migrate()
            seed()
            showcase()
            if stop_path.exists():
                return

            import uvicorn

            server = uvicorn.Server(
                uvicorn.Config("app.main:app", host="127.0.0.1", port=args.port, log_level="info")
            )
            finished = threading.Event()

            def monitor() -> None:
                ready = False
                while not finished.wait(0.25):
                    if stop_path.exists():
                        server.should_exit = True
                        return
                    if server.started and not ready:
                        ready = True
                        state["status"] = "running"
                        write_state(state_path, state)

            watcher = threading.Thread(target=monitor, daemon=True)
            watcher.start()
            try:
                server.run()
            finally:
                finished.set()
                watcher.join()
        except BaseException as error:
            state["status"] = "failed"
            state["error"] = str(error) or type(error).__name__
            raise
        finally:
            if state["status"] != "failed":
                state["status"] = "stopped"
            write_state(state_path, state)
            stop_path.unlink(missing_ok=True)
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == "__main__":
    main()
