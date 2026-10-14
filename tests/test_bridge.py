import socket

import mujoco
import numpy as np
import pytest
from pymavlink.dialects.v20 import common as mavlink

from px4_mujoco_bridge.cli import parser, px4_environment
from px4_mujoco_bridge.frames import D, attitude_to_px4, local_to_gps, vector_to_px4
from px4_mujoco_bridge.model import Aircraft, default_model, motor_thrust
from px4_mujoco_bridge.sensors import Sensors
from px4_mujoco_bridge.transport import Transport


def test_installed_model_exists():
    assert default_model().is_file()


def test_frames():
    np.testing.assert_array_equal(vector_to_px4([1, 2, 3]), [1, -2, -3])
    np.testing.assert_allclose(D @ D, np.eye(3))
    np.testing.assert_allclose(attitude_to_px4(np.eye(3)), [1, 0, 0, 0])
    r = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
    np.testing.assert_allclose(attitude_to_px4(r), [2**-0.5, 0, 0, -2**-0.5], atol=1e-12)


@pytest.mark.parametrize("vector", [[1, 2], [1, 2, float("nan")], [[1, 2, 3]]])
def test_bad_vectors(vector):
    with pytest.raises(ValueError):
        vector_to_px4(vector)


def test_gps_signs():
    lat, lon, alt = local_to_gps([10, 20, 30], 47, 8, 400)
    assert lat > 47 and lon < 8 and alt == 430
    with pytest.raises(ValueError):
        local_to_gps([0, 0, 0], 90, 8, 400)


def test_squared_mapping_and_disarmed_gate():
    controls = np.zeros(16)
    controls[:4] = [.5, 1, -.2, 2]
    np.testing.assert_array_equal(motor_thrust(controls, [10]*4, True), [2.5, 10, 0, 10])
    np.testing.assert_array_equal(motor_thrust(controls, [10]*4, False), [0]*4)
    controls[:4] = [np.nan, np.inf, -np.inf, .2]
    np.testing.assert_allclose(motor_thrust(controls, [10]*4, True), [0, 0, 0, .4])
    with pytest.raises(ValueError):
        motor_thrust([0]*4, [10]*4, True)


def test_model_contract_and_parameters():
    a = Aircraft()
    assert a.model.nq == 7 and a.model.nu == 4 and a.mass == 1.5
    params = a.px4_parameters()
    assert params["CA_ROTOR_COUNT"] == 4 and params["THR_MDL_FAC"] == 1
    assert params["PWM_MAIN_FUNC4"] == 104 and params["PWM_MAIN_FUNC5"] == 0
    np.testing.assert_allclose(a.positions, [[.2,.2,0],[-.2,-.2,0],[.2,-.2,0],[-.2,.2,0]])
    np.testing.assert_allclose(a.km, [.02,.02,-.02,-.02])


@pytest.mark.parametrize("rotor", range(4))
def test_individual_rotor_wrench_matches_px4(rotor):
    a = Aircraft()
    a.data.qpos[2] = 2
    a.data.ctrl[:] = 0
    a.data.ctrl[rotor] = 1
    mujoco.mj_forward(a.model, a.data)
    f = vector_to_px4(a.data.qfrc_actuator[:3])
    torque = vector_to_px4(a.data.qfrc_actuator[3:])
    np.testing.assert_allclose(f, [0, 0, -1])
    np.testing.assert_allclose(torque, np.cross(a.positions[rotor], f) + [0,0,a.km[rotor]], atol=1e-12)


def test_equal_thrust_hover_dynamics():
    a = Aircraft()
    a.data.qpos[2] = 2
    a.data.ctrl[:] = a.mass * 9.80665 / 4
    for _ in range(500):
        mujoco.mj_step(a.model, a.data)
    np.testing.assert_allclose(a.data.qpos[:3], [0,0,2], atol=1e-10)
    np.testing.assert_allclose(a.data.qvel, 0, atol=1e-10)


