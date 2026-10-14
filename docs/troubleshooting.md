# Troubleshooting

Start with the generated `px4.log`, terminal output and `result.json`. Share a
minimal reproduction, not your entire workspace or unredacted personal logs.

## Installation or build

| Symptom | Check / next step |
| --- | --- |
| `px4-mujoco: command not found` | Activate the bridge venv; run `python -m pip install -c requirements-tested.txt -e '.[test]'` from this repository. |
| Wrong module imported | Run from this standalone checkout, not another project containing a package with the same name. Check `python -c 'import px4_mujoco_bridge; print(px4_mujoco_bridge.__file__)'`. |
| pytest imports ROS plugins or complains about unrelated packages | Use `env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`; use a dedicated venv. |
| PX4 cannot find `em`, `kconfiglib`, YAML or code-generation packages | Install the pinned checkout's `Tools/setup/requirements.txt` into its build interpreter and pass `PYTHON_EXECUTABLE` explicitly as shown in setup. |
| PX4 missing submodule source | Run `git -C "$PX4_ROOT" submodule update --init --recursive`; do not update submodules to their latest branches. |
| Build stops with a killed compiler | Reduce parallel jobs; check RAM/swap and disk space. |
| PX4 commit/dirty-tree rejection | Use the separate pinned stock checkout. Do not discard your firmware edits. `--allow-other-px4` is an explicit experiment, not a fix for unknown compatibility. |

## No connection or no sensor exchange

| Symptom | Check / next step |
| --- | --- |
| Address already in use | Inspect listeners with `ss -ltnp` and `ss -lunp`. Use an unused `--instance` or stop the specific run you own. Do not kill all PX4 processes. |
| Waiting for simulator heartbeat | Start with the combined `run` command; verify the owned PX4 has not exited. Simulator TCP port is `4560 + instance`, not QGC's 14550. |
| PX4 tries Gazebo/jMAVSim | Use the combined launcher and a clean stock checkout. Do not start a separate `make ... gz_*` simulator target. |
| No actuators during bootstrap | Inspect PX4 startup/parameter errors in `px4.log`. Verify model-derived output-function mapping and the stock simulator module. |
| Actuator timeout after lockstep | PX4 stopped replying to the current simulated timestamp. The bridge deliberately does not advance with stale commands. Check process health, source version and simulator link. |
| Remote PC or Windows QGC cannot see it | Default workflow is same-host loopback. WSL/VM/container networking and remote hosts are not configured or validated; do not expose MAVLink ports to the internet. |

The bridge speaks MAVLink 2 directly. There is no serial baud rate to set, no
ROS topic required, and no micro XRCE-DDS agent needed for this workflow.

## Vehicle does not move or flies incorrectly

The default launch does not arm. Use `--demo` explicitly for the automatic
trajectory; allow roughly 10–15 simulated seconds for initial estimator and
Offboard setup. Do not force-arm around a reported preflight failure.

If a modified model tips, spins or cannot hover, check the four mappings first:

1. HIL slot order matches MJCF actuator order and PX4 Motor1… functions.
2. NWU/FLU versus NED/FRD signs are correct, including attitude and gyro.
3. Thrust is `T_max × signal²`, paired with PX4 `THR_MDL_FAC=1`.
4. Lever arms and signed reaction torques agree with PX4 allocation.

A hovering motor signal near 0.606 is expected for the included model; its
normalized thrust is about 0.368. They are not the same quantity.
Do not change one side of the motor curve without updating the other.

`Demo local position became stale` means recent position feedback was missing;
other telemetry alone is not sufficient. `Demo timed out` or an offboard-mode
exit needs inspection of command ACKs, EKF health and other connected clients.
Stop competing controllers. The demo reports success only after observed landing
and disarming, not merely after a takeoff command was accepted.

## Viewer, QGC and time

- **No display / GLFW error:** run `--headless` to check physics independently.
  For the viewer, use a graphical session with working OpenGL and the correct
  display permissions. A terminal-only SSH session normally has no display.
- **QGC AppImage will not start on Ubuntu 22.04:** current 5.1 AppImages target
  newer Ubuntu releases; follow the linked official guidance in
  [setup](setup.md#qgroundcontrol-optional). Do not replace system glibc manually.
- **QGC shows no vehicle:** check its UDP auto-connect/listen port 14550, that
  PX4 is still running, and that both are in the same network namespace.
  TCP 4560 is not a QGC communication link.
- **QGC marks Radio/Flight Modes as requiring setup:** this example intentionally
  has no RC and uses `COM_RC_IN_MODE=4`. This was observed while the demo still
  passed normal PX4 arming checks and completed its flight. Do not force-arm or
  bypass unrelated preflight failures; inspect PX4's own messages.
- **Synthetic location near Zurich:** intentional default GPS origin, unrelated
  to where your computer is. The MuJoCo local floor is not a georeferenced map.
- **Old date in ULog filenames:** intentional fixed synthetic GPS epoch, not a
  claim that a test happened on that date. Record your actual run date separately.
- **Simulation slower than wall time:** lockstep can slow down to wait for PX4.
  Test headlessly first. `--speed` requests pacing; it does not guarantee compute
  performance or telemetry timing.
- **Settings disappear next run:** intentional isolated parameter store. Keep
  reproducible overrides in the model/code, not a leftover SITL parameter file.

## What to include in a bug report

Include OS/architecture, Python/package versions, PX4 commit, exact launch
command (redact personal paths), stock or custom model, `result.json`, and the
relevant PX4 error lines. State whether `--headless` reproduces it. Do not attach
credentials, unrelated CAD, real flight logs or sensitive host information.
Use the [issue tracker](https://github.com/Holiday-66/px4-mujoco-bridge/issues)
for non-sensitive reports. Follow [SECURITY.md](../SECURITY.md) for vulnerabilities.
