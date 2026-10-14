import json
from types import SimpleNamespace

import numpy as np
import pytest

from px4_mujoco_bridge import cli, demo
from px4_mujoco_bridge.model import Aircraft, default_model
from px4_mujoco_bridge.sensors import Sensors
from px4_mujoco_bridge.transport import Actuators


@pytest.mark.parametrize("old,new", [
    ('gravity="0 0 -9.80665"', 'gravity="0 0 -9.81"'),
    ('gear="0 0 1 0 0 -0.02"', 'gear="0 1 0 0 0 -0.02"'),
    ('mass="1.5"', 'mass="4"'),
    ('<inertial pos="0 0 0"', '<inertial pos="0.01 0 0"'),
])
def test_reject_inconsistent_models(tmp_path, old, new):
    model = tmp_path / "invalid.xml"
    model.write_text(default_model().read_text().replace(old, new))
    with pytest.raises(ValueError):
        Aircraft(model)


def test_reject_wrong_sensor_type(tmp_path):
    model = tmp_path / "wrong-sensor.xml"
    model.write_text(default_model().read_text().replace(
        '<accelerometer name="imu_accelerometer"', '<gyro name="imu_accelerometer"'))
    with pytest.raises(ValueError, match="imu_accelerometer"):
        Sensors(Aircraft(model))


def test_lockstep_timeout_does_not_advance_physics(tmp_path, monkeypatch):
    class FakeTransport:
        def __init__(self, port):
            self.calls = 0
        def connect(self, timeout):
            pass
        def sensors(self, sample):
            self.sample = sample
        def actuators(self, after_us, timeout):
            self.calls += 1
            if self.calls == 1:
                return Actuators(1, np.zeros(16), False, True)
            assert after_us == 4001
            return None
        def close(self):
            pass

    monkeypatch.setattr(cli, "Transport", FakeTransport)
    output = tmp_path / "run"
    args = cli.parser().parse_args(["bridge", "--headless", "--output", str(output)])
    with pytest.raises(TimeoutError, match="not advanced"):
        cli.run(args)
    result = json.loads((output / "result.json").read_text())
    assert result["steps"] == 1
    assert result["simulation_seconds"] == pytest.approx(.004)
    assert not result["completed"]


class FakeLink:
    def __init__(self):
        self.messages = []
        self.commands = []
        self.mav = SimpleNamespace(
            heartbeat_send=lambda *args: None,
            set_position_target_local_ned_send=lambda *args: None,
            command_long_send=lambda *args: self.commands.append(args),
        )
    def recv_match(self, blocking):
        return self.messages.pop(0) if self.messages else None
    def close(self):
        pass


def message(kind, **values):
    return SimpleNamespace(get_type=lambda: kind, get_srcSystem=lambda: 1, **values)


@pytest.fixture
def simulated_demo(monkeypatch):
    link = FakeLink()
    monkeypatch.setattr(demo.mavutil, "mavlink_connection", lambda *args, **kwargs: link)
    return demo.Demo(0), link


def telemetry(link, position, armed=False, offboard=True, landed=False):
    m = demo.mavutil.mavlink
    link.messages.extend([
        message("HEARTBEAT", autopilot=m.MAV_AUTOPILOT_PX4,
                base_mode=128 if armed else 0, custom_mode=(6 << 16) if offboard else 0),
        message("LOCAL_POSITION_NED", x=position[0], y=position[1], z=position[2], vx=0, vy=0, vz=0),
        message("EXTENDED_SYS_STATE", landed_state=m.MAV_LANDED_STATE_ON_GROUND if landed else m.MAV_LANDED_STATE_IN_AIR),
    ])


def test_demo_requires_state_feedback_and_landing(simulated_demo):
    d, link = simulated_demo
    m = demo.mavutil.mavlink
    telemetry(link, [0, 0, 0], offboard=False, landed=True)
    d.tick(10)
    assert d.phase == "streaming setpoints"
    telemetry(link, [0, 0, 0], offboard=False, landed=True)
    d.tick(12.1)
    assert d.phase == "waiting for offboard"
    telemetry(link, [0, 0, 0], offboard=False, landed=True)
    link.messages.append(message("COMMAND_ACK", command=m.MAV_CMD_DO_SET_MODE, result=0))
    d.tick(12.2)
    assert d.phase == "waiting for offboard"  # ACK is not observed mode state.
    telemetry(link, [0, 0, 0], landed=True)
    d.tick(13)
    assert d.phase == "waiting for arm"
    telemetry(link, [0, 0, 0], armed=True, landed=True)
    d.tick(14)
    for index, target in enumerate(([0,0,-2], [1,0,-2], [1,1,-2], [0,1,-2], [0,0,-2])):
        t = 15 + 3 * index
        telemetry(link, target, armed=True)
        d.tick(t)
        telemetry(link, target, armed=True)
        d.tick(t + 2.1)
    assert d.phase == "landing" and not d.finished
    telemetry(link, [0, 0, 0], armed=True, landed=True)
    d.tick(30)
    assert not d.finished  # Touchdown alone is insufficient.
    telemetry(link, [0, 0, 0], armed=False, landed=True)
    d.tick(31)
    assert d.finished and d.phase == "complete" and d.failure is None
    assert d.waypoint == 4
    commands = [args[2] for args in link.commands]
    assert commands == [m.MAV_CMD_DO_SET_MODE, m.MAV_CMD_COMPONENT_ARM_DISARM, m.MAV_CMD_NAV_LAND]


def test_demo_rejects_stale_position_even_with_heartbeat(simulated_demo):
    d, link = simulated_demo
    telemetry(link, [0,0,0], landed=True)
    d.tick(10)
    link.messages.append(message("HEARTBEAT", autopilot=demo.mavutil.mavlink.MAV_AUTOPILOT_PX4,
                                 base_mode=0, custom_mode=0))
    with pytest.raises(RuntimeError, match="local position became stale"):
        d.tick(11.1)


def test_px4_version_guard_before_launch(tmp_path):
    with pytest.raises(ValueError, match="Build stock PX4"):
        cli.validate_px4(tmp_path)
