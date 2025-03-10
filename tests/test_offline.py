from pathlib import Path

import numpy as np
import numpy.linalg as LA
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from salmon.triplets.offline import OfflineEmbedding
from salmon.triplets.samplers import TSTE


def test_score_predict_basic():
    """Test the interface for score/predict"""
    n = 10
    n_ans = 40
    X = np.random.choice(n, size=(n_ans, 3)).astype("uint8")
    alg = TSTE(n=n, d=2)

    # Test expected interface
    y = np.random.choice(2, size=n_ans).astype("uint8")
    y_hat = alg.predict(X)
    assert y_hat.shape == (n_ans,)
    assert np.unique(y_hat).tolist() == [0, 1]

    acc = alg.score(X, y)
    assert isinstance(acc, float)
    assert 0 <= acc <= 1


def test_score_accurate():
    n = 10
    n_ans = 40
    X = np.random.choice(n, size=(n_ans, 3)).astype("uint8")
    alg = TSTE(n=n, d=2)
    y_hat = alg.predict(X)

    # Make sure perfect accuracy if the output aligns with the embedding
    assert np.allclose(alg.score(X, y_hat), 1)

    # Make sure the score has the expected value (winner has minimum distance)
    embed = alg.opt.embedding() * 1e3
    y_hat2 = []
    for (head, left, right) in X:
        ldist = LA.norm(embed[head] - embed[left])
        rdist = LA.norm(embed[head] - embed[right])

        left_wins = ldist <= rdist
        y_hat2.append(0 if left_wins else 1)

    assert y_hat.tolist() == y_hat2


def test_offline_embedding():
    n, d = 85, 2
    max_epochs = 20

    X = np.random.choice(n, size=(10_000, 3))
    X_train, X_test = train_test_split(X, random_state=0, test_size=0.2)

    model = OfflineEmbedding(n=n, d=d, max_epochs=max_epochs)
    model.fit(X_train, X_test)
    assert isinstance(model.embedding_, np.ndarray)
    assert model.embedding_.shape == (n, d)

    assert isinstance(model.history_, list)
    assert all(isinstance(h, dict) for h in model.history_)
    epochs = model.history_[-1]["num_grad_comps"] / len(X_train)
    eps = 0.75
    assert max_epochs - eps <= epochs <= max_epochs + eps


def test_offline_embedding_random_state():
    n, d = 85, 2
    max_epochs = 20
    random_state = 20

    X = np.random.choice(n, size=(10_000, 3))
    X_train, X_test = train_test_split(X, random_state=0, test_size=0.2)

    m1 = OfflineEmbedding(
        n=n, d=d, max_epochs=max_epochs, random_state=random_state
    ).initialize(X_train)
    m2 = OfflineEmbedding(
        n=n, d=d, max_epochs=max_epochs, random_state=random_state
    ).initialize(X_train)
    assert np.allclose(m1.embedding_, m2.embedding_)
