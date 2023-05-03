import numpy as np

from anchorboost.anchor_mixins import AnchorMixin
from anchorboost.classification_mixins import (
    ClassificationMixin,
    MultiClassificationMixin,
)
from anchorboost.lgbm_mixins import LGBMMixin
from anchorboost.regression_mixins import RegressionMixin


class AnchorKookClassificationObjective(AnchorMixin, ClassificationMixin, LGBMMixin):
    def __init__(self, gamma, center_residuals=False):
        self.gamma = gamma
        self.center_residuals = center_residuals
        self.name = "kook anchor classification"

    def residuals(self, f, data):
        residuals = self.predictions(f) - data.get_label()
        if self.center_residuals:
            residuals -= residuals.mean()
        return residuals

    def loss(self, f, data):
        return (
            super().loss(f, data)
            + (self.gamma - 1) * self._proj(data.anchor, self.residuals(f, data)) ** 2
        )

    def grad(self, f, data):
        predictions = self.predictions(f)
        proj_residuals = self._proj(data.anchor, self.residuals(f, data))

        if self.center_residuals:
            proj_residuals -= proj_residuals.mean()

        return super().grad(f, data) + 2 * (
            self.gamma - 1
        ) * proj_residuals * predictions * (1 - predictions)


class AnchorKookMultiClassificationObjective(
    AnchorMixin, MultiClassificationMixin, LGBMMixin
):
    def __init__(self, gamma, n_classes, center_residuals=False):
        self.gamma = gamma
        self.center_residuals = center_residuals
        super().__init__(n_classes)
        self.name = "kook anchor multi-classification"

    def residuals(self, f, data):
        predictions = self.predictions(f)
        predictions[self._indices(data.get_label())] -= 1
        if self.center_residuals:
            predictions -= predictions.mean(axis=0, keepdims=True)

        return predictions.flatten("F")

    def loss(self, f, data):
        residuals = self.residuals(f, data).reshape((-1, self.n_classes), order="F")
        proj_residuals = self._proj(data.anchor, residuals)
        # Multiply with factor to align two-class classification with
        # AnchorKookClassificationObjective
        return super().loss(f, data) + self.factor * (self.gamma - 1) * np.sum(
            proj_residuals**2, axis=1
        )

    def grad(self, f, data):
        residuals = self.residuals(f, data).reshape((-1, self.n_classes), order="F")
        proj_residuals = self._proj(data.anchor, residuals)

        if self.center_residuals:
            proj_residuals -= proj_residuals.mean(axis=0, keepdims=True)

        predictions = self.predictions(f)
        proj_residuals -= np.sum(proj_residuals * predictions, axis=1, keepdims=True)
        # Multiply with factor to align two-class classification with
        # AnchorKookClassificationObjective
        anchor_grad = 2 * self.factor * (self.gamma - 1) * predictions * proj_residuals
        return super().grad(f, data) + anchor_grad.flatten("F")


class AnchorLiuClassificationObjective(AnchorMixin, ClassificationMixin, LGBMMixin):
    def __init__(self, gamma):
        self.gamma = gamma
        self.name = "liu anchor classification"

    def residuals(self, f, data):
        y = 2 * data.get_label() - 1
        return -f + y * (1 + np.exp(-y * f)) * np.log1p(np.exp(y * f))

    def loss(self, f, data):
        if self.gamma == 1:
            return super().loss(f, data)

        return (
            super().loss(f, data)
            + (self.gamma - 1) * self._proj(data.anchor, self.residuals(f, data)) ** 2
        )

    def grad(self, f, data):
        if self.gamma == 1:
            return super().grad(f, data)

        y = 2 * data.get_label() - 1
        residuals = self.residuals(f, data)
        proj_residuals = self._proj(data.anchor, residuals)

        return super().grad(f, data) - 2 * (self.gamma - 1) * proj_residuals * np.exp(
            -y * f
        ) * np.log1p(np.exp(y * f))


class AnchorHSICRegressionObjective(AnchorMixin, RegressionMixin, LGBMMixin):
    def __init__(self, gamma, n_components=100, random_fourier_features_seed=0):
        self.gamma = gamma
        self.n_components = n_components
        self.random_fourier_features_seed = random_fourier_features_seed
        self.name = "HSIC anchor regression"

    def residuals(self, f, data):
        return data.get_label() - f

    def loss(self, f, data):
        if self.gamma == 1:
            return super().loss(f, data)

        fourier_residuals, _ = self._fourier_residuals(f, data)
        proj_residuals = self._proj(data.anchor, fourier_residuals)
        return (
            super().loss(f, data) + (self.gamma - 1) * (proj_residuals**2).sum(axis=1)
        ) / max(self.gamma, 1)

    def grad(self, f, data):
        if self.gamma == 1:
            return super().grad(f, data)

        fourier_residuals, fourier_derivative = self._fourier_residuals(f, data)
        derivative = self._proj(data.anchor, fourier_residuals) * fourier_derivative

        return (
            super().grad(f, data) - 2 * (self.gamma - 1) * derivative.sum(axis=1)
        ) / max(self.gamma, 1)

    def _fourier_residuals(self, f, data):
        rng = np.random.RandomState(self.random_fourier_features_seed)
        residuals = self.residuals(f, data)
        random_weights = rng.normal(size=(1, self.n_components))
        offset = rng.uniform(size=(1, self.n_components)) * 2 * np.pi
        weight_matrix = residuals.reshape(-1, 1) * random_weights + offset

        fourier_residuals = np.cos(weight_matrix) * np.sqrt(2 / self.n_components)
        fourier_derivative = (
            -np.sin(weight_matrix) * random_weights * np.sqrt(2 / self.n_components)
        )
        return fourier_residuals, fourier_derivative


class AnchorRegressionObjective(AnchorMixin, RegressionMixin, LGBMMixin):
    def __init__(self, gamma):
        self.gamma = gamma
        self.name = "anchor regression"

    def residuals(self, f, data):
        return data.get_label() - f

    def loss(self, f, data):
        if self.gamma == 1:
            return super().loss(f, data)

        return (
            super().loss(f, data)
            + (self.gamma - 1) * self._proj(data.anchor, self.residuals(f, data)) ** 2
        ) / max(self.gamma, 1)

    def grad(self, f, data):
        if self.gamma == 1:
            return super().grad(f, data)

        proj_residuals = self._proj(data.anchor, self.residuals(f, data))
        return (super().grad(f, data) - 2 * (self.gamma - 1) * proj_residuals) / max(
            self.gamma, 1
        )
