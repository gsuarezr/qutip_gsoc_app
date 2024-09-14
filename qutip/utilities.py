"""
This module contains utility functions that are commonly needed in other
qutip modules.
"""

__all__ = ['n_thermal', 'clebsch', 'convert_unit',
           'fit_underdamped', 'fit_correlation']

from time import time

import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.optimize import curve_fit


def n_thermal(w, w_th):
    """
    Return the number of photons in thermal equilibrium for an harmonic
    oscillator mode with frequency 'w', at the temperature described by
    'w_th' where :math:`\\omega_{\\rm th} = k_BT/\\hbar`.

    Parameters
    ----------

    w : float or ndarray
        Frequency of the oscillator.

    w_th : float
        The temperature in units of frequency (or the same units as `w`).


    Returns
    -------

    n_avg : float or array

        Return the number of average photons in thermal equilibrium for a
        an oscillator with the given frequency and temperature.


    """

    if w_th <= 0:
        return np.zeros_like(w)

    w = np.array(w, dtype=float)
    result = np.zeros_like(w)
    non_zero = w != 0
    result[non_zero] = 1 / (np.exp(w[non_zero] / w_th) - 1)
    return result


def _factorial_prod(N, arr):
    arr[:int(N)] += 1


def _factorial_div(N, arr):
    arr[:int(N)] -= 1


def _to_long(arr):
    prod = 1
    for i, v in enumerate(arr):
        prod *= (i+1)**int(v)
    return prod


def clebsch(j1, j2, j3, m1, m2, m3):
    """Calculates the Clebsch-Gordon coefficient
    for coupling (j1,m1) and (j2,m2) to give (j3,m3).

    Parameters
    ----------
    j1 : float
        Total angular momentum 1.

    j2 : float
        Total angular momentum 2.

    j3 : float
        Total angular momentum 3.

    m1 : float
        z-component of angular momentum 1.

    m2 : float
        z-component of angular momentum 2.

    m3 : float
        z-component of angular momentum 3.

    Returns
    -------
    cg_coeff : float
        Requested Clebsch-Gordan coefficient.

    """
    if m3 != m1 + m2:
        return 0
    vmin = int(np.max([-j1 + j2 + m3, -j1 + m1, 0]))
    vmax = int(np.min([j2 + j3 + m1, j3 - j1 + j2, j3 + m3]))

    c_factor = np.zeros((int(j1 + j2 + j3 + 1)), np.int32)
    _factorial_prod(j3 + j1 - j2, c_factor)
    _factorial_prod(j3 - j1 + j2, c_factor)
    _factorial_prod(j1 + j2 - j3, c_factor)
    _factorial_prod(j3 + m3, c_factor)
    _factorial_prod(j3 - m3, c_factor)
    _factorial_div(j1 + j2 + j3 + 1, c_factor)
    _factorial_div(j1 - m1, c_factor)
    _factorial_div(j1 + m1, c_factor)
    _factorial_div(j2 - m2, c_factor)
    _factorial_div(j2 + m2, c_factor)
    C = np.sqrt((2.0 * j3 + 1.0)*_to_long(c_factor))

    s_factors = np.zeros(((vmax + 1 - vmin), (int(j1 + j2 + j3))), np.int32)
    # `S` and `C` are large integer,s if `sign` is a np.int32 it could oveflow
    sign = int((-1) ** (vmin + j2 + m2))
    for i, v in enumerate(range(vmin, vmax + 1)):
        factor = s_factors[i, :]
        _factorial_prod(j2 + j3 + m1 - v, factor)
        _factorial_prod(j1 - m1 + v, factor)
        _factorial_div(j3 - j1 + j2 - v, factor)
        _factorial_div(j3 + m3 - v, factor)
        _factorial_div(v + j1 - j2 - m3, factor)
        _factorial_div(v, factor)
    common_denominator = -np.min(s_factors, axis=0)
    numerators = s_factors + common_denominator
    S = sum([(-1)**i * _to_long(vec) for i, vec in enumerate(numerators)]) * \
        sign / _to_long(common_denominator)
    return C * S


