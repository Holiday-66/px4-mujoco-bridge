"""An opt-in demo for the local PX4 process owned by the combined launcher."""
import os

import numpy as np

os.environ["MAVLINK20"] = "1"
from pymavlink import mavutil


class Demo:
    def __init__(self, instance):
        self.link = mavutil.mavlink_connection(
            f"udpin:127.0.0.1:{14540 + instance}", source_system=250,
            source_component=190, dialect="common")
        self.target = instance + 1
        self.phase = "waiting for position"
        self.start = None
        self.phase_start = 0.0
        self.last_send = -1.0
        self.last_heartbeat = -1.0
        self.position = None
        self.velocity = None
        self.home = None
        self.armed = False
        self.offboard = False
        self.landed = False
        self.stable_since = None
        self.waypoint = 0
        self.finished = False
        self.failure = None
        self.acknowledgments = []
        self.last_rx = None
        self.last_position_rx = None

    def close(self):
        self.link.close()

    def command(self, command, *params):
        self.link.mav.command_long_send(self.target, 1, command, 0, *(list(params) + [0] * (7 - len(params))))

    def transition(self, phase, t):
        self.phase, self.phase_start, self.stable_since = phase, t, None
        print(f"demo: {phase}", flush=True)

    def tick(self, t):
        m = mavutil.mavlink
        for _ in range(200):
            msg = self.link.recv_match(blocking=False)
            if msg is None:
                break
            if msg.get_srcSystem() != self.target:
                continue
            self.last_rx = t
            kind = msg.get_type()
            if kind == "HEARTBEAT" and msg.autopilot == m.MAV_AUTOPILOT_PX4:
                self.armed = bool(msg.base_mode & m.MAV_MODE_FLAG_SAFETY_ARMED)
                self.offboard = ((msg.custom_mode >> 16) & 255) == 6
            elif kind == "LOCAL_POSITION_NED":
                p = np.array([msg.x, msg.y, msg.z])
                v = np.array([msg.vx, msg.vy, msg.vz])
                if np.isfinite(p).all() and np.isfinite(v).all():
                    self.position, self.velocity = p, v
                    self.last_position_rx = t
            elif kind == "EXTENDED_SYS_STATE":
                self.landed = msg.landed_state == m.MAV_LANDED_STATE_ON_GROUND
            elif kind == "COMMAND_ACK":
                self.acknowledgments.append({"command": int(msg.command), "result": int(msg.result)})
                print(f"demo: command {msg.command} acknowledgment {msg.result}", flush=True)

        if t - self.last_heartbeat >= 1.0:
            self.link.mav.heartbeat_send(m.MAV_TYPE_GCS, m.MAV_AUTOPILOT_INVALID, 0, 0, m.MAV_STATE_ACTIVE)
            self.last_heartbeat = t
        if self.phase == "waiting for position":
            if self.position is not None and t - self.last_position_rx < 1 and t >= 10:
                self.home = self.position.copy()
                self.transition("streaming setpoints", t)
            elif t > 45:
                raise RuntimeError("Demo: no local position; check EKF/GPS in px4.log")
            return

        # A 1 m square at 2 m above the captured local ground position.
        offsets = ([0, 0, -2], [1, 0, -2], [1, 1, -2], [0, 1, -2], [0, 0, -2])
        target = self.home + offsets[self.waypoint]
        if t - self.last_send >= 0.05 and self.phase not in ("landing", "complete"):
            # Position + yaw only: ignore velocity, acceleration and yaw-rate.
            mask = 8 | 16 | 32 | 64 | 128 | 256 | 2048
            self.link.mav.set_position_target_local_ned_send(
                int(t * 1000) & 0xFFFFFFFF, self.target, 1, m.MAV_FRAME_LOCAL_NED,
                mask, *target, 0, 0, 0, 0, 0, 0, 0, 0)
            self.last_send = t

        if self.last_rx is None or t - self.last_rx > 3:
            raise RuntimeError("Demo telemetry stopped; stopping this SITL session")
        if self.last_position_rx is None or t - self.last_position_rx > 1:
            raise RuntimeError("Demo local position became stale; stopping this SITL session")
        if self.phase == "streaming setpoints" and t - self.phase_start >= 2:
            self.command(m.MAV_CMD_DO_SET_MODE, m.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6)
            self.transition("waiting for offboard", t)
        elif self.phase == "waiting for offboard" and self.offboard:
            self.command(m.MAV_CMD_COMPONENT_ARM_DISARM, 1)
            self.transition("waiting for arm", t)
        elif self.phase == "waiting for arm" and self.armed:
            self.start = t
            self.transition("flying waypoint 0", t)
        elif self.phase.startswith("flying"):
            if not self.armed or not self.offboard:
                self.failure = "PX4 left armed Offboard mode during the route"
                self.command(m.MAV_CMD_NAV_LAND)
                self.transition("landing", t)
            elif np.linalg.norm(self.position - target) < 0.20 and np.linalg.norm(self.velocity) < 0.35:
                if self.stable_since is None:
                    self.stable_since = t
                if t - self.stable_since >= 2:
                    if self.waypoint == len(offsets) - 1:
                        self.command(m.MAV_CMD_NAV_LAND)
                        self.transition("landing", t)
                    else:
                        self.waypoint += 1
                        self.transition(f"flying waypoint {self.waypoint}", t)
            else:
                self.stable_since = None
        elif self.phase == "landing" and not self.armed and self.landed:
            self.transition("complete", t)
            self.finished = True

        limit = 40 if self.phase == "landing" or self.phase.startswith("flying") else 10
        if t - self.phase_start > limit and not self.finished:
            raise RuntimeError(f"Demo timed out in '{self.phase}'; no forced arming/disarming attempted")