def test_ground_specific_force_and_noise():
    a = Aircraft(); a.reset()
    s = Sensors(a)
    first, second = s.sample(), s.sample()
    np.testing.assert_allclose(first["accel"], [0, 0, -9.80665], atol=1e-5)
    assert first["time_us"] == 1 and first["gps_time_us"] > 1_000_000_000_000_000
    assert first["pressure"] != second["pressure"]
    np.testing.assert_allclose(Sensors.pressure(first["pressure_altitude"]), first["pressure"])


def test_sensor_noise_reproducible():
    a, b = Aircraft(), Aircraft()
    a.reset(); b.reset()
    sa, sb = Sensors(a).sample(), Sensors(b).sample()
    np.testing.assert_array_equal(sa["mag"], sb["mag"])
    assert sa["pressure"] == sb["pressure"]


def test_environment_isolation():
    env = px4_environment(Aircraft().px4_parameters(), 2,
                          {"PX4_PARAM_UNRELATED": "99", "PX4_SIM_HOSTNAME": "remote", "DISPLAY": ":0"})
    assert "PX4_PARAM_UNRELATED" not in env and "PX4_SIM_HOSTNAME" not in env
    assert env["PX4_SYS_AUTOSTART"] == "10016"
    assert env["PX4_SIM_HOST_ADDR"] == "127.0.0.1" and env["PX4_PARAM_MAV_SYS_ID"] == "3"
    assert env["DISPLAY"] == ":0"


@pytest.mark.parametrize("duration", ["-1", "0", "nan", "inf"])
def test_bad_cli_durations(duration):
    with pytest.raises(SystemExit):
        parser().parse_args(["bridge", "--duration", duration])


def test_demo_not_available_for_unowned_bridge():
    with pytest.raises(SystemExit):
        parser().parse_args(["bridge", "--demo"])
    assert not parser().parse_args(["run", "--px4", "/unused"]).demo


class SocketWriter:
    def __init__(self, connection):
        self.connection = connection
    def write(self, data):
        self.connection.sendall(data)


def test_tcp_roundtrip_fragmentation_stale_frame_and_disconnect():
    transport = Transport(port=0)
    client = socket.create_connection(("127.0.0.1", transport.server.getsockname()[1]))
    px4 = mavlink.MAVLink(SocketWriter(client), srcSystem=1, srcComponent=1)
    try:
        px4.heartbeat_send(mavlink.MAV_TYPE_QUADROTOR, mavlink.MAV_AUTOPILOT_PX4, 0, 0, 0)
        transport.connect(timeout=1)
        px4.hil_actuator_controls_send(10, [0.1]*16, 128, 1)
        packet = px4.hil_actuator_controls_encode(20, [0.2]*16, 128, 1).pack(px4)
        client.sendall(packet[:4]); client.sendall(packet[4:])
        frame = transport.actuators(after_us=20, timeout=1)
        assert frame.time_us == 20 and frame.armed and frame.lockstep
        np.testing.assert_allclose(frame.controls, .2)
        assert transport.actuators(after_us=21, timeout=.02) is None
        a = Aircraft(); a.reset()
        transport.sensors(Sensors(a).sample())
        client.settimeout(1)
        decoder = mavlink.MAVLink(None)
        messages = decoder.parse_buffer(client.recv(65536))
        imu = next(x for x in messages if x.get_type() == "HIL_SENSOR")
        assert imu.time_usec == 1 and not imu.fields_updated & (1 << 10)
        assert imu.zacc == pytest.approx(-9.80665, abs=1e-5)
        client.close()
        with pytest.raises(ConnectionError):
            transport.receive(.1)
    finally:
        client.close(); transport.close()


def test_port_conflict_is_visible():
    first = Transport(port=0)
    try:
        with pytest.raises(OSError):
            Transport(port=first.server.getsockname()[1])
    finally:
        first.close()
