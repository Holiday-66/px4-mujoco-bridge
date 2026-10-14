"""MAVLink 2 over a loopback TCP server; no middleware or physical-device access."""
from dataclasses import dataclass
import select
import socket
import time

import numpy as np
from pymavlink.dialects.v20 import common as mavlink


@dataclass(frozen=True)
class Actuators:
    time_us: int
    controls: np.ndarray
    armed: bool
    lockstep: bool


class Transport:
    def __init__(self, port=4560):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client = None
        try:
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(("127.0.0.1", port))
            self.server.listen(1)
        except BaseException:
            self.server.close()
            raise
        self.mav = mavlink.MAVLink(self, srcSystem=200, srcComponent=200)
        self.mav.robust_parsing = True
        self.last_heartbeat = -1_000_000
        self.last_gps = -100_000
        self.last_truth = -20_000
        self.system_id = None

    def write(self, buffer):
        if self.client is None:
            raise ConnectionError("Cannot send sensors before PX4 connects")
        self.client.sendall(buffer)

    def connect(self, timeout=30.0):
        self.server.settimeout(timeout)
        self.client, _ = self.server.accept()
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.client.settimeout(2.0)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for message in self.receive(min(0.1, max(0, deadline-time.monotonic()))):
                if message.get_type() == "HEARTBEAT":
                    self.system_id = message.get_srcSystem()
                    return
        raise TimeoutError("PX4 connected but did not send its simulator heartbeat")

    def close(self):
        if self.client is not None:
            self.client.close()
        self.server.close()

    def receive(self, timeout):
        if self.client is None:
            raise ConnectionError("No PX4 connection")
        if not select.select([self.client], [], [], timeout)[0]:
            return []
        raw = self.client.recv(65536)
        if not raw:
            raise ConnectionError("PX4 closed the simulator connection")
        return self.mav.parse_buffer(raw) or []

    def actuators(self, after_us=0, timeout=2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            newest = None
            for message in self.receive(min(0.1, max(0, deadline-time.monotonic()))):
                if (message.get_type() == "HIL_ACTUATOR_CONTROLS"
                        and message.get_srcSystem() == self.system_id
                        and message.time_usec >= after_us):
                    newest = Actuators(
                        message.time_usec, np.asarray(message.controls, dtype=float),
                        bool(message.mode & mavlink.MAV_MODE_FLAG_SAFETY_ARMED),
                        bool(message.flags & 1),  # PX4 lockstep flag; not named in common.xml.
                    )
            if newest is not None:
                return newest
        return None

    @staticmethod
    def i16(value):
        return int(np.clip(round(value), -32768, 32767))

    @staticmethod
    def u16(value):
        return int(np.clip(round(value), 0, 65535))

    def sensors(self, sample):
        s, t = sample, sample["time_us"]
        if t - self.last_heartbeat >= 1_000_000:
            self.mav.heartbeat_send(mavlink.MAV_TYPE_GENERIC, mavlink.MAV_AUTOPILOT_INVALID,
                                    mavlink.MAV_MODE_FLAG_HIL_ENABLED, 0, mavlink.MAV_STATE_ACTIVE)
            self.last_heartbeat = t
        # Differential pressure is not modelled; its update bit (10) stays clear.
        self.mav.hil_sensor_send(t, *s["accel"], *s["gyro"], *s["mag"],
                                 s["pressure"], 0.0, s["pressure_altitude"], 20.0,
                                 0x1FFF & ~(1 << 10))
        lat, lon, alt = round(s["latitude"] * 1e7), round(s["longitude"] * 1e7), round(s["altitude"] * 1000)
        velocity = 100 * s["velocity"]
        if t - self.last_gps >= 100_000:
            speed = np.linalg.norm(velocity[:2])
            course = self.u16(np.degrees(np.arctan2(velocity[1], velocity[0])) % 360 * 100) if speed > 5 else 65535
            self.mav.hil_gps_send(s["gps_time_us"], 3, lat, lon, alt, 50, 80,
                                 self.u16(np.linalg.norm(velocity)),
                                 *(self.i16(v) for v in velocity), course, 12)
            self.last_gps = t
        if t - self.last_truth >= 20_000:
            self.mav.hil_state_quaternion_send(t, s["quaternion"], *s["gyro"], lat, lon, alt,
                *(self.i16(v) for v in velocity), 0, 0,
                *(self.i16(v * 1000 / 9.80665) for v in s["acceleration_ned"]))
            self.last_truth = t
