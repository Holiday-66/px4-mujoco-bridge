"""Launch a loopback-only MuJoCo bridge, optionally with an owned PX4 SITL process."""
import argparse
from contextlib import ExitStack
import csv
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import mujoco
import numpy as np

from . import __version__
from .model import Aircraft, default_model, motor_thrust
from .sensors import Sensors
from .transport import Transport

PX4_TAG = "v1.17.0"
PX4_COMMIT = "d6f12ad1c4f70ad3230afd7d86e971421e02fef4"


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return number


def px4_environment(parameters, instance, environ=None):
    # Do not inherit research-airframe overrides or a remote simulator target.
    source = os.environ if environ is None else environ
    env = {k: v for k, v in source.items() if not k.startswith("PX4_")}
    env.update(PX4_SYS_AUTOSTART="10016", PX4_SIM_MODEL="none_iris", PX4_SIMULATOR="mujoco",
               PX4_SIM_HOST_ADDR="127.0.0.1", PX4_PARAM_MAV_SYS_ID=str(instance + 1))
    env.update({"PX4_PARAM_" + k: str(v) for k, v in parameters.items()})
    env["PX4_PARAM_MAV_SYS_ID"] = str(instance + 1)
    return env


def validate_px4(root, allow_other=False):
    root = Path(root).resolve()
    build = root / "build/px4_sitl_default"
    binary = build / "bin/px4"
    if not binary.is_file() or not os.access(binary, os.X_OK) or not (build / "etc/init.d-posix/rcS").is_file():
        raise ValueError(f"Build stock PX4 first: make -C {root} px4_sitl_default")
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
    if (commit != PX4_COMMIT or dirty) and not allow_other:
        raise ValueError(f"Expected clean stock {PX4_TAG} ({PX4_COMMIT}); use --allow-other-px4 only for explicit compatibility experiments")
    return root, build, binary, commit, bool(dirty)


def stop_owned_process(process):
    if process.poll() is None:
        # New session: signals target only this launcher's child process group.
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)


