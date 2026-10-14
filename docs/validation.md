# Validation record

Local checks performed on **2026-10-14**. This records observed software behavior,
not hardware-flight readiness, calibrated plant accuracy or general deployment
certification. Public source publication and GitHub CI are recorded separately
below; no package registry upload has occurred.

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
had development dependencies, including optional simulator libraries. A separate
clean-userspace build was subsequently performed for release validation, below.

## Checks and outcomes

| Check | Result |
| --- | --- |
| Headless unit/regression suite | **40 passed**, repeated during release review |
| Stock PX4 SITL build | **Passed** |
| Unarmed 15 s lockstep run | **Passed**, PX4 reported ready for takeoff |
| Full opt-in flight demo | **Passed twice**, all five targets, landed and disarmed |
| Wheel/source-distribution build | **Passed** |
| Wheel installation into a separate fresh venv | **Passed**, bundled MJCF loads outside the source tree |
| Installed-wheel 15 s stock-PX4 run | **Passed**, unarmed and lockstep active |
| Fresh installed-wheel full flight | **Passed**, 44.128 s, all five targets, landed and disarmed, launched outside the source checkout |
| Archive contents and dependency consistency | **Passed**, 16 wheel / 38 sdist text members; correct BSD notice, source/model byte equality, no vendored dependencies; isolated `pip check` passed |
| Launcher SIGTERM cleanup | **Passed**, only the owned PX4 child exited; interruption recorded |
| Read-only PX4 console client | **Passed**, `px4-commander --instance 0 status` |
| Draft hygiene and relative-link audit | **Passed**, 30 allowlisted text files |
| Initial standalone Git history | **Passed**, the initial two commits and all 37 unique blobs reviewed with the file allowlist and limited credential/path patterns; publication-preparation changes are checked separately before push |
| Interactive MuJoCo flight | **Passed**, rendered flight completed all five targets, landed and disarmed |
| Existing QGC connection | **Passed**, PX4 1.17.0 parameter summary displayed; valid GCS heartbeat and received messages on the loopback UDP link |
| Fresh Ubuntu 22.04 userspace | **Passed**, documented installer, 1,109-step stock build, 40 tests, package build, installed-wheel smoke and full flight |

The unit suite checks frame transforms, signs and units, motor output mapping,
individual rotor wrenches, exact ideal hover, sensor noise reproducibility,
TCP framing/disconnects, stale actuator rejection, CLI/model guards, parameter
environment isolation, stale demo position feedback, and observed demo
completion rather than ACK-only success. A mocked lockstep-timeout test verifies
that no extra physics step occurs without a fresh actuator reply.

The release checks also cover license placeholders and missing authorization
markers. The history review found no private CAD, flight logs, firmware binaries,
credentials matching the scanned patterns, or inherited research-project
history. The maintainer explicitly chose to retain the existing commit author
attribution/email. This is a scoped review, not proof that every possible secret
pattern or legal issue has been ruled out. See [dependency notices](../NOTICE.md).
Run dependency checks with `PYTHONPATH` unset too: this host's inherited ROS path
made an initial `pip check` see unrelated ROS packages. The isolated repeat and
new wheel environment both passed without adding ROS dependencies to the bridge.

## Interactive check

On the native host, `run --demo --speed 0.5` opened the MuJoCo viewer and completed
in **44.660 simulated seconds** (11,165 cycles), with five targets and observed
landing/disarming. Maximum root height was 2.101 m; maximum horizontal distance
was 1.516 m. The lower pacing speed allowed observation; no physics/model change
was made. Targeted screenshots confirmed a rendered airborne quadrotor and QGC's
connected PX4 parameter summary; these remain local, not release assets.

PX4's GCS link reported a valid heartbeat from system 255/component 190 on
UDP 18570 → 14550, zero reported RX loss at the sampled instant, and localhost
as its peer. The demo used its separate system-250 offboard link. QGC displayed
an RC-setup warning for this deliberately receiver-free configuration; it did
not prevent the demo's normal arming checks or flight. The exact QGC build and
manual flight-command UI were not validated. No QGC configuration was changed.

## Clean Ubuntu userspace build

An official `ubuntu:22.04` container was pulled at image digest
`sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401`.
It used a separate network namespace, no host display/devices/credentials, a
4-CPU limit and 10 GiB memory limit. It shared the host kernel, so this is not a
fresh physical machine or independent-kernel VM test.

