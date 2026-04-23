
import os
import subprocess
import textwrap


def _sklearn_classifier_script(dataset_path):
    return textwrap.dedent(f"""\
        # Auto-generated scikit-learn classifier training script.
        import os, sys, json, joblib
        import pandas as pd
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, classification_report

        DATA_PATH  = os.environ.get("DATA_PATH",  r"{dataset_path}")
        MODEL_PATH = os.environ.get("MODEL_PATH", "models/classifier.pkl")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

        print(f"Loading {{DATA_PATH}}")
        df = pd.read_csv(DATA_PATH)
        target_col = df.columns[-1]
        X = pd.get_dummies(df.drop(columns=[target_col]))
        y = df[target_col]

        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(X_tr, y_tr)

        preds = model.predict(X_te)
        acc   = accuracy_score(y_te, preds)
        print(f"Accuracy: {{acc:.4f}}")
        print(classification_report(y_te, preds, zero_division=0))

        joblib.dump({{"model": model, "features": list(X.columns)}}, MODEL_PATH)
        print(f"Model saved to {{MODEL_PATH}}")
        with open("models/metrics.json", "w") as f:
            json.dump({{"accuracy": acc}}, f)
        """)


def _sklearn_regressor_script(dataset_path):
    return textwrap.dedent(f"""\
        import os, json, joblib
        import pandas as pd
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.metrics import mean_squared_error, r2_score

        DATA_PATH  = os.environ.get("DATA_PATH",  r"{dataset_path}")
        MODEL_PATH = os.environ.get("MODEL_PATH", "models/regressor.pkl")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

        df = pd.read_csv(DATA_PATH)
        target_col = df.columns[-1]
        X = pd.get_dummies(df.drop(columns=[target_col]))
        y = df[target_col]

        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        model = GradientBoostingRegressor(random_state=42)
        model.fit(X_tr, y_tr)
        preds = model.predict(X_te)
        mse = mean_squared_error(y_te, preds)
        r2  = r2_score(y_te, preds)
        print(f"MSE={{mse:.4f}}  R2={{r2:.4f}}")
        joblib.dump({{"model": model, "features": list(X.columns)}}, MODEL_PATH)
        with open("models/metrics.json", "w") as f:
            json.dump({{"mse": mse, "r2": r2}}, f)
        """)


def _keras_cnn_script(dataset_path):
    return textwrap.dedent(f"""\
        import os, json
        import tensorflow as tf
        from tensorflow.keras import layers, models

        MODEL_PATH = os.environ.get("MODEL_PATH", "models/cnn.keras")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

        (x_tr, y_tr), (x_te, y_te) = tf.keras.datasets.cifar10.load_data()
        x_tr, x_te = x_tr / 255.0, x_te / 255.0

        model = models.Sequential([
            layers.Conv2D(32, 3, activation="relu", input_shape=(32, 32, 3)),
            layers.MaxPooling2D(),
            layers.Conv2D(64, 3, activation="relu"),
            layers.MaxPooling2D(),
            layers.Conv2D(64, 3, activation="relu"),
            layers.Flatten(),
            layers.Dense(64, activation="relu"),
            layers.Dense(10, activation="softmax"),
        ])
        model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        hist = model.fit(x_tr, y_tr, epochs=5, validation_data=(x_te, y_te), verbose=2)
        model.save(MODEL_PATH)
        with open("models/metrics.json", "w") as f:
            json.dump({{"val_accuracy": float(hist.history["val_accuracy"][-1])}}, f)
        """)


