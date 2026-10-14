"""Synthetic inertial, magnetic, barometric and GNSS data, in MAVLink units."""
from dataclasses import dataclass

import mujoco
import numpy as np

from .frames import D, attitude_to_px4, local_to_gps, vector_to_px4


@dataclass(frozen=True)
class SensorConfig:
    latitude: float = 47.397742
    longitude: float = 8.545594
    altitude: float = 488.0
    # An approximate constant mid-latitude field, not a global magnetic model.
    magnetic_ned_gauss: tuple = (0.215, 0.007, 0.427)
    seed: int = 0
    gps_epoch_us: int = 1_700_000_000_000_000


class Sensors:
    def __init__(self, aircraft, config=None):
        self.aircraft = aircraft
        self.config = config or SensorConfig()
        self.rng = np.random.default_rng(self.config.seed)
        self.previous_time = None
        self.previous_velocity = None
        self.slices = {}
        m = aircraft.model
        for name, kind in (("imu_accelerometer", mujoco.mjtSensor.mjSENS_ACCELEROMETER),
                           ("imu_gyro", mujoco.mjtSensor.mjSENS_GYRO)):
            sensor = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SENSOR, name)
            if (sensor < 0 or m.sensor_dim[sensor] != 3
                    or m.sensor_type[sensor] != kind
                    or m.sensor_objtype[sensor] != mujoco.mjtObj.mjOBJ_SITE):
                raise ValueError(f"Missing three-axis sensor {name}")
            site = m.sensor_objid[sensor]
            if (m.site_bodyid[site] != aircraft.root
                    or not np.allclose(m.site_quat[site], [1, 0, 0, 0])
                    or not np.allclose(m.site_pos[site], [0, 0, 0])):
                raise ValueError("IMU sites must be at the vehicle origin, aligned with its FLU axes")
            address = m.sensor_adr[sensor]
            self.slices[name] = slice(address, address + 3)

    @staticmethod
    def pressure(altitude):
        return 1013.25 * max(1e-6, 1 - 2.25577e-5 * altitude) ** 5.25588

    @staticmethod
    def pressure_altitude(pressure):
        return (1 - (max(pressure, 1e-9) / 1013.25) ** (1 / 5.25588)) / 2.25577e-5

    def sample(self):
        a, c = self.aircraft, self.config
        m, d = a.model, a.data
        mujoco.mj_subtreeVel(m, d)
        position = d.xpos[a.root].copy()
        velocity = vector_to_px4(d.subtree_linvel[a.root])
        rotation = d.xmat[a.root].reshape(3, 3)
        accel = np.zeros(3)
        if self.previous_time is not None and d.time > self.previous_time:
            accel = (velocity - self.previous_velocity) / (d.time - self.previous_time)
        self.previous_time, self.previous_velocity = d.time, velocity.copy()
        lat, lon, alt = local_to_gps(position, c.latitude, c.longitude, c.altitude)
        mag = (D @ rotation @ D).T @ np.asarray(c.magnetic_ned_gauss)
        mag += self.rng.normal(0, 5e-4, 3)
        # Avoid bit-identical stuck sensor streams; pressure and altitude stay consistent.
        pressure = max(1e-6, self.pressure(alt) + self.rng.normal(0, 0.005))
        t = int(round(d.time * 1_000_000)) + 1
        return dict(
            time_us=t, gps_time_us=c.gps_epoch_us + t,
            accel=vector_to_px4(d.sensordata[self.slices["imu_accelerometer"]]),
            gyro=vector_to_px4(d.sensordata[self.slices["imu_gyro"]]),
            mag=mag, pressure=pressure, pressure_altitude=self.pressure_altitude(pressure),
            quaternion=attitude_to_px4(rotation), latitude=lat, longitude=lon,
            altitude=alt, velocity=velocity, acceleration_ned=accel,
        )
