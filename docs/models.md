# The quadrotor model and how to change it

The included [quadrotor.xml](../src/px4_mujoco_bridge/models/quadrotor.xml) uses
primitive geometry created for this example. It has no external meshes, textures,
CAD dependencies or firmware-specific proprietary data.

## Physical values and motor order

| Property | Value |
| --- | --- |
| Mass | 1.5 kg |
| Body principal inertia | 0.03, 0.03, 0.05 kg·m² |
| Rotor XY lever arms | ±0.20 m |
| Per-rotor maximum thrust | 10 N |
| Reaction torque / thrust magnitude | 0.02 m |
| Physics timestep | 0.002 s, RK4 |
| Gravity | `(0, 0, -9.80665)` m/s² in NWU |

All rotors thrust along local FLU +Z. Index order is the order of the MJCF
`<actuator>` entries, **not** the order of visually sorted rotor positions:

| HIL slot | Motor / site | FLU position m | FRD position m | FLU yaw torque per N | PX4 `CA_ROTORi_KM` |
| --- | --- | --- | --- | --- | --- |
| 0 | 1 / `rotor_1` | `(0.2, -0.2, 0)` | `(0.2, 0.2, 0)` | −0.02 N·m | +0.02 |
| 1 | 2 / `rotor_2` | `(-0.2, 0.2, 0)` | `(-0.2, -0.2, 0)` | −0.02 N·m | +0.02 |
| 2 | 3 / `rotor_3` | `(0.2, 0.2, 0)` | `(0.2, -0.2, 0)` | +0.02 N·m | −0.02 |
| 3 | 4 / `rotor_4` | `(-0.2, -0.2, 0)` | `(-0.2, 0.2, 0)` | +0.02 N·m | −0.02 |

The launcher derives PX4 `CA_ROTOR*` lever arms and signed moment coefficients
from these sites and gears. It maps output functions Motor1–Motor4 to the first
four HIL slots and clears unused output functions. Airframe 10016 provides the
stock multicopter startup, but its default geometry is overridden to match
**this** quadrotor. No manual mixer edit is required.

## Appearance-only edits

Make a copy of the XML before experimenting:

```bash
mkdir -p models
cp src/px4_mujoco_bridge/models/quadrotor.xml models/my_quadrotor.xml
px4-mujoco run --px4 /absolute/path/to/PX4-Autopilot --model models/my_quadrotor.xml
```

Change colors, lights, camera settings or add massless decorative geoms. Keep
the explicit inertial unchanged for an appearance-only edit. For decorative
geometry that should not alter contact behavior, use `mass="0" contype="0"
conaffinity="0"`. The current arms and fuselage do collide; changing their shape
changes contact behavior even if mass is unchanged. Propeller discs are visual
only; their appearance does not generate forces or model blade aerodynamics.

Use relative mesh paths if adding your own redistributable assets. Include their
notices and verify the model still opens from another directory. Never reference
personal absolute CAD paths or upload assets you do not have permission to share.

## Supported physical model contract

This initial adapter intentionally supports a narrow class of models:

- A body named `vehicle`, with the model's only free joint (7 qpos / 6 qvel).
- Complete mass/inertia on that body; its center of mass at the root origin.
- Between 4 and 12 identical, non-reversible, fixed-axis thrusters. Only the
  included four-rotor model has been flight-tested in this package.
- Direct site motors with unit force gain, no actuator dynamics/bias or separate
  force limiting, `ctrlrange="0 T_max"`, and
  `gear="0 0 1 0 0 signed_reaction_coefficient"`.
- Motor sites directly on `vehicle`, aligned to its FLU axes.
- Three-axis MuJoCo `accelerometer` and `gyro` sensors named `imu_accelerometer`
  and `imu_gyro`, on root-aligned sites at the vehicle origin.
- NWU gravity `(0, 0, -9.80665)`; a physics timestep dividing 0.004 s exactly.
- Hover thrust fraction `mass × g / sum(T_max)` within the pinned PX4 parameter
  range 0.1–0.8. More thrust margin is not a proof of controller suitability.

Invalid basic configurations are rejected rather than silently reinterpreted.
Acceptance is not proof of controllability, full allocation rank, stable tuning,
accurate contacts or realistic sensor behavior. Changes to mass, inertia or arm
length can need PX4 tuning even when geometry is generated correctly.

Articulated aircraft, movable rotor axes, servo outputs, nonuniform thrust limits,
motor lag and flexible mechanisms require extensions to the adapter and PX4
allocation. Do not simply drop an arbitrary MJCF into this CLI and expect it to
fly.

## Validation after a change

1. Print `px4-mujoco parameters --model models/my_quadrotor.xml`; check signs,
   lever arms, motor order and hover thrust against your intended design.
2. Run unit tests. Extend the individual-rotor wrench and hover tests to cover
   your model; do not rely on the included model's results.
3. Run an unarmed headless session and inspect estimator health and lockstep.
4. Run a supervised **SITL-only** demo; inspect attitude, height, landing and logs.
5. Record changed values, PX4 commit and validation results before sharing.

Model XML semantics are documented in the
[MuJoCo XML reference](https://mujoco.readthedocs.io/en/3.4.0/XMLreference.html).