# -----------------------------------------------------------------------------
# Functions for unit conversions
#
_e = 1.602176565e-19  # C
_kB = 1.3806488e-23   # J/K
_h = 6.62606957e-34   # Js

_unit_factor_tbl = {
    #   "unit": "factor that convert argument from unit 'unit' to Joule"
    "J": 1.0,
    "eV": _e,
    "meV": 1.0e-3 * _e,
    "GHz": 1.0e9 * _h,
    "mK": 1.0e-3 * _kB,
}


def convert_unit(value, orig="meV", to="GHz"):
    """
    Convert an energy from unit `orig` to unit `to`.

    Parameters
    ----------
    value : float / array
        The energy in the old unit.

    orig : str, {"J", "eV", "meV", "GHz", "mK"}, default: "meV"
        The name of the original unit.

    to : str, {"J", "eV", "meV", "GHz", "mK"}, default: "GHz"
        The name of the new unit.

    Returns
    -------
    value_new_unit : float / array
        The energy in the new unit.
    """
    if orig not in _unit_factor_tbl:
        raise TypeError("Unsupported unit %s" % orig)

    if to not in _unit_factor_tbl:
        raise TypeError("Unsupported unit %s" % to)

    return value * (_unit_factor_tbl[orig] / _unit_factor_tbl[to])


def convert_GHz_to_meV(w):
    """
    Convert an energy from unit GHz to unit meV.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.
    """
    # 1 GHz = 4.1357e-6 eV = 4.1357e-3 meV
    w_meV = w * 4.1357e-3
    return w_meV


def convert_meV_to_GHz(w):
    """
    Convert an energy from unit meV to unit GHz.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.
    """
    # 1 meV = 1.0/4.1357e-3 GHz
    w_GHz = w / 4.1357e-3
    return w_GHz


def convert_J_to_meV(w):
    """
    Convert an energy from unit J to unit meV.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.
    """
    # 1 eV = 1.602e-19 J
    w_meV = 1000.0 * w / _e
    return w_meV


def convert_meV_to_J(w):
    """
    Convert an energy from unit meV to unit J.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.
    """
    # 1 eV = 1.602e-19 J
    w_J = 0.001 * w * _e
    return w_J


def convert_meV_to_mK(w):
    """
    Convert an energy from unit meV to unit mK.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.
    """
    # 1 mK = 0.0000861740 meV
    w_mK = w / 0.0000861740
    return w_mK


def convert_mK_to_meV(w):
    """
    Convert an energy from unit mK to unit meV.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.
    """
    # 1 mK = 0.0000861740 meV
    w_meV = w * 0.0000861740
    return w_meV


def convert_GHz_to_mK(w):
    """
    Convert an energy from unit GHz to unit mK.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.
    """
    # h v [Hz] = kB T [K]
    # h 1e9 v [GHz] = kB 1e-3 T [mK]
    # T [mK] = 1e12 * (h/kB) * v [GHz]
    w_mK = w * 1.0e12 * (_h / _kB)
    return w_mK


def convert_mK_to_GHz(w):
    """
    Convert an energy from unit mK to unit GHz.

    Parameters
    ----------
    w : float / array
        The energy in the old unit.

    Returns
    -------
    w_new_unit : float / array
        The energy in the new unit.

    """
    w_GHz = w * 1.0e-12 * (_kB / _h)
    return w_GHz


def _version2int(version_string):
    str_list = version_string.split(
        "-dev")[0].split("rc")[0].split("a")[0].split("b")[0].split(
        "post")[0].split('.')
    return sum([int(d if len(d) > 0 else 0) * (100 ** (3 - n))
                for n, d in enumerate(str_list[:3])])


