"""The fixed-rotor model contract and matching PX4 allocation parameters."""
from importlib.resources import files
from pathlib import Path

import mujoco
import numpy as np

from .frames import vector_to_px4


def default_model():
    return Path(str(files("px4_mujoco_bridge") / "models" / "quadrotor.xml"))


def motor_thrust(controls, maximum, armed):
    """Signal-squared thrust, paired with PX4 THR_MDL_FAC=1."""
    controls = np.asarray(controls, dtype=float)
    if controls.shape != (16,):
        raise ValueError("HIL_ACTUATOR_CONTROLS must contain 16 values")
    maximum = np.asarray(maximum, dtype=float)
    if not armed:
        return np.zeros_like(maximum)
    # Invalid values produce zero, including +inf; never turn +inf into full thrust.
    signal = np.nan_to_num(controls[:len(maximum)], nan=0.0, posinf=0.0, neginf=0.0)
    return maximum * np.clip(signal, 0.0, 1.0) ** 2


class Aircraft:
    """Accept a single free rigid body with identical, fixed +FLU-Z thrusters."""

    def __init__(self, path=None):
        self.path = default_model() if path is None else Path(path).resolve()
        self.model = mujoco.MjModel.from_xml_path(str(self.path))
        self.data = mujoco.MjData(self.model)
        m = self.model
        self.root = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "vehicle")
        if self.root < 1 or m.nq != 7 or m.nv != 6 or not 4 <= m.nu <= 12:
            raise ValueError("Model needs body 'vehicle', one free joint, and 4..12 fixed thrusters")
        if m.njnt != 1 or m.jnt_type[0] != mujoco.mjtJoint.mjJNT_FREE or m.jnt_bodyid[0] != self.root:
            raise ValueError("The free joint must belong to 'vehicle'")
        if not np.allclose(m.opt.gravity, [0, 0, -9.80665]):
            raise ValueError("Model gravity must be [0,0,-9.80665] in NWU")
        self.maximum = m.actuator_ctrlrange[:, 1].copy()
        if not np.isfinite(self.maximum).all() or np.any(self.maximum <= 0):
            raise ValueError("Thrusters need positive finite control limits in newtons")
        if not np.allclose(self.maximum, self.maximum[0]):
            raise ValueError("This example requires equal per-rotor thrust limits")
        self.positions = []
        self.km = []
        for i in range(m.nu):
            if (m.actuator_trntype[i] != mujoco.mjtTrn.mjTRN_SITE
                    or not m.actuator_ctrllimited[i]
                    or m.actuator_ctrlrange[i, 0] != 0
                    or not np.allclose(m.actuator_gear[i, :5], [0, 0, 1, 0, 0])
                    or m.actuator_dyntype[i] != mujoco.mjtDyn.mjDYN_NONE
                    or m.actuator_gaintype[i] != mujoco.mjtGain.mjGAIN_FIXED
                    or m.actuator_biastype[i] != mujoco.mjtBias.mjBIAS_NONE
                    or m.actuator_forcelimited[i]
                    or m.actuator_gainprm[i, 0] != 1):
                raise ValueError("Use direct site motors with gear='0 0 1 0 0 +/-kappa'")
            site = m.actuator_trnid[i, 0]
            if m.site_bodyid[site] != self.root or not np.allclose(m.site_quat[site], [1, 0, 0, 0]):
                raise ValueError("Thruster sites must be unrotated and directly attached to vehicle")
            self.positions.append(vector_to_px4(m.site_pos[site]))
            self.km.append(-float(m.actuator_gear[i, 5]))
        # Supported model is a single rigid body; mass-centre offsets would require
        # shifting the allocation geometry and IMU/GNSS reference consistently.
        if not np.allclose(m.body_ipos[self.root], [0, 0, 0]):
            raise ValueError("Vehicle centre of mass must coincide with the root origin")
        if np.any(m.body_mass[np.arange(m.nbody) != self.root] > 0):
            raise ValueError("Put the complete mass and inertia on body 'vehicle'")
        self.mass = float(m.body_mass[self.root])
        self.positions = np.asarray(self.positions)
        if not 0.1 <= self.mass * 9.80665 / np.sum(self.maximum) <= 0.8:
            raise ValueError("Hover thrust fraction must fit PX4 MPC_THR_HOVER limits [0.1, 0.8]")

    def reset(self):
        mujoco.mj_resetData(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)
        for _ in range(round(1.0 / self.model.opt.timestep)):
            mujoco.mj_step(self.model, self.data)
        self.data.time = 0.0
        mujoco.mj_forward(self.model, self.data)

    def px4_parameters(self):
        params = {
            "CA_AIRFRAME": 0, "CA_ROTOR_COUNT": self.model.nu,
            "THR_MDL_FAC": 1.0,
            "MPC_THR_HOVER": self.mass * 9.80665 / np.sum(self.maximum),
            "COM_RC_IN_MODE": 4,  # SITL example uses GCS/commands, not a physical RC.
            "SIM_GZ_EN": 0, "IMU_INTEG_RATE": 250,
            "MAV_SYS_ID": 1,
        }
        for i, (position, km) in enumerate(zip(self.positions, self.km)):
            for axis, value in zip("XYZ", position):
                params[f"CA_ROTOR{i}_P{axis}"] = float(value)
            params.update({f"CA_ROTOR{i}_AX": 0, f"CA_ROTOR{i}_AY": 0,
                           f"CA_ROTOR{i}_AZ": -1, f"CA_ROTOR{i}_KM": km})
        for i in range(16):
            params[f"PWM_MAIN_FUNC{i+1}"] = 101 + i if i < self.model.nu else 0
        return params
