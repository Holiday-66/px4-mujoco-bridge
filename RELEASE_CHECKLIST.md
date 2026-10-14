# Release checklist — local preparation only

Intended destination: **Holiday-66/px4-mujoco-bridge**.
The maintainer confirmed the name but has **not** authorized publication or
confirmed ownership/licensing. Do not create the public repository, push this
draft, publish a package, or upload its artifacts yet.

## Required before publication

- [ ] Confirm who owns the implementation and who can authorize its release.
- [ ] Resolve any employer, university, collaborator or funding obligations.
- [ ] Confirm the release license and applicable copyright holders/year.
- [ ] Review dependency licenses and preserve any required notices.
- [ ] Add the approved LICENSE and matching package metadata; update NOTICE.
- [ ] Review every tracked file and the complete standalone Git history.
- [ ] Confirm no credentials, personal paths, confidential source, CAD, logs,
  videos, firmware binaries, upstream checkout or inherited project history.
- [ ] Reproduce installation on a clean supported Ubuntu machine.
- [ ] Verify interactive MuJoCo viewing and QGC connection; record QGC version.
- [ ] Re-run unit tests, wheel installation and the pinned PX4 smoke/full demo.
- [ ] Run `python scripts/check_release.py --ready`; perform a separate manual
  rights/security review (the script cannot determine ownership).
- [ ] Obtain explicit approval to publish the reviewed content.
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
An absent LICENSE is intentional during preparation, not an open-source license.
