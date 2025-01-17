import numpy as np


class MultiClassificationMixin:
    def __init__(self, n_classes):
        self.n_classes = n_classes
        self.factor = (n_classes - 1) / n_classes

    def init_score(self, y):
        """Initial score for LGBM.

        Parameters
        ----------
        y: np.ndarray of dimension (n,)
            Vector with true labels in (0, ..., n_classes - 1).

        Returns
        -------
        np.ndarray of dimension (n * n_classes,)
            Initial scores for LGBM. Note that this is flattened.
        """
        unique_values, unique_counts = np.unique(y, return_counts=True)
        assert len(unique_values) == self.n_classes
        assert (sorted(unique_values) == unique_values).all()

        odds = np.array(unique_counts) / np.sum(unique_counts)
        return np.log(np.tile(odds, (len(y), 1)).flatten("F"))

    def loss(self, f, data):
        """Multi-class negative log-likelihood loss.

        Parameters
        ----------
        f: np.ndarray of dimension (n * n_classes,)
            Vector with scores.
        data: lgbm.Dataset
            LGBM dataset with labels of dimension (n,) in (0, ..., n_classes - 1).

        Returns
        -------
        np.ndarray of dimension (n,).
            Loss.
        """
        y = data.get_label()
        f = f.reshape((-1, self.n_classes), order="F")  # (n, n_classes)
        f = f - np.max(f, axis=1)[:, np.newaxis]  # normalize f to avoid overflow
        log_divisor = np.log(np.sum(np.exp(f), axis=1))
        return -f[self._indices(y)] + log_divisor

    def _indices(self, y):
        return (np.arange(len(y)), y.astype(int))

    def predictions(self, f):
        """Compute probability predictions from scores via softmax.

        Parameters
        ----------
        f: np.ndarray of dimension (n * n_classes,).]
            Vector with scores.

        Returns
        -------
        np.ndarray of dimension (n, n_classes)
            Vector with probabilities.
        """
        f = f.reshape((-1, self.n_classes), order="F")  # (n, n_classes)
        f = f - np.max(f, axis=1)[:, np.newaxis]  # normalize f to avoid overflow
        predictions = np.exp(f)
        predictions /= np.sum(predictions, axis=1)[:, np.newaxis]
        return predictions

    def grad(self, f, data):
        """
        Gradient of the multi-class log-likelihood loss.

        Parameters
        ----------
        f: np.ndarray of dimension (n * n_classes,)
            Vector with scores.
        data: lgbm.Dataset
            LGBM dataset with labels of dimension (n,) in (0, ..., n_classes - 1).
        """
        y = data.get_label()
        predictions = self.predictions(f)
        predictions[self._indices(y)] -= 1

        return predictions.flatten("F")

    def hess(self, f, data):
        """
        Diagonal of the Hessian of the multi-class log-likelihood loss.

        Parameters
        ----------
        f: np.ndarray of dimension (n * n_classes,)
            Vector with scores.
        data: lgbm.Dataset
            LGBM dataset with labels of dimension (n,) in (0, ..., n_classes - 1).
        """
        predictions = self.predictions(f).flatten("F")
        return 1 / self.factor * predictions * (1.0 - predictions)


class ClassificationMixin:
    def init_score(self, y):
        """Initial score for LGBM.

        Parameters
        ----------
        y: np.ndarray of dimension (n,)
            Vector with true labels in (0, 1).

        Returns
        -------
        np.ndarray of length n
            Initial scores for LGBM.
        """
        p = np.sum(y) / len(y)
        return np.ones(len(y)) * np.log(p / (1 - p))

    def loss(self, f, data):
        """Two-class negative log-likelihood loss.

        Parameters
        ----------
        f: np.ndarray of dimension (n)
            Vector with scores.
        data: lgbm.Dataset
            LGBM dataset with labels of dimension (n,) in (0, 1).

        Returns
        -------
        np.ndarray of dimension (n,)
            Loss.
        """
        return np.log(1 + np.exp((-2 * data.get_label() + 1) * f))

    def predictions(self, f):
        """Compute probability predictions from scores via softmax.

        Parameters
        ----------
        f: np.ndarray of dimension (n,)
            Vector with scores.

        Returns
        -------
        np.ndarray of dimension (n,)
            Vector with probabilities.
        """
        return 1 / (1 + np.exp(-f))

    def grad(self, f, data):
        """
        Gradient of the two-class log-likelihood loss.

        Parameters
        ----------
        f: np.ndarray of dimension (n,)
            Vector with scores.
        data: lgbm.Dataset
            LGBM dataset with labels of dimension (n,) in (0, 1).
        """
        return self.predictions(f) - data.get_label()

    def hess(self, f, data):
        """
        Diagonal of the Hessian of the multi-class log-likelihood loss.

        Parameters
        ----------
        f: np.ndarray of dimension (n,)
            Vector with scores.
        data: lgbm.Dataset
            LGBM dataset with labels of dimension (n,) in (0, 1).
        """
        predictions = self.predictions(f)
        return predictions * (1.0 - predictions)
