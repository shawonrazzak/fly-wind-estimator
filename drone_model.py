
import numpy as np
import matplotlib.pyplot as plt
import sympy as sp
import figurefirst as fifi
import figure_functions as ff
from pybounds import Simulator
import util


class DroneParameters:
    """ Stores drone parameters.
    """

    def __init__(self):
        self.g = 9.81  # gravity [m/s^2]
        self.m = 0.086  # mass [kg]
        self.M = 2.529  # mass [kg]
        self.Mm = 4 * self.m + self.M  # total mass [kg]
        self.L = 0.2032  # length [m]
        self.R = 0.1778  # average body radius [m]
        self.I_x = 2 * (self.M * self.R ** 2) / 5 + 2 * self.m * self.L ** 2  # [kg*m^2] moment of inertia about x
        self.I_y = 2 * (self.M * self.R ** 2) / 5 + 2 * self.m * self.L ** 2  # [kg*m^2] moment of inertia about y
        self.I_z = 2 * (self.M * self.R ** 2) / 5 + 4 * self.m * self.L ** 2  # [kg*m^2] moment of inertia about y
        self.b = 1.8311  # thrust coefficient
        self.d = 0.01  # drag constant
        self.C = 0.1  # drag coefficient from ground speed plus air speed


class DroneModel:
    """ Stores drone model
    """

    def __init__(self):
        # Parameters
        self.params = DroneParameters()

        # State names
        self.state_names = ['x',  # x position in inertial frame [m]
                            'y',  # y position in inertial frame [m]
                            'z',  # z position in inertial frame [m]
                            'v_x',  # x velocity in body-level frame (parallel to heading) [m/s]
                            'v_y',  # y velocity in body-level frame (perpendicular to heading) [m/s]
                            'v_z',  # z velocity in body-level frame [m/s]
                            'phi',  # roll in body frame [rad],
                            'theta',  # pitch in vehicle-2 frame [rad],
                            'psi',  # yaw in body-level frame (vehicle-1) [rad]
                            'omega_x',  # roll rate in body-frame [rad/s]
                            'omega_y',  # pitch rate in body-frame [rad/s]
                            'omega_z',  # yaw rate in body-frame [rad/s]
                            'w',  # wind speed in XY-plane [ms]
                            'zeta',  # wind direction in XY-plane[rad]

                            'm',  # mass [kg]
                            'I_x',  # mass moment of inertia about body x-axis [kg*m^2]
                            'I_y',  # mass moment of inertia about body y-axis [kg*m^2]
                            'I_z',  # mass moment of inertia about body z-axis [kg*m^2]
                            'C',  # translational drag damping constant [N/m/s]
                            ]

        # Input names
        self.input_names = ['u_thrust',  # thrust force [N]
                            'u_phi',  # roll torque [N*m]
                            'u_theta',  # pitch torque [N*m]
                            'u_psi',  # yaw torque [N*m]
                            'u_w',  # wind magnitude control
                            'u_zeta',  # wind direction control
                            ]

        # Measurement names
        measurement_names = ['g', 'beta', 'r', 'r_x', 'r_y', 'a', 'gamma', 'v_x_dot', 'v_y_dot', 'q', 'alpha', 'u_x', 'u_y']
        self.measurement_names = self.state_names + self.input_names + measurement_names

    def f(self, X, U):
        """ Dynamic model.
        """
        gravity = self.params.g

        # States
        x, y, z, v_x, v_y, v_z, phi, theta, psi, omega_x, omega_y, omega_z, w, zeta, m, Ix, Iy, Iz, C = X

        # Inputs
        u_thrust, u_phi, u_theta, u_psi, u_w, u_zeta = U

        # Drag dynamics
        a_x = v_x - w * np.cos(psi - zeta)
        a_y = v_y + w * np.sin(psi - zeta)
        a_z = v_z

        # Dynamics
        # Rotation
        phi_dot = omega_x + omega_z * np.tan(theta) * np.cos(phi) + omega_y * np.tan(theta) * np.sin(phi)
        theta_dot = omega_y * np.cos(phi) - omega_z * np.sin(phi)
        psi_dot = omega_z * np.cos(phi) * (1 / np.cos(theta)) + omega_y * np.sin(phi) * (1 / np.cos(theta))

        omega_x_dot = (1 / Ix) * u_phi + omega_z * omega_y * (Iy - Iz) / Ix
        omega_y_dot = (1 / Iy) * u_theta + omega_z * omega_x * (Iz - Ix) / Iy
        omega_z_dot = (1 / Iz) * u_psi + omega_x * omega_y * (Ix - Iy) / Iz

        # Position in inertial frame
        x_dot = v_x * np.cos(psi) - v_y * np.sin(psi)
        y_dot = v_x * np.sin(psi) + v_y * np.cos(psi)
        z_dot = v_z

        # Velocity in body-level frame
        v_x_dot = (1 / m) * (u_thrust * np.cos(phi) * np.sin(theta) - C * a_x) + v_y * psi_dot
        v_y_dot = (1 / m) * (-u_thrust * np.sin(phi) - C * a_y) - v_x * psi_dot
        v_z_dot = (1 / m) * (-u_thrust * np.cos(phi) * np.cos(theta) - C * v_z + m * gravity)

        # Wind
        w_dot = u_w
        zeta_dot = u_zeta

        # Parameters
        m_dot = 0*m
        I_x_dot = 0*Ix
        I_y_dot = 0*Iy
        I_z_dot = 0*Iz
        C_dot = 0*C

        # Package and return xdot
        x_dot = [x_dot, y_dot, z_dot,
                 v_x_dot, v_y_dot, v_z_dot,
                 phi_dot, theta_dot, psi_dot,
                 omega_x_dot, omega_y_dot, omega_z_dot,
                 w_dot, zeta_dot,
                 m_dot, I_x_dot, I_y_dot, I_z_dot, C_dot
                 ]

        return x_dot

    def h(self, X, U):
        """ Measurement model.
        """
        # m = self.params.Mm
        # Ix = self.params.Ix
        # Iy = self.params.Iy
        # Iz = self.params.Iz
        # C = self.params.C
        gravity = self.params.g

        # States
        x, y, z, v_x, v_y, v_z, phi, theta, psi, omega_x, omega_y, omega_z, w, zeta, m, Ix, Iy, Iz, C = X

        # Inputs
        u_thrust, u_phi, u_theta, u_psi, u_w, u_zeta = U

        # Rotation
        # phi_dot = omega_x + omega_z * np.tan(theta) * np.cos(phi) + omega_y * np.tan(theta) * np.sin(phi)
        # theta_dot = omega_y * np.cos(phi) - omega_z * np.sin(phi)
        psi_dot = omega_z * np.cos(phi) * (1 / np.cos(theta)) + omega_y * np.sin(phi) * (1 / np.cos(theta))

        # Airspeed & apparent airflow angle in body-level frame
        a_x = v_x - w * np.cos(psi - zeta)
        a_y = v_y + w * np.sin(psi - zeta)
        a_z = v_z
        a = np.sqrt(a_x ** 2 + a_y ** 2)
        gamma = np.arctan2(a_y, a_x)

        # Velocity in body-level frame
        v_x_dot = (1 / m) * (u_thrust * np.cos(phi) * np.sin(theta) - C * a_x) + v_y * psi_dot
        v_y_dot = (1 / m) * (-u_thrust * np.sin(phi) - C * a_y) - v_x * psi_dot
        v_z_dot = (1 / m) * (u_thrust * np.cos(phi) * np.cos(theta) - C * v_z - m * gravity)

        u_x = u_thrust * np.cos(phi) * np.sin(theta)
        u_y = -u_thrust * np.sin(phi)
        u_z = u_thrust * np.cos(phi) * np.cos(theta)

        # Ground speed & course direction in body-level frame
        g = np.sqrt(v_x ** 2 + v_y ** 2)
        r = g / z
        r_x = v_x / z
        r_y = v_y / z
        beta = np.arctan2(v_y, v_x)

        # Acceleration
        q = np.sqrt(v_x_dot ** 2 + v_y_dot ** 2)
        alpha = np.arctan2(v_y_dot, v_x_dot)

        # Unwrap angles
        if np.array(phi).ndim > 0:
            if np.array(phi).shape[0] > 1:
                unwrap_function = util.smart_unwrap
                # phi = unwrap_function(phi)
                # theta = unwrap_function(theta)
                psi = unwrap_function(psi)
                gamma = unwrap_function(gamma)
                beta = unwrap_function(beta)
                alpha = unwrap_function(alpha)
                # zeta = unwrap_function(zeta)

        Y = list(X) + list(U) + [g, beta, r, r_x, r_y, a, gamma, v_x_dot, v_y_dot, q, alpha, u_x, u_y]

        return Y


