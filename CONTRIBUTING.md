# Contributing and local development

Bug reports, documentation improvements and small, tested changes are welcome.
Use the [issue tracker](https://github.com/Holiday-66/px4-mujoco-bridge/issues)
for non-sensitive reports, and discuss substantial interface/model changes
before implementing them. Read the [license and notices](NOTICE.md); only submit
work you have authority to share. Security concerns follow [SECURITY.md](SECURITY.md).

## Development checks

Use a dedicated venv and the documented dependency baseline:

```bash
python -m pip install -c requirements-tested.txt -e '.[test]'
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m build
python scripts/check_release.py
python scripts/check_release.py --ready
```

Tests run headlessly without PX4 or a GPU, but the TCP tests need loopback
sockets. They cover frame signs, per-rotor wrenches, hover physics, synthetic
sensors, TCP parsing/stale messages, disarm gating, startup parameter isolation,
model validation, lockstep timeout behavior and demo completion checks.

For transport, sensor, model or flight-control-interface changes, also run:

```bash
px4-mujoco run --px4 /absolute/path/to/stock/PX4-Autopilot --headless --duration 15
px4-mujoco run --px4 /absolute/path/to/stock/PX4-Autopilot --headless --demo
```

Review both results and PX4 logs. Add a dated entry to the validation document
only for checks actually performed. Never describe unit tests as hardware-flight
validation or claim a successful flight from a command acknowledgment alone.

## Change boundaries

Keep simulator transport, plant modeling and demonstration commands separate.
Document coordinate frames and units at interfaces. Extend tests before changing
the motor curve, allocator mapping, timing or supported model class. Avoid
silently relaxing the version guard, disarm gate, loopback binding or timeouts.
Do not introduce global process-kill commands, automatic force arming, arbitrary
remote targets or downloaded executable helpers into the quick start.

The [GitHub Actions workflow](https://github.com/Holiday-66/px4-mujoco-bridge/actions)
installs the pinned runtime dependencies, runs headless unit tests and
builds/checks a wheel. It deliberately does not deploy packages, create releases,
upload flight logs or require credentials. Full PX4 flight testing remains a
separate check; the local validation record does not imply that remote CI passed.

Before contributing assets, confirm ownership and redistribution permission.
Keep runtime logs, personal paths, environment secrets, binary firmware, upstream
PX4 source, and unrelated project files out of commits.
