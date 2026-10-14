# Ownership, licensing and third-party components

**Selected release license: BSD-3-Clause.** The maintainer approved this license
choice on 2026-10-14. The standard text is prepared in [LICENSE](LICENSE), and the
package metadata declares `BSD-3-Clause`. The maintainer selected `HolidayHan`
as the public copyright name, giving the notice `Copyright (c) 2026, HolidayHan`.
The placeholder has been replaced. This local draft has not been cleared for
public distribution.

Ownership confirmation: pending.
Publication approval: pending.

Confirm release authority and record publication authorization before publishing.
Selecting a license and public copyright name does not by itself settle
university, employer, collaborator or funding obligations. The two approval
markers above must only change to `confirmed` after explicit confirmation; the
release check verifies those markers but cannot establish legal ownership.

The repository is a standalone community-bridge draft. Its example MJCF uses
new primitive geometry. No upstream firmware source, binary distribution,
third-party mesh or CAD asset is vendored here. PX4 is built from its own
upstream checkout; Python packages are installed separately.

Dependencies and optional external applications retain their own terms. Review
the exact versions and any distribution obligations before release; do not
assume they all use the same license:

- [PX4 license at the pinned release](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/LICENSE)
- [MuJoCo 3.4.0 license](https://github.com/google-deepmind/mujoco/blob/3.4.0/LICENSE)
- [NumPy 2.2.6 license](https://github.com/numpy/numpy/blob/v2.2.6/LICENSE.txt)
- [pymavlink COPYING](https://github.com/ArduPilot/pymavlink/blob/master/COPYING),
  including library terms and the generated-code exception; inspect the installed
  2.4.49 distribution's notices for the release review
- [MAVLink protocol repository](https://github.com/mavlink/mavlink)
- [QGroundControl licensing](https://github.com/mavlink/qgroundcontrol/blob/master/.github/COPYING.md)

These links are attribution/review pointers, not a legal opinion that a proposed
distribution is cleared. Preserve required notices if third-party code or assets
are ever added. No affiliation or endorsement by these upstream projects is
claimed.
