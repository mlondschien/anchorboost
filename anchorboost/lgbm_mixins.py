class LGBMMixin:

    higher_is_better = False

    def objective(self, f, data):
        """Objective function for LGBM."""
        return self.grad(f, data), self.hess(f, data)

    def score(self, f, data):
        """Score function for LGBM."""
        return (
            f"{self.name} ({self.gamma})",
            self.loss(f, data).mean(),
            self.higher_is_better,
        )