# -----------------------------------------------------------------------------
# Fitting utilities
# TODO clean up all of this -- generalize and remove reference to environments

# Gerardo: I don't know what you mean by Generalize

def _corr_approx(t, a, b, c, d=0):
    r"""
    This is the form of the correlation function to be used for fitting.

    Parameters
    ----------
    t : :obj:`np.array.` or float
        The times at which to evaluates the correlation function.
    a : list or :obj:`np.array.`
        A list describing the  real part amplitude of the correlation
        approximation.
    b : list or :obj:`np.array.`
        A list describing the decay of the correlation approximation.
    c : list or :obj:`np.array.`
        A list describing the oscillations of the correlation
        approximation.
    d:  A list describing the imaginary part amplitude of the correlation
        approximation, only used if the user selects if the full_ansatz
        flag from get_fit is True.
    """

    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    d = np.array(d)
    if (d == 0).all():
        d = np.zeros(a.shape)

    return np.sum(
        (a[:, None]+1j*d[:, None]) * np.exp(b[:, None] * t[None, :]) *
        np.exp(1j*c[:, None] * t[None, :]),
        axis=0,
    )

def fit_correlation(
    C,t, Nr=None, Ni=None,final_rmse=2e-5,lower=None,
    upper=None,sigma=None,guesses=None,full_ansatz=False):
    r"""
    Fit the correlation function with Ni exponential terms
    for the imaginary part of the correlation function and Nr for the real.
    If no number of terms is provided, this function determines the number
    of exponents based on reducing the normalized root mean squared
    error below a certain threshold.

    Parameters
    ----------
    Nr : optional, int
        Number of exponents to use for the real part.
        If set to None it is determined automatically.
    Ni : optional, int
        Number of exponents terms to use for the imaginary part.
        If set to None it is found automatically.
    final_rmse : float
        Desired normalized root mean squared error. Only used if Ni or Nr
        are not specified.
    lower : list
        lower bounds on the parameters for the fit. A list of size 4 when
        full_ansatz is True and of size 3 when it is false,each value
        represents the lower bound for each parameter.

        The first and last terms describe the real and imaginary parts of
        the amplitude, the second the decay rate, and the third one the
        oscillation frequency. The lower bounds are considered to be
        the same for all Nr and Ni exponents. for example

        lower=[0,-1,1,1]

        would bound the real part of the amplitude to be bigger than 0,
        the decay rate to be higher than -1, and the oscillation frequency
        to be bigger than 1, and the imaginary part of the amplitude to
        be greater than 1
    upper : list
        upper bounds on the parameters for the fit, the structure is the
        same as the lower keyword.
    sigma : float
        uncertainty in the data considered for the fit, all data points are
        considered to have the same uncertainty.
    guesses : list
        Initial guesses for the parameters. Same structure as lower and
        upper.
    full_ansatz : bool
        Indicates whether to use the function

        .. math::
            C(t)= \sum_{k}a_{k}e^{-b_{k} t}e^{i c_{k} t}

        for the fitting of the correlation function (when False, the
        default value)  this function gives us
        faster fits,usually it is not needed to tweek
        guesses, sigma, upper and lower as defaults work for most
        situations.  When set to True one uses the function

        .. math::
            C(t)= \sum_{k}(a_{k}+i d_{k})e^{-b_{k} t}e^{i c_{k} t}

        Unfortunately this gives us significantly slower fits and some
        tunning of the guesses,sigma, upper and lower are usually needed.
        On the other hand, it can lead to better fits with lesser exponents
        specially for anomalous spectral densities such that
        $Im(C(0))\neq 0$. When using this with default values if the fit
        takes too long you should input guesses, lower and upper bounds,
        if you are not sure what to set them to it is useful to use the
        output of fitting with the other option as guesses for the fit.



    Note: If one of lower, upper, sigma, guesses is None, all are discarded

    Returns
    -------
    1. A Bosonic Bath created with the fit parameters from the original
        correlation function (that was provided or interpolated).
    2. A dictionary containing the following information about the fit:
        * Nr :
            The number of terms used to fit the real part of the
            correlation function.
        * Ni :
            The number of terms used to fit the imaginary part of the
            correlation function.
        * fit_time_real :
            The time the fit of the real part of the correlation function
            took in seconds.
        * fit_time_imag :
            The time the fit of the imaginary part of the correlation
            function took in seconds.
        * rsme_real :
            Normalized mean squared error obtained in the fit of the real
            part of the correlation function.
        * rsme_imag :
            Normalized mean squared error obtained in the fit of the
            imaginary part of the correlation function.
        * params_real :
            The fitted parameters (3N parameters) for the real part of the
            correlation function, it contains three lists one for each
            parameter, each list containing N terms.
        * params_imag :
            The fitted parameters (3N parameters) for the imaginary part
            of the correlation function, it contains three lists one for
            each parameter, each list containing N terms.
        * summary :
            A string that summarizes the information about the fit.
        """
    if full_ansatz:
        num_params = 4
    else:
        num_params = 3
    if callable(C):
        C=C(t)
    # Fit real part
    start_real = time()
    rmse_real, params_real = _run_fit(
        lambda *args: np.real(_corr_approx(*args)),
        y=np.real(C), x=t, final_rmse=final_rmse,
        default_guess_scenario="correlation_real", N=Nr, sigma=sigma,
        guesses=guesses, lower=lower, upper=upper, n=num_params)
    end_real = time()

    # Fit imaginary part
    start_imag = time()
    rmse_imag, params_imag = _run_fit(
        lambda *args: np.imag(_corr_approx(*args)),
        y=np.imag(C), x=t, final_rmse=final_rmse,
        default_guess_scenario="correlation_imag", N=Ni, sigma=sigma,
        guesses=guesses, lower=lower, upper=upper, n=num_params)
    end_imag = time()

    # Calculate Fit Times
    fit_time_real = end_real - start_real
    fit_time_imag = end_imag - start_imag

    # Generate summary
    Nr = len(params_real[0])
    Ni = len(params_imag[0])
    full_summary = _two_column_summary(
        params_real, params_imag, fit_time_real, fit_time_imag, Nr, Ni,
        rmse_imag, rmse_real, n=num_params)

    fitInfo = {"Nr": Nr, "Ni": Ni,
                "fit_time_real": fit_time_real,
                "fit_time_imag": fit_time_imag,
                "rmse_real": rmse_real, "rmse_imag": rmse_imag,
                "params_real": params_real,
                "params_imag": params_imag, "summary": full_summary}
    ckAR, vkAR, ckAI, vkAI = _generate_correlation_exponents(
        params_real, params_imag, n=num_params)
    return ckAR, vkAR, ckAI, vkAI, fitInfo