After installing basic Python/venv, Git, CA certificates, sudo, distribution
metadata and viewer runtime libraries, the documented upstream installer ran
with `--no-nuttx --no-sim-tools`. Stock PX4 then built successfully in **1,109
steps**, using `make -j4 px4_sitl_default` with the build interpreter explicitly
selected. No Gazebo installation, source patch or host build artifact was used.

| Clean-build component | Observed version |
| --- | --- |
| Ubuntu userspace / architecture | 22.04 / x86-64 |
| Build Python | 3.10.12 |
| GCC / CMake | 11.4.0 / 3.22.1 |
| Build venv setuptools / empy | 59.6.0 / 3.3.4 |
| Build venv pymavlink | 2.4.50, resolved from upstream PX4 build requirements |
| Bridge runtime pymavlink constraint | 2.4.49, separate from the build venv |

The public upstream source-object cache was reused for fresh Git checkouts and
pinned submodules; package downloads and builds ran in the clean container.
An initial redundant source download was canceled and retried from that cache.
No source-fetch timing or all-network clone benchmark is claimed. Build logs and
resolved environment inventories are retained locally, not distributed as
third-party binaries in this repository.

With a separate bridge environment, **all 40 tests passed** (pytest 8.4.2), the
30-file hygiene check passed, and both wheel and source distribution built.
That wheel was installed into a third, new venv and launched from `/tmp`, outside
the source checkout. Runtime versions were MuJoCo 3.4.0, NumPy 2.2.6 and
pymavlink 2.4.49. Both checks passed:

- **Unarmed smoke:** 15.000 simulated seconds, 3,750 cycles, lockstep observed.
- **Full demo:** 44.428 simulated seconds, 11,107 cycles, five targets completed,
  landing and disarming observed; maximum root height 2.105 m and horizontal
  distance 1.523 m.

PX4's tracked checkout remained clean. The overall validation process exited
with status 0. No host QGC, real flight controller or host simulator was involved
in these container flights. This verifies the documented software setup on this
userspace baseline, not flight-controller hardware or container GUI support.

## Recorded host headless-flight result

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

## Publication and GitHub CI

The standalone source was published on **2026-10-14** to
[Holiday-66/px4-mujoco-bridge](https://github.com/Holiday-66/px4-mujoco-bridge).
The initial remote `main` matched the locally validated commit
`398ad364c36aa5340b448669be9e4aaad90bfcbd`. Before that push, all three standalone
commits and 48 unique reachable blobs were checked with the scoped source/history
audit. No private research-project history or assets were uploaded.

The [initial GitHub Actions run](https://github.com/Holiday-66/px4-mujoco-bridge/actions/runs/38537153484)
completed successfully for **Python 3.10 and 3.12** on Ubuntu 22.04. Both jobs ran
the headless unit suite, ready-to-publish source check, wheel/source-distribution
build and installed-wheel model/CLI checks. This CI does not build PX4 or run the
closed-loop flight demo; those were separate local and clean-container checks
described above.

The initial run reported Node.js 20 deprecation warnings for the old action
versions. The workflow now pins the official Node.js 24-based v7 releases of
`actions/checkout` and `actions/setup-python` to full commit hashes, retaining
read-only repository permissions and disabling checkout credential persistence.
See [Actions](https://github.com/Holiday-66/px4-mujoco-bridge/actions) for the
results of subsequent commits. No GitHub Release, package registry, container or
firmware binary was published.

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

- Exact host QGC build/version, manual QGC flight commands, joystick or RC input.
- A fresh Ubuntu desktop/VM, QGC installation on it, or container-to-host
  display/QGC networking; only clean headless container userspace was tested.
- Ubuntu 24.04, Windows/WSL2, macOS or ARM hosts.
- Multiple concurrent instances, external offboard clients or bridge-only launch
  orchestration beyond unit-level transport tests.
- Other PX4 commits, custom airframes, models with more than four motors, motor
  lag, realistic aerodynamics, sensor biases, latency/loss or high-speed pacing.
- Any physical device, real flight, HITL or safety-critical application.

Keep these boundaries visible in a public release rather than extending the
support claim from a successful build or one example flight.
