"""Compiled and parallelized functions."""

import warnings
import numpy as np
from numba import jit


# Disable bad division warning when summing up squares
warnings.filterwarnings("ignore", category=RuntimeWarning)


@jit(nopython=True, parallel=True)
def loop_u(u, n_h, X_v, U, U_no_noise, X, mu_lhs, u_noise=0., x_noise=0.):
    """Return the inputs/snapshots matrices from parallel computation."""
    # pylint: disable=not-an-iterable


    for i in range(mu_lhs.shape[0]):
        X_v[i, :] = mu_lhs[i]
        U_i_no_noise = u(X, 0, X_v[i, :]).reshape((n_h,))
        if x_noise > 0.:
            # X_v[i, :] += x_noise*np.std(X_v[i, :])*np.random.randn(X_v[i, :].shape[0])
            X_v[i, :] += np.random.normal(0., x_noise*np.std(X_v[i, :]), X_v.shape[1])
        U_i = u(X, 0, X_v[i, :]).reshape((n_h,))
        if u_noise > 0.:
            U_i += u_noise*np.std(U_i)*np.random.randn(U_i.shape[0])
        U[:, i] = U_i
        U_no_noise[:, i] = U_i_no_noise
    U_struct = U
    return X_v, U, U_struct, U_no_noise


@jit(nopython=True, parallel=True)
def loop_u_t(u, n_t, n_v, n_xyz, n_h,
             X_v, U, U_no_noise, U_struct, X, mu_lhs, t_min, t_max, u_noise=0., x_noise=0.):
    """Return the inputs/snapshots matrices from parallel computation (w/ t)."""
    # Creating the time steps
    t = np.linspace(t_min, t_max, n_t)
    tT = t.reshape((n_t, 1))
    # pylint: disable=not-an-iterable
    for i in range(mu_lhs.shape[0]):
        # Getting the snapshot times indices
        s = n_t * i
        e = n_t * (i + 1)

        # Setting the regression inputs (t, mu)
        mu_i_no_noise = mu_lhs[i, :]
        mu_i = mu_lhs[i, :]
        dev = np.std(mu_i)
        if dev == 0.:
            dev = mu_i[0]
        mu_i = mu_i_no_noise + \
               x_noise*dev*np.random.randn(mu_i.shape[0])
        X_v[s:e, :] = np.hstack((tT, np.ones_like(tT)*mu_i))

        # Calling the analytical solution function
        Ui = np.zeros((n_v, n_xyz, n_t))
        Ui_no_noise = np.zeros((n_v, n_xyz, n_t))
        for j in range(n_t):
            Uij = u(X, t[j], mu_i)
            Uij_no_noise = u(X, t[j], mu_i_no_noise)
            if u_noise > 0.:
                Uij += u_noise*np.std(Uij)*np.random.randn(Uij.shape[0], Uij.shape[1])
            Ui[:, :, j] = Uij
            Ui_no_noise[:, :, j] = Uij_no_noise

        U[:, s:e] = Ui.reshape((n_h, n_t))
        U_no_noise[:, s:e] = Ui_no_noise.reshape((n_h, n_t))
        U_struct[:, :, i] = U[:, s:e]
    return X_v, U, U_struct, U_no_noise


@jit(nopython=True, parallel=True)
def lhs(n, samples):
    """Borrowed, parallelized __lhscentered() from pyDOE."""

    # Generate the intervals
    cut = np.linspace(0, 1, samples + 1)

    # Fill points uniformly in each interval
    u = np.random.rand(samples, n)
    a = cut[:samples]
    b = cut[1:samples + 1]
    rdpoints = np.zeros(u.shape)
    for j in range(n):
        rdpoints[:, j] = u[:, j]*(b-a) + a

    # Make the random pairings
    H = np.zeros(rdpoints.shape)
    for j in range(n):
        order = np.random.permutation(np.arange(samples))
        H[:, j] = rdpoints[order, j]

    return H