def _torch_cnn_script(dataset_path):
    return textwrap.dedent("""\
        import os, json
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torchvision import datasets, transforms
        from torch.utils.data import DataLoader

        MODEL_PATH = os.environ.get("MODEL_PATH", "models/cnn.pt")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

        transform = transforms.Compose([transforms.ToTensor()])
        train = datasets.MNIST(".data", train=True,  download=True, transform=transform)
        test  = datasets.MNIST(".data", train=False, download=True, transform=transform)
        train_loader = DataLoader(train, batch_size=64, shuffle=True)
        test_loader  = DataLoader(test, batch_size=256)

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Conv2d(1, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                    nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                    nn.Flatten(),
                    nn.Linear(64*7*7, 128), nn.ReLU(),
                    nn.Linear(128, 10),
                )
            def forward(self, x): return self.net(x)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model  = Net().to(device)
        opt    = optim.Adam(model.parameters(), lr=1e-3)
        loss_fn = nn.CrossEntropyLoss()
        for epoch in range(3):
            model.train()
            for xb, yb in train_loader:
                xb, yb = xb.to(device), yb.to(device)
                opt.zero_grad(); loss = loss_fn(model(xb), yb); loss.backward(); opt.step()
            print(f"epoch={epoch} loss={loss.item():.4f}")
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for xb, yb in test_loader:
                xb, yb = xb.to(device), yb.to(device)
                preds = model(xb).argmax(1)
                correct += (preds == yb).sum().item(); total += yb.size(0)
        acc = correct / total
        print(f"accuracy={acc:.4f}")
        torch.save(model.state_dict(), MODEL_PATH)
        with open("models/metrics.json", "w") as f:
            json.dump({"accuracy": acc}, f)
        """)


def generate_training_script(project_type, dataset_path, framework="sklearn"):
    """Return the contents of train.py for the requested framework / task."""
    framework = (framework or "sklearn").lower()
    project_type = (project_type or "").lower()

    if framework == "sklearn":
        if "regression" in project_type:
            return _sklearn_regressor_script(dataset_path)
        return _sklearn_classifier_script(dataset_path)

    if framework in ("tensorflow", "keras", "tf"):
        return _keras_cnn_script(dataset_path)

    if framework in ("torch", "pytorch"):
        return _torch_cnn_script(dataset_path)

    raise ValueError(f"Unsupported framework: {framework}")


def generate_inference_script(model_path, framework="sklearn"):
    framework = (framework or "sklearn").lower()
    if framework == "sklearn":
        return textwrap.dedent(f"""\
            import os, sys, joblib, pandas as pd
            MODEL_PATH = os.environ.get("MODEL_PATH", r"{model_path}")
            bundle = joblib.load(MODEL_PATH)
            model, features = bundle["model"], bundle["features"]

            def predict(row_dict):
                X = pd.DataFrame([row_dict])
                X = pd.get_dummies(X).reindex(columns=features, fill_value=0)
                return model.predict(X)[0]

            if __name__ == "__main__":
                import json
                print(predict(json.loads(sys.argv[1])))
            """)
    if framework in ("tensorflow", "keras", "tf"):
        return textwrap.dedent(f"""\
            import os, sys, numpy as np, tensorflow as tf
            MODEL_PATH = os.environ.get("MODEL_PATH", r"{model_path}")
            model = tf.keras.models.load_model(MODEL_PATH)
            def predict(image_array):
                x = np.array(image_array)[None, ...] / 255.0
                return int(np.argmax(model.predict(x)[0]))
            """)
    if framework in ("torch", "pytorch"):
        return textwrap.dedent(f"""\
            import os, sys, torch
            MODEL_PATH = os.environ.get("MODEL_PATH", r"{model_path}")
            state = torch.load(MODEL_PATH, map_location="cpu")
            # TODO: reconstruct your model architecture before loading state.
            """)
    raise ValueError(framework)


def train_model(script_path, cwd=None, timeout=600):
    """Run a training script with the project's Python interpreter."""
    import sys
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
        ok = result.returncode == 0
        return {"ok": ok, "stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def save_model(model, path, framework="sklearn"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if framework == "sklearn":
        import joblib
        joblib.dump(model, path)
        return path
    if framework in ("tensorflow", "keras"):
        model.save(path)
        return path
    if framework in ("torch", "pytorch"):
        import torch
        torch.save(model.state_dict(), path)
        return path
    raise ValueError(framework)


# Eel exposures so the UI can trigger training 

try:
    import eel

    @eel.expose
    def uiGenerateTrainingScript(project_type, dataset_path, framework="sklearn"):
        import json
        try:
            return json.dumps({"ok": True, "script": generate_training_script(project_type, dataset_path, framework)})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @eel.expose
    def uiGenerateInferenceScript(model_path, framework="sklearn"):
        import json
        try:
            return json.dumps({"ok": True, "script": generate_inference_script(model_path, framework)})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
except ImportError:
    pass
