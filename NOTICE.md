# Ownership, licensing and third-party components

**Release license pending.** This local draft has not been authorized for public
distribution. No BSD, MIT or other license is granted by this document.
Ownership and permission to publish the bridge implementation must be confirmed
before adding a LICENSE, license metadata or an open-source badge.

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