def run(args):
    aircraft = Aircraft(args.model)
    dt = float(aircraft.model.opt.timestep)
    substeps = round(0.004 / dt)
    if substeps < 1 or not math.isclose(substeps * dt, 0.004, abs_tol=1e-10):
        raise ValueError("The physics timestep must divide the 0.004 s HIL interval exactly")
    px4 = validate_px4(args.px4, args.allow_other_px4) if args.command == "run" else None
    aircraft.reset()
    sensors = Sensors(aircraft)
    params = aircraft.px4_parameters()
    port = 4560 + args.instance
    print(f"Simulator TCP server: 127.0.0.1:{port}; no physical devices are accessed", flush=True)
    result = {"bridge_version": __version__, "mujoco_version": mujoco.__version__,
              "instance": args.instance, "completed": False, "demo": args.demo,
              "lockstep_seen": False, "startup_steps": 0, "steps": 0,
              "max_height_m": 0.0, "max_horizontal_distance_m": 0.0}
    with ExitStack() as stack:
        transport = Transport(port)
        stack.callback(transport.close)
        output = Path(args.output).resolve() if args.output else None
        if output is not None:
            output.mkdir(parents=True, exist_ok=False)
        else:
            Path("runs").mkdir(exist_ok=True)
            output = Path(tempfile.mkdtemp(prefix="sitl-", dir="runs")).resolve()
        print(f"Run directory: {output}", flush=True)
        (output / "parameters.json").write_text(json.dumps(params, indent=2) + "\n")
        process = None
        if px4:
            root, build, binary, commit, dirty = px4
            result.update(px4_commit=commit, px4_dirty=dirty)
            work = output / "rootfs"
            work.mkdir()
            log = stack.enter_context((output / "px4.log").open("w"))
            process = subprocess.Popen([str(binary), "-d", "-i", str(args.instance), "-w", str(work), str(build / "etc")],
                cwd=root, env=px4_environment(params, args.instance), stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True)
            stack.callback(stop_owned_process, process)
            print(f"PX4 started; QGroundControl listens on UDP 14550. PX4 log: {output / 'px4.log'}", flush=True)
            print(f"Local console client example: {build / 'bin/px4-commander'} --instance {args.instance} status", flush=True)
        demo = None
        if args.demo:
            from .demo import Demo
            demo = Demo(args.instance)
            stack.callback(demo.close)
            print("Explicit SITL demo enabled: arm, climb 2 m, fly a 1 m square, land", flush=True)
        viewer = None
        if not args.headless:
            from mujoco import viewer as viewer_module
            viewer = stack.enter_context(viewer_module.launch_passive(aircraft.model, aircraft.data))
            viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = 4.5, 135, -25
            viewer.cam.lookat[:] = [0.4, -0.4, 0.8]
        trace = stack.enter_context((output / "state.csv").open("w", newline=""))
        writer = csv.writer(trace)
        writer.writerow(["time_s", "north_m", "west_m", "up_m", "armed", "lockstep", "max_motor_signal"])
        try:
            transport.connect(timeout=args.connect_timeout)
            print("PX4 simulator heartbeat received", flush=True)
            wall_start = time.monotonic()
            seen_lockstep = False
            last_report, last_view, last_trace = -1, -1.0, -1.0
            while args.duration is None or aircraft.data.time < args.duration:
                if process is not None and process.poll() is not None:
                    raise RuntimeError(f"Owned PX4 exited with status {process.returncode}; inspect px4.log")
                if viewer is not None and not viewer.is_running():
                    break
                sample = sensors.sample()
                transport.sensors(sample)
                frame = transport.actuators(after_us=sample["time_us"] if seen_lockstep else 0,
                                             timeout=2.0 if seen_lockstep else 0.02)
                if frame is None:
                    if seen_lockstep:
                        raise TimeoutError("PX4 actuator timeout: physics was not advanced without a fresh lockstep reply")
                    if time.monotonic() - wall_start > 30:
                        raise TimeoutError("PX4 produced no actuator data during bootstrap; inspect px4.log")
                    controls, armed = np.zeros(16), False
                    result["startup_steps"] += 1
                else:
                    controls, armed = frame.controls, frame.armed
                    seen_lockstep |= frame.lockstep
                aircraft.data.ctrl[:] = motor_thrust(controls, aircraft.maximum, armed)
                for _ in range(substeps):
                    mujoco.mj_step(aircraft.model, aircraft.data)
                t = float(aircraft.data.time)
                if not np.isfinite(aircraft.data.qpos).all() or not np.isfinite(aircraft.data.qvel).all():
                    raise RuntimeError("Non-finite MuJoCo state")
                if demo:
                    demo.tick(t)
                position = aircraft.data.qpos[:3]
                result["steps"] += 1
                result["lockstep_seen"] = seen_lockstep
                result["max_height_m"] = max(result["max_height_m"], float(position[2]))
                result["max_horizontal_distance_m"] = max(result["max_horizontal_distance_m"], float(np.linalg.norm(position[:2])))
                if t - last_trace >= 0.02:
                    writer.writerow([t, *position, int(armed), int(seen_lockstep), float(np.max(controls[:aircraft.model.nu]))])
                    last_trace = t
                if viewer is not None and t - last_view >= 1 / 30:
                    viewer.sync()
                    last_view = t
                if int(t) != last_report:
                    print(f"t={t:7.3f}s  position NWU={np.round(position, 3)}  armed={armed}  lockstep={seen_lockstep}", flush=True)
                    last_report = int(t)
                if demo and demo.finished:
                    result["demo_waypoints"] = demo.waypoint + 1
                    result["demo_landed_disarmed"] = demo.landed and not demo.armed
                    if demo.failure:
                        raise RuntimeError(demo.failure)
                    result["completed"] = True
                    break
                # Pacing limits wall-clock speed but never defines simulation timestamps.
                delay = wall_start + t / args.speed - time.monotonic()
                if delay > 0:
                    time.sleep(min(delay, 0.05))
            if not demo:
                result["completed"] = seen_lockstep
            if demo and not result["completed"]:
                raise RuntimeError("Demo stopped before confirmed landing/disarm")
        except BaseException as error:
            result["error"] = str(error) or type(error).__name__
            raise
        finally:
            result["simulation_seconds"] = float(aircraft.data.time)
            if demo:
                result["demo_phase"] = demo.phase
                result["command_acknowledgments"] = demo.acknowledgments
            (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(f"Result: {output / 'result.json'}", flush=True)
    return 0


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("run", "bridge"):
        sub = commands.add_parser(name, help="Launch PX4 and bridge" if name == "run" else "Bridge only; start PX4 separately")
        if name == "run":
            sub.add_argument("--px4", required=True, type=Path, help="Stock PX4 source root with built SITL")
            sub.add_argument("--allow-other-px4", action="store_true", help="Explicitly bypass the tested source-version guard")
            sub.add_argument("--demo", action="store_true", help="Explicitly arm and fly ONLY the owned local SITL process")
        else:
            sub.set_defaults(demo=False, allow_other_px4=False)
        sub.add_argument("--model", type=Path, default=default_model())
        sub.add_argument("--instance", type=int, choices=range(10), default=0)
        sub.add_argument("--headless", action="store_true")
        sub.add_argument("--duration", type=positive, help="Stop after this many simulated seconds")
        sub.add_argument("--speed", type=positive, default=1.0, help="Requested real-time factor; not a performance guarantee")
        sub.add_argument("--connect-timeout", type=positive, default=30)
        sub.add_argument("--output", type=Path, help="New run directory; must not already exist")
    sub = commands.add_parser("parameters", help="Print model-derived PX4 environment settings")
    sub.add_argument("--model", type=Path, default=default_model())
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    def terminate(signum, frame):
        raise KeyboardInterrupt
    previous_sigterm = signal.signal(signal.SIGTERM, terminate)
    try:
        if args.command == "parameters":
            for key, value in Aircraft(args.model).px4_parameters().items():
                print(f"export PX4_PARAM_{key}={value}")
            return 0
        return run(args)
    except KeyboardInterrupt:
        print("Stopped; only the launcher's own PX4 child is cleaned up", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"px4-mujoco: {error}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
