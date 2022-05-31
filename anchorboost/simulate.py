import numpy as np


def simulate(f, seed=0):
    rng = np.random.RandomState(seed)

    n = 10000
    a = rng.normal(size=(n, 2))
    h = rng.normal(size=(n, 1))
    x_noise = 0.5 * rng.normal(size=(n, 10))
    x = x_noise + np.repeat(a[:, 0] + a[:, 1] + 2 * h[:, 0], 10).reshape((n, 10))

    y_noise = 0.25 * rng.normal(size=n)
    y = f(x[:, 1], x[:, 2]) - 2 * a[:, 0] + 3 * h[:, 0] + y_noise

    return x, y, a


def f2(x2, x3):
    return x2 + x3 + (x2 <= 0) + (x2 <= -0.5) * (x3 <= 1)