def _generate_correlation_exponents(params_real, params_imag, n=3):
    """
    Calculate the Matsubara coefficients and frequencies for the
    fitted underdamped oscillators and generate the corresponding bosonic
    bath.

    Parameters
    ----------
    params_real : :obj:`np.array.`
        array of shape (N,3) where N is the number of fitted terms
        for the real part.
    params_imag : np.imag
        array of shape (N,3) where N is the number of fitted terms
        for the imaginary part.

    Returns
    -------
    A bosonic Bath constructed from the fitted exponents.
    """
    if n == 4:
        a, b, c, d = params_real
        a2, b2, c2, d2 = params_imag
    else:
        a, b, c = params_real
        a2, b2, c2 = params_imag
        d = np.zeros(a.shape, dtype=int)
        d2 = np.zeros(a2.shape, dtype=int)

    # the 0.5 is from the cosine
    ckAR = [(x + 1j*y)*0.5 for x, y in zip(a, d)]
    # extend the list with the complex conjugates:
    ckAR.extend(np.conjugate(ckAR))
    vkAR = [-x - 1.0j * y for x, y in zip(b, c)]
    vkAR.extend([-x + 1.0j * y for x, y in zip(b, c)])

    # the 0.5 is from the sine
    ckAI = [-1j*(x + 1j*y)*0.5 for x, y in zip(a2, d2)]

    # extend the list with the complex conjugates:
    ckAI.extend(np.conjugate(ckAI))
    vkAI = [-x - 1.0j * y for x, y in zip(b2, c2)]
    vkAI.extend([-x + 1.0j * y for x, y in zip(b2, c2)])

    return ckAR, vkAR, ckAI, vkAI