class DroneSimulator(Simulator):
    def __init__(self, dt=0.1, mpc_horizon=10, r_u=1e-2, input_mode='direct', control_mode='velocity_body_level'):
        self.dynamics = DroneModel()
        super().__init__(self.dynamics.f, self.dynamics.h, dt=dt, mpc_horizon=mpc_horizon,
                         state_names=self.dynamics.state_names,
                         input_names=self.dynamics.input_names,
                         measurement_names=self.dynamics.measurement_names)

        # Set parameters
        self.params = DroneParameters()

        # Define cost function
        self.control_mode = control_mode
        if self.control_mode == 'velocity_body_level':
            cost = (1.0 * (self.model.x['v_x'] - self.model.tvp['v_x_set']) ** 2 +
                    1.0 * (self.model.x['v_y'] - self.model.tvp['v_y_set']) ** 2 +
                    1.0 * (self.model.x['z'] - self.model.tvp['z_set']) ** 2 +
                    1.0 * (self.model.x['psi'] - self.model.tvp['psi_set']) ** 2 +
                    1.0 * (self.model.x['w'] - self.model.tvp['w_set']) ** 2 +
                    1.0 * (self.model.x['zeta'] - self.model.tvp['zeta_set']) ** 2
                    )

        elif self.control_mode == 'position_global':
            cost = (1.0 * (self.model.x['x'] - self.model.tvp['x_set']) ** 2 +
                    1.0 * (self.model.x['y'] - self.model.tvp['y_set']) ** 2 +
                    1.0 * (self.model.x['z'] - self.model.tvp['z_set']) ** 2 +
                    1.0 * (self.model.x['psi'] - self.model.tvp['psi_set']) ** 2 +
                    1.0 * (self.model.x['w'] - self.model.tvp['w_set']) ** 2 +
                    1.0 * (self.model.x['zeta'] - self.model.tvp['zeta_set']) ** 2
                    )
        else:
            raise Exception('Control mode not available')

        # Set cost function
        self.mpc.set_objective(mterm=cost, lterm=cost)

        # Set input penalty & constraints
        self.input_mode = input_mode
        if self.input_mode == 'direct':
            self.mpc.bounds['lower', '_u', 'u_thrust'] = 0
            self.mpc.set_rterm(u_thrust=r_u, u_phi=r_u, u_theta=r_u, u_psi=r_u, u_w=1e12, u_zeta=1e-3)
        elif self.input_mode == 'rotor':
            self.mpc.set_rterm(u_f=r_u, u_r=r_u, u_l=r_u, u_b=r_u)
            self.mpc.bounds['lower', '_u', 'u_1'] = 0
            self.mpc.bounds['lower', '_u', 'u_2'] = 0
            self.mpc.bounds['lower', '_u', 'u_3'] = 0
            self.mpc.bounds['lower', '_u', 'u_4'] = 0
        else:
            raise Exception('Input mode not available')

        # Place limit on states
        self.mpc.bounds['lower', '_x', 'z'] = 0

        self.mpc.bounds['upper', '_x', 'phi'] = np.pi / 4
        self.mpc.bounds['upper', '_x', 'theta'] = np.pi / 4

        self.mpc.bounds['lower', '_x', 'phi'] = -np.pi / 4
        self.mpc.bounds['lower', '_x', 'theta'] = -np.pi / 4

    def update_setpoint(self, x=None, y=None, v_x=None, v_y=None, psi=None, z=None, w=None, zeta=None):
        """ Set the set-point variables.
        """

        # Set time
        T = self.dt * (len(w) - 1)
        tsim = np.arange(0, T + self.dt / 2, step=self.dt)

        # Set control setpoints
        if self.control_mode == 'velocity_body_level':  # control the body-level x & y velocities
            if (v_x is None) or (v_y is None):  # must set velocities
                raise Exception('x or y velocity not set')
            else:  # x & y don't matter, set to 0
                x = 0.0 * np.ones_like(tsim)
                y = 0.0 * np.ones_like(tsim)

        elif self.control_mode == 'position_global':  # control the global position
            if (x is None) or (y is None):  # must set positions
                raise Exception('x or y position not set')
            else:  # v_x & v_y don't matter, set to 0
                v_x = 0.0 * np.ones_like(tsim)
                v_y = 0.0 * np.ones_like(tsim)

        elif self.control_mode == 'position_velocity':  # control the global position
            if (x is None) or (y is None):  # must set positions
                raise Exception('x or y position not set')

            if (v_x is None) or (v_y is None):  # must set velocities
                raise Exception('x or y velocity not set')
        else:
            raise Exception('Control mode not available')

        # Define the set-points to follow
        setpoint = {'x': x,
                    'y': y,
                    'z': z,
                    'v_x': v_x,
                    'v_y': v_y,
                    'v_z': 0.0 * np.ones_like(tsim),
                    'phi': 0.0 * np.ones_like(tsim),
                    'theta': 0.0 * np.ones_like(tsim),
                    'psi': psi,
                    'omega_x': 0.0 * np.ones_like(tsim),
                    'omega_y': 0.0 * np.ones_like(tsim),
                    'omega_z': 0.0 * np.ones_like(tsim),
                    'w': w,
                    'zeta': zeta,

                    'm': self.params.Mm * np.ones_like(tsim),
                    'I_x': self.params.I_x * np.ones_like(tsim),
                    'I_y': self.params.I_y * np.ones_like(tsim),
                    'I_z': self.params.I_z * np.ones_like(tsim),
                    'C': self.params.C * np.ones_like(tsim),
                    }

        # Update the simulator set-point
        self.update_dict(setpoint, name='setpoint')

    def plot_trajectory(self, start_index=0, dpi=200, size_radius=None, nskip=0):
        """ Plot the trajectory.
        """

        fig, ax = plt.subplots(1, 1, figsize=(3 * 1, 3 * 1), dpi=dpi)

        x = self.y['x'][start_index:]
        y = self.y['y'][start_index:]
        heading = self.y['psi'][start_index:]
        time = self.time[start_index:]

        if size_radius is None:
            size_radius = 0.06 * np.max(np.array([util.range_of_vals(x), util.range_of_vals(y)]))

        ff.plot_trajectory(x, y, heading,
                           color=time,
                           ax=ax,
                           size_radius=size_radius,
                           nskip=nskip)

        fifi.mpl_functions.adjust_spines(ax, [])

# Coordinate transformation function
def z_function(X):
    # Old states as sympy variables
    x, y, z, v_x, v_y, v_z, phi, theta, psi, omega_x, omega_y, omega_z, w, zeta, m, I_x, I_y, I_z, C = X

    # Expressions for new states in terms of old states
    g = (v_x ** 2 + v_y ** 2) ** (1 / 2)  # ground speed magnitude
    beta = sp.atan(v_y / v_x)  # ground speed angle

    # Define new state vector
    z = [x, y, z, g, beta, v_z, phi, theta, psi, omega_x, omega_y, omega_z, w, zeta, m, I_x, I_y, I_z, C]
    return sp.Matrix(z)
