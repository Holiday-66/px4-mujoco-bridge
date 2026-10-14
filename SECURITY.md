# Security and safety scope

This package is for local software-in-the-loop simulation. It is not a flight
safety system, real-time certification, HITL interface, or hardware validation.

The bridge binds its simulator TCP server to `127.0.0.1`. The optional demo binds
its offboard UDP endpoint to loopback and is only available with the combined
launcher. It commands the locally launched PX4 instance and never opens serial
ports or flashes devices. Keep real flight controllers disconnected and do not
forward these links to a vehicle.

MAVLink/TCP and the local API messages are not authenticated or encrypted by this
package. Loopback is an exposure limit, not protection against other local
processes. PX4 itself owns its telemetry sockets. Do not expose them through port
forwarding, enable network broadcasts, or run untrusted local clients. Separate
instances by their documented IDs and ports.

Only open trusted MJCF files and Python environments. Model files may reference
external assets and can consume significant resources. Validate models before
running them. The source-commit guard is a compatibility check, not a binary
signature or supply-chain attestation.

The default launch does not arm. `--demo` is an explicit opt-in that can arm the
simulated vehicle. Interrupting or failing the demo stops the owned simulation;
it is not an emergency landing procedure for real hardware. Cleanup targets
only the child process group created by the launcher.

## Reporting a vulnerability

Use **Security → Advisories → Report a vulnerability** on the
[repository's Security page](https://github.com/Holiday-66/px4-mujoco-bridge/security/advisories)
when private vulnerability reporting is available. Do not disclose exploit
details, credentials, or private assets in a public issue.

If the private-report button is not available, open a minimal issue requesting a
private contact channel without including the vulnerability details. Maintainers
should enable private vulnerability reporting in repository settings; its
activation is tracked in [the release checklist](RELEASE_CHECKLIST.md).