def _meier_tannor_SD(w, a, b, c):
    r"""
    Underdamped spectral density used for fitting in Meier-Tannor form
    (see Eq. 38 in the BoFiN paper, DOI: 10.1103/PhysRevResearch.5.013181)
    or the get_fit method.

    Parameters
    ----------
    w : :obj:`np.array.`
        The frequency of the spectral density
    a : :obj:`np.array.`
        Array of coupling constants ($\alpha_i^2$)
    b : :obj:`np.array.`
        Array of cutoff parameters ($\Gamma'_i$)
    c : :obj:`np.array.`
        Array of resonant frequencies ($\Omega_i$)
    """

    return sum((2 * ai * bi * w
                / ((w + ci) ** 2 + bi ** 2)
                / ((w - ci) ** 2 + bi ** 2))
                for ai, bi, ci in zip(a, b, c))

def fit_underdamped(J,w,
    N=None,
    Nk=None,
    final_rmse=5e-6,
    lower=None,
    upper=None,
    sigma=None,
    guesses=None,
):
    r"""
    Provides a fit to the spectral density with N underdamped oscillator
    baths. N can be determined automatically based on reducing the
    normalized root mean squared error below a certain threshold.

    Parameters
    ----------
    N : optional, int
        Number of underdamped oscillators to use.
        If set to None, it is determined automatically.
    lower: list
        The lower bounds are considered to be the same for all N modes.
        For example,

        lower=[0,-1,2]

        would bound the coupling to be bigger than 0, the cutoff frequency
        to be higher than 1, and the central frequency to be bigger than 2

    upper : list
        Upper bounds on the parameters for the fit, the structure is the
        same as the lower keyword.
    sigma : float
        Uncertainty in the data considered for the fit, all data points are
        considered to have the same uncertainty.
    guesses : list
        Initial guesses for the parameters. Same structure as lower and
        upper.

    Note: If one of lower, upper, sigma, guesses is None, all are discarded

    Returns
    -------
    1. A Bosonic Bath created with the fit parameters for the original
        spectral density function (that was provided or interpolated)
    2. A dictionary containing the following information about the fit:
        * fit_time:
            The time the fit took in seconds.
        * rsme:
            Normalized mean squared error obtained in the fit.
        * N:
            The number of terms used for the fit.
        * params:
            The fitted parameters (3N parameters), it contains three lists
            one for each parameter, each list containing N terms.
        * Nk:
            The number of exponents used to construct the bosonic bath.
        * summary:
            A string that summarizes the information of the fit.
    """
    if callable(J):
        J=J(w)

    start = time()
    rmse, params = _run_fit(
        _meier_tannor_SD, J, w,
        final_rmse, default_guess_scenario="Spectral Density", N=N,
        sigma=sigma, guesses=guesses, lower=lower, upper=upper)
    end = time()

    fit_time = end - start
    spec_n = len(params[0])
    #result = self._generate_bath(params, Nk)
    summary = _gen_summary(
        fit_time, rmse, N, "The Spectral Density", params)
    fitInfo = {
        "fit_time": fit_time, "rmse": rmse, "N": spec_n, "params": params,
        "Nk": Nk, "summary": summary}
    return params,fitInfo


def _pack(*args):
    """
    Pack parameter lists for fitting. In both use cases (spectral fit,
    correlation fit), the fit parameters are three arrays of equal length.
    """
    return np.concatenate(tuple(args))


