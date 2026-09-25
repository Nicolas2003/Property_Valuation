from __future__ import annotations

from sklearn.model_selection import train_test_split

from estimator.ml.dataset import training_frame
from estimator.ml.training import TRAINERS


def main() -> None:
    inputs, outputs = training_frame()
    train_inputs, test_inputs, train_outputs, test_outputs = train_test_split(
        inputs, outputs, test_size=1, random_state=42
    )

    actual = test_outputs.iloc[0]
    print(f"Fitted on {len(train_inputs)} sales, priced 1 held out.\n")

    for name, train in TRAINERS.items():
        model = train(train_inputs, train_outputs)
        prediction = model.predict(test_inputs)[0]
        difference = actual - prediction
        percentage_error = abs(difference) / actual * 100

        print(f"{name} predicted ${prediction:,.2f}")
        print(f"  Difference to the actual price: ${difference:,.2f}")
        print(f"  Absolute error: ${abs(difference):,.2f}")
        print(f"  Percentage error: {percentage_error:.2f}%\n")

    print(f"Actual price ${actual:,.2f}")


if __name__ == "__main__":
    main()
