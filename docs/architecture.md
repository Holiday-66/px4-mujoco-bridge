# Architecture and protocol

## Responsibility boundaries

PX4 is the autopilot: estimator, position/attitude/rate loops, control allocator,
arming and mode logic. MuJoCo integrates a rigid-body plant with contacts. Python
converts state to simulated sensor messages and motor signals to physical forces.
The optional demo is a separate MAVLink offboard client inside the launcher; it
does not replace PX4's flight controller.

| File | Responsibility |
| --- | --- |
| `cli.py` | Version guard, owned PX4 process, timing loop, viewer and run artifacts |
| `transport.py` | Loopback TCP server, MAVLink framing, sensor transmission and actuator reception |
| `sensors.py` | IMU reads, approximate magnetic field, barometer and local-tangent GPS |
| `frames.py` | NWU/FLU ↔ NED/FRD transformations |
| `model.py` | MJCF contract, motor force curve and corresponding PX4 parameters |
| `demo.py` | Opt-in position-setpoint demonstration and observed completion checks |

## Startup and lockstep

The combined launcher starts the TCP server **before** PX4. It selects stock
airframe `10016_none_iris`, then overrides rotor geometry, output functions and
thrust parameters from MJCF through `PX4_PARAM_*` environment variables.
`PX4_SIMULATOR=mujoco`, `PX4_SIM_MODEL=none_iris` and `SIM_GZ_EN=0` select stock
`simulator_mavlink`; they do not require a new upstream simulator target.

The bridge accepts one connection and waits for PX4's simulator heartbeat before
sending sensors. A bounded bootstrap lets PX4 initialize using sensor updates
while missing actuator output means zero motor force. Once PX4 reports the
lockstep flag, each cycle is:

1. Read simulated state at time `t` and transmit sensors timestamped `t`.
2. Wait for an actuator message from the connected PX4 system with a timestamp
   at least as recent as that sensor sample.
3. Apply disarm gating and the motor thrust curve.
4. Advance MuJoCo by exactly 4 ms (two 2 ms steps for the included model).
5. Update the viewer, optional demo and trace, then pace against wall time.

A fresh actuator reply is required after lockstep begins. On a two-second
wall-clock actuator timeout, the bridge exits **without advancing that physics
cycle**. Disconnects fail visibly. TCP buffering/fragmentation is handled by the
MAVLink parser; message boundaries need not match socket reads.

Simulation time comes only from MuJoCo, not wall-clock timestamps. The first HIL
time is `1 µs` rather than zero. GPS uses a fixed Unix epoch plus simulation time
to provide GNSS time. That epoch can make PX4's ULog dates look historical.
Wall pacing and estimator initialization are not guaranteed bitwise deterministic
across hosts even though the synthetic noise seed is fixed.

## Messages and units

| Message | Bridge direction | Nominal rate | Main units |
| --- | --- | --- | --- |
| `HEARTBEAT` | Both directions during connection; bridge → PX4 thereafter | 1 Hz bridge heartbeat | System identity/liveness |
| `HIL_SENSOR` | Bridge → PX4 | 250 Hz | FRD specific force m/s², gyro rad/s, magnetic field gauss, pressure hPa |
| `HIL_GPS` | Bridge → PX4 | 10 Hz | Degrees × 1e7, altitude mm AMSL, NED velocity cm/s |
| `HIL_STATE_QUATERNION` | Bridge → PX4 | 50 Hz | Scalar-first body-to-NED quaternion, ground-truth pose/velocity |
| `HIL_ACTUATOR_CONTROLS` | PX4 → bridge | Lockstep response | 16 normalized motor/actuator slots, armed mode bit, PX4 lockstep flag |