def _unpack(params, n=3):
    """
    Unpack parameter lists for fitting. In the use cases (spectral fit/
    correlation fit), the fit parameters are three/four arrays of equal length.
    """
    num_params = len(params) // n
    zz = []
    for i in range(n):
        zz.append(params[i*num_params:(i+1)*num_params])
    return zz


def _leastsq(func, y, x, guesses=None, lower=None,
             upper=None, sigma=None, n=3):
    """
    Performs nonlinear least squares to fit the function func to x and y.

    Parameters
    ----------
    func : function
        The function we wish to fit.
    x : np.array
        a numpy array containing the independent variable used for the fit.
    y : :obj:`np.array.`
        a numpy array containing the dependent variable we use for the fit.
    guesses : list
        Initial guess for the parameters.
    lower : list
        lower bounds on the parameters for the fit.
    upper : list
        upper bounds on the parameters for the fit.
    sigma : float
        uncertainty in the data considered for the fit
    n: int
        number of free parameters to be fitted, used for reshaping of the
        parameters array across the different functions
    Returns
    -------
    params: list
        It returns the fitted parameters.
    """

    sigma = [sigma] * len(x)
    params, _ = curve_fit(
        lambda x, *params: func(x, *_unpack(params, n)),
        x,
        y,
        p0=guesses,
        bounds=(lower, upper),
        sigma=sigma,
        maxfev=int(1e9),
        method="trf",
    )

    return _unpack(params, n)


def _rmse(func, x, y, *args):
    """
    Calculates the normalized root mean squared error for fits
    from the fitted parameters a, b, c.

    Parameters
    ----------
    func : function
        The approximated function for which we want to compute the rmse.
    x: :obj:`np.array.`
        a numpy array containing the independent variable used for the fit.
    y: :obj:`np.array.`
        a numpy array containing the dependent variable used for the fit.
    a, b, c : list
        fitted parameters.

    Returns
    -------
    rmse: float
        The normalized root mean squared error for the fit, the closer
        to zero the better the fit.
    """
    yhat = func(x, *args)
    rmse = np.sqrt(np.mean((yhat - y) ** 2) / len(y)) / \
        (np.max(y) - np.min(y))
    return rmse


def _fit(func, corr, t, N, default_guess_scenario='',
         guesses=None, lower=None, upper=None, sigma=None, n=3):
    """
    Performs a fit the function func to t and corr, with N number of
    terms in func, the guesses,bounds and uncertainty can be determined
    by the user.If none is provided it constructs default ones according
    to the label.

    Parameters
    ----------
    func : function
        The function we wish to fit.
    corr : :obj:`np.array.`
        a numpy array containing the dependent variable used for the fit.
    t : :obj:`np.array.`
        a numpy array containing the independent variable used for the fit.
    N : int
        The number of modes / baths used for the fitting.
    default_guess_scenario : str
        Determines how the default guesses and bounds are chosen (in the case
        guesses or bounds are not specified). May be 'correlation_real',
        'correlation_imag' or any other string. Any other string will use
        guesses and bounds designed for the fitting of spectral densities.
    guesses : list
        Initial guess for the parameters.
    lower : list
        lower bounds on the parameters for the fit.
    upper: list
        upper bounds on the parameters for the fit.
    sigma: float
        uncertainty in the data considered for the fit.
    n: int
        The Number of variables used in the fit
    Returns
    -------
    params:
        It returns the fitted parameters as a list.
    rmse:
        It returns the normalized mean squared error from the fit
    """

    if None not in (guesses, lower, upper, sigma):
        guesses = _reformat(guesses, N)
        lower = _reformat(lower, N)
        upper = _reformat(upper, N)
    else:
        tempguess, templower, tempupper, tempsigma = _default_guess_scenarios(
            corr, t, default_guess_scenario, N, n)
        guesses = tempguess
        lower = templower
        upper = tempupper
        sigma = tempsigma
        if (tempupper == templower).all() and (tempguess == tempupper).all():
            return 0, _unpack(templower, n)
    if not ((len(guesses) == len(lower)) and (len(guesses) == len(upper))):
        raise ValueError("The shape of the provided fit parameters is \
                         not consistent")
    args = _leastsq(func, corr, t, sigma=sigma, guesses=guesses,
                    lower=lower, upper=upper, n=n)
    rmse = _rmse(func, t, corr, *args)
    return rmse, args


