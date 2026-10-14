# Validation record

Local checks performed on **2026-10-14**. This records observed software behavior,
not hardware-flight readiness, calibrated plant accuracy or a clean-machine
installation certification. No public CI or package publication has occurred.

## Environment

| Component | Recorded version |
| --- | --- |
| Host | Ubuntu 22.04.5 LTS, x86-64 |
| Bridge interpreter | Python 3.10.19, isolated venv |
| MuJoCo | 3.4.0 |
| NumPy | 2.2.6 |
| pymavlink | 2.4.49 |
| pytest | 8.4.2 |
| PX4 | Stock v1.17.0, commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` |
| PX4 compiler / CMake | GCC 11.4.0 / CMake 3.22.1 |
| PX4 build interpreter | Existing host Python 3.13.5, separate from bridge venv |

PX4 was cloned into a new checkout with its pinned submodules and built using
`make -j6 px4_sitl_default`. Tracked source files remained clean. The host already
had development dependencies, including optional simulator libraries. We did not
run the system dependency installer or reproduce an empty OS image.

## Checks and outcomes

| Check | Result |
| --- | --- |
| Headless unit/regression suite | **32 passed** |
| Stock PX4 SITL build | **Passed** |
| Unarmed 15 s lockstep run | **Passed**, PX4 reported ready for takeoff |
| Full opt-in flight demo | **Passed twice**, all five targets, landed and disarmed |
| Wheel/source-distribution build | **Passed** |
| Wheel installation into a separate fresh venv | **Passed**, bundled MJCF loads outside the source tree |
| Installed-wheel 15 s stock-PX4 run | **Passed**, unarmed and lockstep active |
| Launcher SIGTERM cleanup | **Passed**, only the owned PX4 child exited; interruption recorded |
| Read-only PX4 console client | **Passed**, `px4-commander --instance 0 status` |
| Draft hygiene and relative-link audit | **Passed**, 28 allowlisted text files |

The unit suite checks frame transforms, signs and units, motor output mapping,
individual rotor wrenches, exact ideal hover, sensor noise reproducibility,
TCP framing/disconnects, stale actuator rejection, CLI/model guards, parameter
environment isolation, stale demo position feedback, and observed demo
completion rather than ACK-only success. A mocked lockstep-timeout test verifies
that no extra physics step occurs without a fresh actuator reply.

## Latest full-flight result

The [machine-readable result](validation-result.json) contains only generic
simulation data and versions, with no private host paths or real flight logs.

- PX4 commit matched the pin; tracked source was clean.
- Simulation duration: **44.904 s**, 11,226 bridge cycles.
- Bootstrap cycles before an actuator response: 18; lockstep then observed.
- Maximum root-origin height: **2.104 m** above the world floor.
- Maximum horizontal distance from origin: **1.515 m**.
- Five position targets completed; landing and disarming observed.
- Mode, arm and land command acknowledgments were accepted.

The 2 m climb is relative to captured estimated ground position. The body origin
rests about 0.085 m above the floor, and estimator/control transients mean the
maximum physical height is not exactly 2.000 m. Horizontal maximum includes
transient overshoot around a square with diagonal length about 1.414 m. These
figures demonstrate a working closed-loop connection, not a tracking-accuracy
benchmark.

The first full run completed in 44.876 s, illustrating that a fixed noise seed
does not make the whole asynchronous PX4/telemetry startup bitwise deterministic.
There is a pinned-PX4 ground-truth acceleration logging scale caveat documented
in [architecture](architecture.md#messages-and-units); do not use that field as
an uncorrected SI acceleration benchmark.

## Reproduce

From the bridge checkout with its venv active and a separate pinned PX4 build:

```bash
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m build
px4-mujoco run --px4 /absolute/path/to/PX4-Autopilot --headless --duration 15
px4-mujoco run --px4 /absolute/path/to/PX4-Autopilot --headless --demo
python scripts/check_release.py
```

Each live launch writes a new result/log directory. Do not overwrite a previous
test result to make a newer run appear successful. When testing an installed
wheel, run from outside this source checkout and confirm the loaded model path
belongs to the installed package.

## Not yet validated

- Interactive viewer operation and QGC UI connection/commands. A host QGC process
  was present, but it was not driven or accepted as an integration test.
- Fresh Ubuntu installation or the documented dependency-installer procedure.
- Ubuntu 24.04, Windows/WSL2, macOS, containers or ARM hosts.
- Multiple concurrent instances, external offboard clients or bridge-only launch
  orchestration beyond unit-level transport tests.
- Other PX4 commits, custom airframes, models with more than four motors, motor
  lag, realistic aerodynamics, sensor biases, latency/loss or high-speed pacing.
- Any physical device, real flight, HITL or safety-critical application.
- GitHub Actions execution; the local workflow is prepared but unpublished.

Keep these boundaries visible in a public release rather than extending the
support claim from a successful build or one example flight.