Scheduling occurs on the 4 ms grid; lower-rate sends can be quantized by one
tick. The differential-pressure update bit stays clear because no pitot sensor
is modeled. Pressure altitude is calculated from the same noisy pressure value.
Ground truth is not an excuse to bypass sensor/frame correctness: the demo uses
PX4's estimated `LOCAL_POSITION_NED` feedback over its API link.
Wire definitions are in the [MAVLink common message specification](https://mavlink.io/en/messages/common.html).

Known upstream logging caveat: this bridge sends HIL-state acceleration in the
specified milli-g units, but the pinned PX4
[ground-truth receiver](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/simulation/simulator_mavlink/SimulatorMavlink.cpp)
divides those fields by 1000 without multiplying by gravity before publishing
local-position ground-truth acceleration. Do not treat that logged acceleration
as SI m/s² without correcting its scale. This does not change the separate
`HIL_SENSOR` accelerometer stream, which is already in m/s² and feeds estimation.

## Frames: keep world and body transformations separate

| Quantity | MuJoCo convention in this example | PX4/MAVLink convention |
| --- | --- | --- |
| World position/velocity | North, West, Up (NWU) | North, East, Down (NED) |
| Body vectors | Forward, Left, Up (FLU) | Forward, Right, Down (FRD) |
| Quaternion order | `w, x, y, z` | `w, x, y, z` for HIL state |

With `D = diag(1, -1, -1)`:

```text
p_NED = D p_NWU
v_FRD = D v_FLU
R_NED_from_FRD = D R_NWU_from_FLU D
```

Changing position signs alone is insufficient. Body rates, accelerometer,
magnetometer, attitude, rotor lever arms and reaction moments must agree too.
At rest, this model's FRD accelerometer reads approximately `(0, 0, -9.80665)`
m/s²: an accelerometer reports specific force, not gravitational acceleration.

The default geodetic origin is the public SITL-style reference
`47.397742° N, 8.545594° E, 488 m AMSL`, not a flight-test location. GPS is a
small-area tangent-plane approximation; it is not a global navigation model.
The magnetic field is constant and approximate. No sensor biases, realistic
GPS outages, airspeed, wind, battery drain or communication impairments are
included. Small seeded magnetic/barometric noise avoids bit-identical stuck
streams; it is not a calibrated sensor-noise characterization.

## Motor outputs are not thrust commands in newtons

For this PX4 parameterization, `THR_MDL_FAC=1` makes the PX4 output stage map
normalized desired thrust through a square root. The bridge applies the paired
plant curve:

```text
u_i = clamp(finite(HIL_controls[i]), 0, 1)
T_i = T_max,i × u_i²               when armed
T_i = 0                           when disarmed
```

NaN and both infinities produce zero signal; a positive infinity never becomes
full thrust. The first `model.nu` of the 16 slots are used. MJCF control values
are newtons, and each site's gear also applies its signed reaction torque.

For the example, `MPC_THR_HOVER = 1.5 × 9.80665 / 40 ≈ 0.36775`, while the
balanced motor signal is about `sqrt(0.36775) ≈ 0.6064`. Confusing these two
values causes poor hover/altitude behavior. The relevant upstream mapping is
[FunctionMotors in pinned PX4](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/lib/mixer_module/functions/FunctionMotors.hpp).

## External offboard control

Use the combined launcher **without** `--demo`, then connect one offboard client
to `udpin:127.0.0.1:14540` for instance 0. The same host's QGC link is separate.
Do not run the built-in demo and another offboard controller simultaneously.

The included demo sends position-and-yaw setpoints at roughly 20 Hz. It streams
before requesting Offboard and checks received mode/arming state, not only
command acknowledgments. Positive NED Z is down; its climb target is home Z minus
2 m. Consult [PX4 Offboard requirements](https://docs.px4.io/v1.17/en/flight_modes/offboard)
when replacing this example. This repository supplies no ROS node or hardware
offboard controller.

## Bridge-only mode

`px4-mujoco bridge --headless` opens the simulator connection without launching,
stopping or arming PX4. It intentionally has no `--demo` option. An external PX4
launcher must supply the same model parameters, geometry, port, thrust curve
and stock `simulator_mavlink` startup. Inspect the exact generated overrides with:

```bash
px4-mujoco parameters
```

For new users, `run --px4 ...` is the reproducible, tested path. Bridge-only
orchestration is an integration interface, not automatic compatibility with an
arbitrary aircraft or firmware. Parameters cannot be applied to an already
running PX4 merely by setting environment variables in another terminal.
