# Initial publication checklist

Intended destination: **Holiday-66/px4-mujoco-bridge**.
The maintainer confirmed the name, selected **BSD-3-Clause**, and identified the
implementation as an independent personal project. Technical validation passed;
publication was explicitly approved on 2026-10-14. Remote creation and the first
push are still pending; local approval does not mean an upload has occurred.

## Required before publication

- [x] Record the maintainer's statement that this was independently developed,
  not work for a university or company. This is not an independent legal audit.
- [x] Select BSD-3-Clause for the bridge's own code.
- [x] Prepare standard LICENSE text, package license metadata and updated notices.
- [x] Replace the LICENSE placeholder with the selected notice: `Copyright (c) 2026, HolidayHan`.
- [x] Review installed dependency notices; distinguish pymavlink's LGPL library
  from its generated-code exception. No dependencies are vendored in the wheel.
- [x] Review every tracked file and the complete standalone Git history.
- [x] Check for credentials, personal paths, confidential source, CAD, logs,
  videos, firmware binaries, upstream checkout or inherited project history.
  The maintainer explicitly requested preserving existing commit attribution.
- [x] Reproduce installation/build and installed-wheel smoke/full flight in
  fresh Ubuntu 22.04 container userspace. A fresh desktop/VM is not claimed.
- [x] Verify rendered MuJoCo flight and QGC connection/parameter display.
  The exact existing QGC build could not be established; no manual QGC flight
  command or version-specific support claim is made.
- [x] Re-run 40 unit tests, wheel installation and the pinned PX4 smoke/full demo
  on the host and in the clean container; inspect packaged files and notices.
- [x] Run `python scripts/check_release.py --ready` and the scoped manual
  source/history/dependency review. Ownership relies on the maintainer's
  declaration; this is not independent legal or comprehensive security clearance.
- [x] Record final publication approval after validation in NOTICE.
- [x] Prepare public-facing clone/setup instructions and repository links.
- [x] Configure the local `origin` for `Holiday-66/px4-mujoco-bridge` using the
  verified existing GitHub SSH identity.
- [ ] Create the agreed empty public GitHub repository.
- [ ] Push only this standalone repository's `main` branch and verify its SHA.
- [ ] Enable private vulnerability reporting in repository settings.
- [ ] Verify GitHub Actions for Python 3.10 and 3.12 after the first push.

Technical validation passed on 2026-10-14; see the [record](docs/validation.md).
The local-draft and pending-publication markers have now been resolved with the
maintainer's approval. GitHub repository state, push completion, and remote CI
must be verified separately. No package, container, or firmware upload is planned.

## Included in the source repository

- Standalone src-layout Python package and original generic quadrotor model.
- Stock-PX4 launcher, loopback MAVLink transport, isolated run data, opt-in demo.
- Setup, QGC, architecture, model, troubleshooting and validation documentation.
- Headless unit tests and a non-publishing CI workflow.
- Local-only release audit; no GitHub credentials, deploy key or publishing job.

Any local Git repository must have a fresh history; never copy an unrelated
project's `.git` directory or expose a private repository by changing visibility.
The prepared LICENSE uses the maintainer-selected name `HolidayHan`.
The completed notice and selected SPDX identifier do not themselves clear publication.