def _default_guess_scenarios(corr, t, default_guess_scenario, N, n):
    corr_max = abs(max(corr, key=np.abs))
    tempsigma = 1e-2

    if corr_max == 0:
        # When the target function is zero
        tempguesses = _pack(
            [0] * N, [0] * N, [0] * N, [0] * N)
        templower = tempguesses
        tempupper = tempguesses
        return tempguesses, templower, tempupper, tempsigma
    wc = t[np.argmax(corr)]

    if "correlation" in default_guess_scenario:
        if n == 4:
            templower = _pack([-100*corr_max] * N, [-np.inf] * N, [-1]
                              * N, [-100*corr_max] * N)
        else:
            templower = _pack([-20 * corr_max] * N, [-np.inf] * N, [0.0] * N)

    if default_guess_scenario == "correlation_real":
        if n == 4:
            wc = np.inf
            tempguesses = _pack([corr_max] * N, [-100*corr_max]
                                * N, [0] * N, [0] * N)
            tempupper = _pack([100*corr_max] * N, [0] * N,
                              [1] * N, [100*corr_max] * N)
        else:
            tempguesses = _pack([corr_max] * N, [-wc] * N, [wc] * N)
            tempupper = _pack([20 * corr_max] * N, [0.1] * N, [np.inf] * N)
    elif default_guess_scenario == "correlation_imag":
        if n == 4:
            wc = np.inf
            tempguesses = _pack([0] * N, [-10*corr_max] * N, [0] * N, [0] * N)
            tempupper = _pack([100*corr_max] * N, [0] * N,
                              [2] * N, [100*corr_max] * N)
        else:
            tempguesses = _pack([-corr_max] * N, [-10*corr_max] * N, [1] * N)
            tempupper = _pack([10 * corr_max] * N, [0] * N, [np.inf] * N)
    else:
        tempguesses = _pack([corr_max] * N, [wc] * N, [wc] * N)
        templower = _pack([-100 * corr_max] * N,
                          [0.1 * wc] * N, [0.1 * wc] * N)
        tempupper = _pack([100 * corr_max] * N,
                          [100 * wc] * N, [100 * wc] * N)
    return tempguesses, templower, tempupper, tempsigma


def _reformat(guess, N):
    """
    This function reformats the user provided guesses into the format
    appropiate for fitting, if the user did not provide it the defaults are
    assigned
    """
    guesses = [[i]*N for i in guess]
    guesses = [x for xs in guesses for x in xs]
    guesses = _pack(guesses)
    return guesses


