# Setup: from an empty workspace to a simulated flight

This tutorial targets native Ubuntu Linux on one machine. The recorded live
test used Ubuntu 22.04.5 x86-64. Ubuntu 24.04, WSL2, containers, macOS and Windows
have not been validated for this package. The current QGroundControl AppImage
has a different OS baseline; see its section below.

This local draft is not published yet. Use your provided local checkout for now;
do not expect a GitHub clone URL or PyPI package to work until release.

## 1. Keep the two repositories separate

Suggested layout:

```text
workspace/
  px4-mujoco-bridge/     # this small Python package
  PX4-Autopilot/         # separate, unmodified upstream PX4 source
```

PX4's source, submodules and build can consume several GB. Do not commit that
directory or its build artifacts into the bridge repository. No flight
controller, USB cable, RC transmitter, ROS workspace or Gazebo process is needed.

## 2. Install the Python bridge

On Ubuntu, install the venv support and libraries needed by the interactive
viewer if missing. These commands change system packages; review them first:

```bash
sudo apt update
sudo apt install git python3-venv python3-pip libgl1 libglfw3
```

From the bridge checkout, create an isolated environment:

```bash
cd /absolute/path/to/px4-mujoco-bridge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -c requirements-tested.txt -e '.[test]'
px4-mujoco --version
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

`requirements-tested.txt` pins the three direct runtime dependencies used in
testing; it is not a complete transitive lockfile. The package supports Python
3.10 or newer by metadata, but local live-flight testing used 3.10. Do not install
the bridge system-wide or reuse an unrelated ROS environment for the first test.

The official [MuJoCo Python documentation](https://mujoco.readthedocs.io/en/3.4.0/python.html)
describes the native Python bindings and viewer. MuJoCo physics can run with
`--headless` without opening an OpenGL window; no EGL setup is needed merely to
step physics.

## 3. Get the exact stock PX4 source

Choose a **new** directory. Do not replace or reset a checkout containing your
own firmware work:

```bash
PX4_ROOT=/absolute/path/to/workspace/PX4-Autopilot
git clone --branch v1.17.0 --single-branch https://github.com/PX4/PX4-Autopilot.git "$PX4_ROOT"
git -C "$PX4_ROOT" checkout --detach d6f12ad1c4f70ad3230afd7d86e971421e02fef4
git -C "$PX4_ROOT" submodule update --init --recursive
git -C "$PX4_ROOT" rev-parse HEAD
```

The hash must match the command above. This is the pinned
[PX4 v1.17.0 release](https://github.com/PX4/PX4-Autopilot/releases/tag/v1.17.0),
not a moving `main` branch. Keep submodules at the commits recorded by PX4.
Do not run `git submodule update --remote`.

## 4. Install PX4 build dependencies and build SITL

PX4 provides an [Ubuntu development-environment guide](https://docs.px4.io/v1.17/en/dev_setup/dev_env_linux_ubuntu).
The pinned checkout contains its own dependency installer. **Read it before
running it**: it installs system packages, and its Python-install behavior
depends on Python/Ubuntu versions.

Use a separate build venv so PX4's development packages do not alter the bridge
environment. In a second terminal:

```bash
PX4_ROOT=/absolute/path/to/workspace/PX4-Autopilot
PX4_BUILD_ENV=/absolute/path/to/workspace/px4-build-venv
python3 -m venv "$PX4_BUILD_ENV"
source "$PX4_BUILD_ENV/bin/activate"
python -m pip install --upgrade pip
less "$PX4_ROOT/Tools/setup/ubuntu.sh"
bash "$PX4_ROOT/Tools/setup/ubuntu.sh" --no-nuttx --no-sim-tools
python -m pip install -r "$PX4_ROOT/Tools/setup/requirements.txt"
make -C "$PX4_ROOT" -j4 px4_sitl_default PYTHON_EXECUTABLE="$PX4_BUILD_ENV/bin/python"
```

`--no-nuttx` skips the hardware firmware toolchain; `--no-sim-tools` skips the
other simulator installations. The explicit pip command ensures dependencies
are present in the interpreter passed to CMake. Use fewer jobs if RAM is limited.
On an already configured PX4 development machine, you can skip the installer
after checking dependencies. No `sudo make` is needed.

The output binary should be:

```text
PX4-Autopilot/build/px4_sitl_default/bin/px4
```

Do **not** run `make px4_sitl gz_x500` or a jMAVSim target for this example: that
starts another simulator. The bridge owns the simulator TCP server itself.
No edits to PX4 C++, airframe scripts, mixer files or board configuration are
required. The first build can take several minutes.

The recorded build passed on an existing development host, not on a fresh OS
image. The system dependency installation procedure above still needs a
clean-machine reproduction before release.

## 5. Start both applications

Back in the bridge terminal, activate its venv, not the PX4 build venv:

```bash
cd /absolute/path/to/px4-mujoco-bridge
source .venv/bin/activate
PX4_ROOT=/absolute/path/to/workspace/PX4-Autopilot
px4-mujoco run --px4 "$PX4_ROOT"
```

Expected sequence:

1. The bridge listens on `127.0.0.1:4560`.
2. It launches stock PX4 with a new, isolated parameter store.
3. PX4 connects; the bridge reports its simulator heartbeat.
4. Simulated sensors initialize PX4's estimator. The vehicle stays on the floor.
5. The terminal reports `lockstep=True`. PX4's log should reach `Ready for takeoff!`.

Close the viewer or press Ctrl+C to stop. The launcher cleans up its own PX4
process group, not other PX4 instances. Do not run two instance-0 launchers.

To see motion, stop the first run and start:

```bash
px4-mujoco run --px4 "$PX4_ROOT" --demo
```

This explicitly authorizes **only the launched local SITL vehicle** to switch
to Offboard, arm, climb 2 m, visit the four corners of a 1 m square, return over
the starting point, land and automatically disarm. The demo waits for position
feedback, pre-streams setpoints, checks the observed flight mode and arm state,
and has timeouts. It does not force-arm or bypass PX4 arming checks.

Do not let QGC, another offboard client, or a joystick change flight mode while
this demo runs. The trajectory is a connection example, not a controller
benchmark. A failed demo stops its owned SITL session; this is not a hardware
failsafe or a physical emergency-landing routine.

## QGroundControl (optional)

Download from the [official stable download page](https://docs.qgroundcontrol.com/Stable_V5.1/en/qgc-user-guide/getting_started/download_and_install.html)
or [official releases](https://github.com/mavlink/qgroundcontrol/releases).
Choose the asset matching your OS and architecture, not a daily build.
As checked on 2026-10-14, the current 5.1 Linux AppImages target Ubuntu 24.04/26.04.
On Ubuntu 22.04, keep an already compatible installation or follow QGC's
[source-build guide](https://docs.qgroundcontrol.com/Stable_V5.1/en/qgc-dev-guide/getting_started/).
Do not assume that the newest AppImage runs on the bridge's tested host OS.

For a compatible downloaded Linux x86-64 AppImage, from its download directory:

```bash
chmod +x QGroundControl-x86_64.AppImage
./QGroundControl-x86_64.AppImage
```

Use the exact downloaded filename if different. QGC's download guide lists any
distribution-specific runtime libraries. This localhost-only SITL workflow does
not need USB/serial access, dialout-group changes, firmware flashing, or disabling
ModemManager. Keep real flight controllers disconnected.

Open QGC on the **same OS/network namespace** as PX4. Enable its usual UDP auto
connection; it listens on port `14550`. PX4 sends GCS telemetry there by default.
If needed, create one UDP communication link listening on `14550`; avoid two
listeners fighting for the same port. QGC should show one vehicle and its
synthetic GPS location near Zurich. Do not calibrate real sensors or re-select
an airframe: the launcher already supplies the model's simulated parameters.

QGC is a telemetry/command client, not the physics bridge. Its absence does not
prevent `--demo` from flying. A MuJoCo window and a QGC map serve different
purposes: one renders local physics; the other shows autopilot telemetry.
QGC interaction was not part of the automated validation.

## Ports and multiple runs

| Link | Listening/destination port, instance 0 | Role |
| --- | --- | --- |
| PX4 → bridge | TCP `127.0.0.1:4560` | Simulated sensors and motor reply on one connection |
| PX4 ↔ QGC | PX4 UDP `18570` → QGC UDP `14550` | Ground-station telemetry/commands |
| PX4 ↔ demo | PX4 UDP `14580` → demo UDP `127.0.0.1:14540` | Offboard setpoints and feedback |

For `--instance N` (0–9), TCP and PX4/API UDP ports gain `N`; QGC's destination
stays `14550`. The launcher's MAVLink system ID is `N + 1`. Choose an unused
instance instead of terminating an unknown process. Other stock PX4 links can
also appear in its log; an XRCE-DDS agent is not required here. Multi-instance
operation is implemented but not part of the recorded flight validation.

## Logs, reproducibility and other versions

Each launch creates `runs/sitl-…/`, or a **new** path supplied with
`--output /absolute/path/to/new-run`. Existing output directories are refused.

- `parameters.json`: the bridge's model-derived parameter overrides.
- `px4.log`: PX4 console output, for combined `run` mode.
- `state.csv`: time, NWU position, armed/lockstep flags and maximum motor signal.
- `result.json`: completion, versions, timing, flight extent and demo result.
- `rootfs/`: isolated PX4 parameters and any generated ULog under `log/`.

Initialization failures before entering the simulation loop may not produce
`result.json`; use terminal output and `px4.log`. The source checkout is not
modified. A new run starts from fresh parameters, so QGC tuning is **not** saved
across launches. Put intentional model changes in version-controlled model/code,
then re-test.

`--speed 1` requests real-time pacing. `--duration 15` uses simulated time,
not a guaranteed wall-clock deadline. Faster/slower pacing is experimental for
telemetry clients; start with the default.

To experiment with a different PX4 checkout, use `--allow-other-px4` explicitly.
First run an unarmed check, then verify allocation, thrust mapping and the full
demo. A successful build or TCP connection alone is not compatibility validation.
Do not silently advance the documented pinned baseline to `main`.

For frame conventions, bridge-only integration, and model changes, continue with
[architecture](architecture.md), [model contract](models.md) and
[troubleshooting](troubleshooting.md).
