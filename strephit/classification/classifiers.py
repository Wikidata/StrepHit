from collections import defaultdict

from sklearn.base import BaseEstimator, ClassifierMixin
import numpy as np
from importlib import import_module


class FeatureSelectedClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self, model_cls='sklearn.linear_model.LogisticRegression',
                 selector_column=None, model_args=None):
        self.model_cls = model_cls
        self.selector_column = selector_column
        self.model_args = model_args

    def get_classifier(self, i):
        if i not in self.classifiers_:
            self.classifiers_[i] = self.model_cls(**(self.model_args or {}))
        return self.classifiers_[i]

    def _setup(self):
        if isinstance(self.model_cls, basestring):
            path = self.model_cls.split('.')
            module = '.'.join(path[:-1])
            self.model_cls = getattr(import_module(module), path[-1])

        if self.selector_column is not None:
            self.classifiers_ = {}
        else:
            self.default_classifier_ = self.model_cls(**(self.model_args or {}))

    def fit(self, x, y=None):
        self._setup()

        if self.selector_column is None:
            return self.default_classifier_.fit(x, y)

        selector = np.squeeze(x[:, self.selector_column].toarray())
        for label in set(selector):
            label_samples = selector == label
            classifier = self.get_classifier(label)
            classifier.fit(x[label_samples], y[label_samples])

        return self

    def predict(self, x):
        if self.selector_column is None:
            return self.default_classifier_.predict(x)

        y = np.zeros(x.shape[0])
        y = np.array([-1] * x.shape[0])
        selector = np.squeeze(x[:, self.selector_column].toarray())
        for label in set(selector):
            label_samples = selector == label
            classifier = self.get_classifier(label)
            y[label_samples] = classifier.predict(x[label_samples])

        return y

    def score(self, x, y, sample_weight=None):
        if self.selector_column is None:
            return self.default_classifier_.score(x, y, sample_weight)

        scores = []
        selector = np.squeeze(x[:, self.selector_column].toarray())
        for label in set(selector):
            label_samples = selector == label
            classifier = self.get_classifier(label)
            scores.append(classifier.score(x[label_samples], y[label_samples]))

        return np.average(scores)

    def get_params(self, deep=True):
        if not isinstance(self.model_cls, basestring):
            model_cls = '%s.%s' % (self.model_cls.__module__, self.model_cls.__name__)
        else:
            model_cls = self.model_cls

        return {
            'model_cls': model_cls,
            'selector_column': self.selector_column,
            'model_args': self.model_args,
        }

    def set_params(self, **params):
        self.model_cls = params.get('model_cls', self.model_cls)
        self.selector_column = params.get('selector_column', self.selector_column)
        self.model_args = params.get('model_args', self.model_args)
        return self
