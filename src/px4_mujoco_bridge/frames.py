"""Explicit NWU/FLU to NED/FRD basis changes. Quaternions are w,x,y,z."""
import mujoco
import numpy as np

D = np.diag([1.0, -1.0, -1.0])
EARTH_RADIUS_M = 6_378_137.0


def vector_to_px4(value):
    value = np.asarray(value, dtype=float)
    if value.shape != (3,) or not np.isfinite(value).all():
        raise ValueError("Expected a finite three-vector")
    return D @ value


def attitude_to_px4(rotation_nwu_from_flu):
    rotation = np.asarray(rotation_nwu_from_flu, dtype=float)
    if rotation.shape != (3, 3) or not np.isfinite(rotation).all():
        raise ValueError("Expected a finite 3x3 rotation")
    quaternion = np.empty(4)
    mujoco.mju_mat2Quat(quaternion, (D @ rotation @ D).flatten())
    return quaternion


def local_to_gps(position_nwu, latitude, longitude, altitude):
    north, east, down = vector_to_px4(position_nwu)
    if not np.isfinite([latitude, longitude, altitude]).all() or abs(latitude) >= 85:
        raise ValueError("The local tangent-plane GPS model requires latitude within +/-85 deg")
    return (
        latitude + np.degrees(north / EARTH_RADIUS_M),
        longitude + np.degrees(east / (EARTH_RADIUS_M * np.cos(np.radians(latitude)))),
        altitude - down,
    )
