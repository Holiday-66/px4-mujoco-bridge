# Release checklist — local preparation only

Intended destination: **Holiday-66/px4-mujoco-bridge**.
The maintainer confirmed the name and selected **BSD-3-Clause**. Ownership and
authority to release the code remain unconfirmed. Do not create the public
repository, push this draft, publish a package, or upload its artifacts yet.

## Required before publication

- [ ] Confirm who owns the implementation and who can authorize its release.
- [ ] Resolve any employer, university, collaborator or funding obligations.
- [x] Select BSD-3-Clause for the bridge's own code.
- [x] Prepare standard LICENSE text, package license metadata and updated notices.
- [x] Replace the LICENSE placeholder with the selected notice: `Copyright (c) 2026, HolidayHan`.
- [ ] Review dependency licenses and preserve any required notices.
- [ ] Review every tracked file and the complete standalone Git history.
- [ ] Confirm no credentials, personal paths, confidential source, CAD, logs,
  videos, firmware binaries, upstream checkout or inherited project history.
- [ ] Reproduce installation on a clean supported Ubuntu machine.
- [ ] Verify interactive MuJoCo viewing and QGC connection; record QGC version.
- [ ] Re-run unit tests, wheel installation and the pinned PX4 smoke/full demo.
- [ ] Run `python scripts/check_release.py --ready`; perform a separate manual
  rights/security review (the script cannot determine ownership).
- [ ] Obtain explicit release authority and publication approval; update the
  corresponding confirmation markers in NOTICE only after that confirmation.
- [ ] Only then create the agreed GitHub repository and attach its remote.
- [ ] Configure a private security-reporting route, verify CI, and update docs
  from draft language to actual release/clone instructions.

## Prepared in this draft

- Standalone src-layout Python package and original generic quadrotor model.
- Stock-PX4 launcher, loopback MAVLink transport, isolated run data, opt-in demo.
- Setup, QGC, architecture, model, troubleshooting and validation documentation.
- Headless unit tests and a non-publishing CI workflow.
- Local-only release audit; no GitHub credentials, deploy key or publishing job.

Any local Git repository must have a fresh history; never copy an unrelated
project's `.git` directory or expose a private repository by changing visibility.
The prepared LICENSE uses the maintainer-selected name `HolidayHan`.
The completed notice and selected SPDX identifier do not themselves clear publication.
