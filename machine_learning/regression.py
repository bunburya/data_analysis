#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Callable, Sequence, Tuple, Union
import numpy as np

class NonConvergenceError(Exception): pass
class NoHypothesisError(Exception): pass

class BaseRegression:

    def __init__(self, features: Sequence[Sequence[float]], outputs: Sequence[float], scale_features=True):
        self.features = np.array([np.insert(np.array(row), 0, 1) for row in features])
        if scale_features:
            self.scaled = True
            self._scale_learning_features()
        else:
            self.scaled = False
        self.outputs = np.array(outputs)
        self.m, self.n = self.features.shape
        self.theta = None
        self.hypothesis = None
    
    @property
    def data(self):
        return zip(self.features, self.outputs)
    
    def _scale_learning_features(self):
        self.means = np.mean(self.features, axis=0)
        self.stds = np.std(self.features, axis=0)
        with np.errstate(divide='ignore', invalid='ignore'):
            self.features = (self.features - self.means) / self.stds
        self.features[:,0] = 1 # Set first parameter back to one as it shouldn't be scaled
    
    def scale_features(self, features: Sequence[float]) -> Sequence[float]:
        features = np.array(features)
        with np.errstate(divide='ignore', invalid='ignore'):
            scaled = (features - self.means) / self.stds
        scaled[0] = 1
        return scaled
    
    def get_prediction(self, features: Sequence[float], h: Callable[[np.ndarray], float] = None, add_x0: bool = True) -> float:
        features = np.array(features)
        if h is None:
            if self.hypothesis is None:
                raise NoHypothesisError('No hypothesis function available to make prediction. Generate one by calling the gradient_descent method (with the "store_results" argument set to True).')
            else:
                h = self.hypothesis
        if add_x0:
            features = np.insert(features, 0, 1)
        if self.scaled:
            features = self.scale_features(features)
        return h(features)
    
    def get_hypothesis(self, theta: np.ndarray) -> Callable:
        raise NotImplementedError('Need to implement hypothesis function.')

    def cost_function(self, h: Callable) -> float:
        raise NotImplementedError('Need to implement cost function.')
    
    def delta(self, theta: np.ndarray) -> np.ndarray:
        raise NotImplementedError('Need to implement delta function.')
    
    def gradient_descent(self, a: float, t_start: np.ndarray = None, store_results: bool = True,
                        convergence_threshold: float = 1e-6, iterations: int = None) -> Tuple[np.ndarray, Callable[[float], int]]:
        if iterations is not None:
            convergence_threshold = None
        if t_start is None:
            theta = np.zeros((self.n, 1))
        else:
            theta = t_start
        num_steps = 0
        h = self.get_hypothesis(theta)
        old_cost = self.cost_function(theta)
        while True:
            num_steps += 1
            delta = self.delta(theta)
            theta = theta - ((a / self.m) * delta)
            new_h = self.get_hypothesis(theta)
            new_cost = self.cost_function(theta)
            if new_cost > old_cost:
                raise NonConvergenceError(f'Failed to converge: latest cost ({new_cost}) is greater than previous cost ({old_cost}) at step {num_steps}.')
            if (
                ((convergence_threshold is not None) and ((old_cost - new_cost) < convergence_threshold)) or
                ((iterations is not None) and (num_steps == iterations))
            ):
                if store_results:
                    self.theta = theta
                    self.hypothesis = h
                return theta, h, num_steps
            old_cost = new_cost
            h = new_h
