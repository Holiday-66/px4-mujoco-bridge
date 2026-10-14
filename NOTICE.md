# Ownership, licensing and third-party components

**Selected release license: BSD-3-Clause.** The maintainer approved this license
choice on 2026-10-14. The standard text is prepared in [LICENSE](LICENSE), and the
package metadata declares `BSD-3-Clause`. The maintainer selected `HolidayHan`
as the public copyright name, giving the notice `Copyright (c) 2026, HolidayHan`.
The placeholder has been replaced. The maintainer describes this as an
independently developed personal project, not work performed for a university or
company. Ownership confirmation below records that statement, not an independent
legal determination. Technical validation passed, and the maintainer approved
publishing this standalone source repository on 2026-10-14.

Ownership confirmation: confirmed.
Publication approval: confirmed.

Selecting a license and public copyright name does not by itself settle
third-party obligations. The release check verifies recorded markers but cannot
establish legal ownership. Approval covers the standalone community bridge, not
unrelated research code, assets, firmware binaries or package/container uploads.

The repository is a standalone community bridge. Its example MJCF uses
new primitive geometry. No upstream firmware source, binary distribution,
third-party mesh or CAD asset is vendored here. PX4 is built from its own
upstream checkout; Python packages are installed separately.

## Dependency review (2026-10-14)

The installed distributions' license files and package metadata were inspected.
The bridge wheel contains only its own Python code, original MJCF and package
metadata/notices: dependencies are installed separately, not relicensed or
vendored into this repository.

| Component reviewed | Terms / scope |
| --- | --- |
| Stock PX4 v1.17.0 at the pinned commit | BSD-3-Clause for PX4; its submodules retain separate notices. Source and firmware binaries are not distributed here. |
| MuJoCo 3.4.0 | Apache-2.0, with `LICENSES_THIRD_PARTY.md` for bundled components. |
| NumPy 2.2.6 | BSD-3-Clause for NumPy; its wheel's `LICENSE.txt` also covers bundled libraries, including OpenBLAS and runtime components. |
| pymavlink 2.4.49 | LGPLv3 library/generator; individual library headers such as `mavutil.py` specify LGPL version 3 or later. `COPYING` grants an MIT exception for generated code only. The demo imports the library, so this dependency is **not wholly MIT**. |
| QGroundControl (optional, installed separately) | Its own upstream licensing; no QGC executable is included. The exact build of the existing host installation was not established. |

Runtime transitive distributions were inventoried as well: absl-py 2.5.1,
glfw 2.10.2, PyOpenGL 3.1.10, etils 1.13.0, fsspec 2026.9.0,
importlib_resources 7.1.0, zipp 4.1.1, typing_extensions 4.16.0, lxml 6.1.3,
and fastcrc 0.5.0. Their package-level licenses include Apache-2.0, MIT,
BSD-style and PSF-2.0 terms; native/bundled components can have additional
notices. This inventory is not a complete transitive lockfile or a blanket
relicensing statement. Future installations can resolve different versions.

Preserve upstream notices and applicable source/relinking rights when
redistributing dependency binaries or modified dependencies. A bundled
executable, container image or firmware release needs its own distribution
review; none is part of this source-only repository release.

Primary-source license pointers:

- [PX4 license at the pinned release](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/LICENSE)
- [MuJoCo 3.4.0 license](https://github.com/google-deepmind/mujoco/blob/3.4.0/LICENSE)
- [NumPy 2.2.6 license](https://github.com/numpy/numpy/blob/v2.2.6/LICENSE.txt)
- [pymavlink 2.4.49 COPYING](https://github.com/ArduPilot/pymavlink/blob/v2.4.49/COPYING),
  including library terms and the generated-code exception
- [MAVLink protocol repository](https://github.com/mavlink/mavlink)
- [QGroundControl licensing](https://github.com/mavlink/qgroundcontrol/blob/master/.github/COPYING.md)

These links are attribution/review pointers, not a legal opinion that a proposed
distribution is cleared. Preserve required notices if third-party code or assets
are ever added. No affiliation or endorsement by these upstream projects is
claimed.