def _run_fit(funcx, y, x, final_rmse, default_guess_scenario='', N=None, n=3,
             **kwargs):
    """
    It iteratively tries to fit the funcx to y on the interval x.
    If N is provided the fit is done with N modes, if it is
    None then this automatically finds the smallest number of modes that
    whose mean squared error is smaller than final_rmse.

    Parameters
    ----------
    funcx : function
        The function we wish to fit.
    y : :obj:`np.array.`
        The function used for the fitting.
    x : :obj:`np.array.`
        a numpy array containing the independent variable used for the fit.
    final_rmse : float
        Desired normalized root mean squared error.
    default_guess_scenario : str
        Determines how the default guesses and bounds are chosen (in the case
        guesses or bounds are not specified). May be 'correlation_real',
        'correlation_imag' or any other string. Any other string will use
        guesses and bounds designed for the fitting of spectral densities.
    N : optional , int
        The number of modes used for the fitting, if not provided starts at
        1 and increases until a desired RMSE is satisfied.
    sigma: float
        uncertainty in the data considered for the fit.
    guesses : list
        Initial guess for the parameters.
    lower : list
        lower bounds on the parameters for the fit.
    upper: list
        upper bounds on the parameters for the fit.

    Returns
    -------
    params:
        It returns the fitted parameters as a list.
    rmse:
        It returns the normalized mean squared error from the fit
    """

    if N is None:
        N = 2
        iterate = True
    else:
        iterate = False
    rmse1 = np.inf

    while rmse1 > final_rmse:
        rmse1, params = _fit(
            funcx, y, x, N, default_guess_scenario, n=n, **kwargs)
        N += 1
        if not iterate:
            break

    return rmse1, params


def _gen_summary(time, rmse, N, label, params,
                 columns=['lam', 'gamma', 'w0']):
    """Generates a summary of fits by nonlinear least squares"""
    if len(columns) == 3:
        summary = (f"Result of fitting {label} "
                   f"with {N} terms: \n \n {'Parameters': <10}|"
                   f"{columns[0]: ^10}|{columns[1]: ^10}|{columns[2]: >5} \n ")
        for k in range(len(params[0])):
            summary += (
                f"{k+1: <10}|{params[0][k]: ^10.2e}|{params[1][k]:^10.2e}|"
                f"{params[2][k]:>5.2e}\n ")
    else:
        summary = (
            f"Result of fitting {label} "
            f"with {N} terms: \n \n {'Parameters': <10}|"
            f"{columns[0]: ^10}|{columns[1]: ^10}|{columns[2]: ^10}"
            f"|{columns[3]: >5} \n ")
        for k in range(len(params[0])):
            summary += (
                f"{k+1: <10}|{params[0][k]: ^10.2e}|{params[1][k]:^10.2e}"
                f"|{params[2][k]:^10.2e}|{params[3][k]:>5.2e}\n ")
    summary += (f"\nA  normalized RMSE of {rmse: .2e}"
                f" was obtained for the {label}\n")
    summary += f" The current fit took {time: 2f} seconds"
    return summary


def _two_column_summary(
        params_real, params_imag, fit_time_real, fit_time_imag, Nr, Ni,
        rmse_imag, rmse_real, n=3):
    # Generate nicely formatted summary with two columns for correlations
    columns = ["a", "b", "c"]
    if n == 4:
        columns.append("d")
    summary_real = _gen_summary(
        fit_time_real,
        rmse_real,
        Nr,
        "The Real Part Of  \n the Correlation Function", params_real,
        columns=columns)
    summary_imag = _gen_summary(
        fit_time_imag,
        rmse_imag,
        Ni,
        "The Imaginary Part \n Of the Correlation Function", params_imag,
        columns=columns)

    full_summary = "Fit correlation class instance: \n \n"
    lines_real = summary_real.splitlines()
    lines_imag = summary_imag.splitlines()
    max_lines = max(len(lines_real), len(lines_imag))
    # Fill the shorter string with blank lines
    lines_real = lines_real[:-1] + (max_lines - len(lines_real)
                                    ) * [""] + [lines_real[-1]]
    lines_imag = lines_imag[:-1] + (max_lines - len(lines_imag)
                                    ) * [""] + [lines_imag[-1]]
    # Find the maximum line length in each column
    max_length1 = max(len(line) for line in lines_real)
    max_length2 = max(len(line) for line in lines_imag)

    # Print the strings side by side with a vertical bar separator
    for line1, line2 in zip(lines_real, lines_imag):
        formatted_line1 = f"{line1:<{max_length1}} |"
        formatted_line2 = f"{line2:<{max_length2}}"
        full_summary += formatted_line1 + formatted_line2 + "\n"
    return full_summary
