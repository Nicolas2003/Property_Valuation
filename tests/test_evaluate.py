from __future__ import annotations

import pandas as pd

from scripts import evaluate


class FixedModel:
    def __init__(self, price):
        self.price = price

    def predict(self, inputs):
        return [self.price] * len(inputs)


def test_main_reports_each_trainers_error_on_the_held_out_sale(monkeypatch, capsys):
    inputs = pd.DataFrame({"AREA": [100, 200, 300]})
    outputs = pd.Series([400_000.0, 400_000.0, 400_000.0])
    monkeypatch.setattr(evaluate, "training_frame", lambda: (inputs, outputs))
    monkeypatch.setattr(evaluate, "TRAINERS", {"Fixed": lambda _inputs, _outputs: FixedModel(300_000.0)})

    evaluate.main()

    out = capsys.readouterr().out
    assert "Fitted on 2 sales, priced 1 held out." in out
    assert "Fixed predicted $300,000.00" in out
    assert "Difference to the actual price: $100,000.00" in out
    assert "Percentage error: 25.00%" in out
    assert "Actual price $400,000.00" in out
