"""
Dataset discovery helpers used by the ML pipeline.

Sources:
    * Kaggle — via the kaggle CLI if credentials (~/.kaggle/kaggle.json) exist.
    * Hugging Face Datasets — via the huggingface_hub package if installed.
    * Curated fallback — a small catalogue of classic public datasets so the
      feature has sensible results even without network or keys.

All heavy imports are done lazily so the module stays import-safe.
"""

import json
import os
import shutil
import subprocess


FALLBACK_CATALOGUE = {
    "tabular-classification": [
        {"id": "iris",            "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data",
         "columns": ["sepal_length", "sepal_width", "petal_length", "petal_width", "class"], "size": "small"},
        {"id": "titanic",         "url": "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv",
         "columns": ["Survived", "Pclass", "Sex", "Age", "Fare"], "size": "small"},
        {"id": "breast-cancer",   "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/breast-cancer-wisconsin/wdbc.data",
         "columns": ["id", "diagnosis"] + [f"f{i}" for i in range(30)], "size": "small"},
    ],
    "tabular-regression": [
        {"id": "boston-housing",  "url": "http://lib.stat.cmu.edu/datasets/boston",
         "columns": ["CRIM", "ZN", "INDUS", "RM", "AGE", "DIS", "MEDV"], "size": "small"},
        {"id": "california-housing", "url": "sklearn.datasets.fetch_california_housing",
         "columns": ["MedInc", "HouseAge", "AveRooms", "Population", "MedHouseVal"], "size": "small"},
    ],
    "image-classification": [
        {"id": "cifar10",         "url": "tensorflow.keras.datasets.cifar10", "columns": ["image", "label"], "size": "medium"},
        {"id": "mnist",           "url": "tensorflow.keras.datasets.mnist",   "columns": ["image", "label"], "size": "medium"},
    ],
    "text-classification": [
        {"id": "imdb-reviews",    "url": "tensorflow.keras.datasets.imdb", "columns": ["review", "sentiment"], "size": "medium"},
        {"id": "sms-spam",        "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip",
         "columns": ["label", "message"], "size": "small"},
    ],
}


def _kaggle_available():
    return shutil.which("kaggle") is not None and os.path.exists(
        os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json")
    )


def _kaggle_search(keywords):
    if not _kaggle_available():
        return []
    try:
        out = subprocess.run(
            ["kaggle", "datasets", "list", "-s", keywords, "-v"],
            capture_output=True, text=True, timeout=30
        )
        rows = out.stdout.strip().splitlines()[1:]
        datasets = []
        for row in rows[:10]:
            parts = row.split(",")
            if len(parts) >= 2:
                datasets.append({"id": parts[0], "source": "kaggle", "title": parts[1]})
        return datasets
    except Exception as e:
        print(f"[dataset_finder] Kaggle error: {e}")
        return []


def _huggingface_search(keywords):
    try:
        from huggingface_hub import list_datasets
        found = list(list_datasets(search=keywords, limit=10))
        return [{"id": d.id, "source": "huggingface", "title": d.id} for d in found]
    except Exception as e:
        print(f"[dataset_finder] HuggingFace unavailable: {e}")
        return []


def find_datasets(project_type, keywords=""):
    """
    project_type examples: 'tabular-classification', 'image-classification',
                           'text-classification', 'tabular-regression'.
    keywords: free-text extra search terms.
    """
    results = []
    if keywords:
        results.extend(_kaggle_search(keywords))
        results.extend(_huggingface_search(keywords))
    results.extend(FALLBACK_CATALOGUE.get(project_type, []))
    # Deduplicate by id, preserve order.
    seen = set()
    dedup = []
    for r in results:
        key = r.get("id")
        if key and key not in seen:
            seen.add(key)
            dedup.append(r)
    return dedup


def download_dataset(dataset_id, source, target_dir):
    """Download the dataset to target_dir. Returns (ok, message)."""
    os.makedirs(target_dir, exist_ok=True)

    if source == "kaggle":
        if not _kaggle_available():
            return False, "Kaggle CLI not configured."
        try:
            subprocess.run(
                ["kaggle", "datasets", "download", "-d", dataset_id,
                 "-p", target_dir, "--unzip"],
                check=True, timeout=180
            )
            return True, f"Downloaded {dataset_id} to {target_dir}."
        except Exception as e:
            return False, str(e)

    if source == "huggingface":
        try:
            from datasets import load_dataset
            ds = load_dataset(dataset_id)
            ds_path = os.path.join(target_dir, dataset_id.replace("/", "_"))
            ds.save_to_disk(ds_path)
            return True, f"Saved HF dataset to {ds_path}."
        except Exception as e:
            return False, str(e)

    # Fallback: attempt a plain URL download.
    try:
        from urllib.request import urlretrieve
        url = dataset_id if dataset_id.startswith("http") else None
        if not url:
            return False, f"Unknown source '{source}' and no URL given."
        target_path = os.path.join(target_dir, os.path.basename(url) or "dataset.bin")
        urlretrieve(url, target_path)
        return True, f"Downloaded to {target_path}."
    except Exception as e:
        return False, str(e)


def validate_dataset(path):
    if not os.path.exists(path):
        return {"ok": False, "message": "Path does not exist."}
    if os.path.isfile(path):
        size = os.path.getsize(path)
        return {"ok": size > 0, "message": f"{size} bytes", "size": size}
    # Directory — look for common formats.
    found = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith((".csv", ".tsv", ".json", ".jsonl", ".parquet", ".npz", ".arrow")):
                found.append(os.path.join(root, f))
    return {"ok": bool(found), "message": f"{len(found)} data files", "files": found[:20]}


def get_dataset_info(dataset_id):
    for type_list in FALLBACK_CATALOGUE.values():
        for entry in type_list:
            if entry["id"] == dataset_id:
                return entry
    return {"id": dataset_id, "columns": [], "size": "unknown"}
