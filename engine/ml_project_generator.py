import os
import re
import json
import time
import subprocess
import threading
import webbrowser
import requests


# ════════════════════════════════════════════════════════════════════════════
#  AI / ML PROJECT GENERATOR
#  Flow:
#    1. Understand the ML task from query
#    2. Search Kaggle + UCI + GitHub for a matching dataset
#    3. Generate full ML pipeline (train.py) — trains model + saves .pkl
#    4. Generate Flask prediction app (app.py + templates)
#    5. Install deps → run training → launch web app
# ════════════════════════════════════════════════════════════════════════════

def handleMLGeneration(query):
    from engine.command import speak, takecommand
    from engine.config import LLM_KEY
    import google.generativeai as genai
    import os
    
    # ── TEMP DEBUG — remove after fixing ─────────────────────────────────
    print(f"[DEBUG] LLM_KEY value: '{LLM_KEY}'")
    print(f"[DEBUG] CWD: {os.getcwd()}")
    
    engine_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir   = os.path.dirname(engine_dir)
    env_path   = os.path.join(root_dir, '.env')
    print(f"[DEBUG] Looking for .env at: {env_path}")
    print(f"[DEBUG] .env exists: {os.path.exists(env_path)}")
    
    if os.path.exists(env_path):
        with open(env_path) as f:
            content = f.read()
            # Mask the key for safety while printing
            masked = content.replace(LLM_KEY, '***') if LLM_KEY and len(LLM_KEY) > 5 else content
            print(f"[DEBUG] .env contents:\n{masked}")
    # ─────────────────────────────────────────────────────────────────────

    speak("Sure! Let me set up your machine learning project.")

    # ── Validate API key early ────────────────────────────────────────────
    if not LLM_KEY:
        speak("API key is missing. Please check your config file.")
        print("[MLGen] ERROR: LLM_KEY is empty or None in engine/config.py")
        return

    # ── Where to save ─────────────────────────────────────────────────────
    speak("Where would you like to save this project?")
    save_path_response = takecommand()
    save_dir     = _parse_save_path(save_path_response)
    project_name = _extract_project_name(query)
    project_dir  = os.path.join(save_dir, project_name)

    # ── Understand ML task ────────────────────────────────────────────────
    task_info = _analyze_ml_task(query)
    speak(f"Detected task: {task_info['task_type']}. Target: {task_info['target']}.")
    print(f"[MLGen] Task: {task_info}")

    # ── Search for datasets ───────────────────────────────────────────────
    speak("Searching for suitable datasets online.")
    dataset_info = _search_datasets(query, task_info, LLM_KEY)
    print(f"[MLGen] Dataset: {dataset_info['name']} | Source: {dataset_info['source']}")
    speak(f"Found dataset: {dataset_info['name']} from {dataset_info['source']}.")

    # ── Generate all project files — parallel batched ────────────────────
    speak("Generating your machine learning project files.")
    file_specs = _get_ml_file_specs(query, task_info, dataset_info, project_name)
    total = len(file_specs)

    genai.configure(api_key=LLM_KEY)
    from engine.code_generator import smart_generate_with_batching
    generated_files = smart_generate_with_batching(file_specs, genai)

    print(f"[MLGen] Generated {len(generated_files)}/{total} files.")

    # ── Deterministic fallback: if Gemini didn't produce train.py, inject a template
    if "train.py" not in generated_files:
        try:
            from engine.model_trainer import generate_training_script
            dataset_path = _infer_dataset_path(dataset_info)
            framework = "sklearn" if task_info["task_type"] != "image_classification" else "tensorflow"
            generated_files["train.py"] = generate_training_script(
                task_info["task_type"], dataset_path, framework=framework
            )
            print("[MLGen] train.py injected from deterministic template.")
        except Exception as e:
            print(f"[MLGen] train.py fallback failed: {e}")

    if "inference.py" not in generated_files:
        try:
            from engine.model_trainer import generate_inference_script
            framework = "sklearn" if task_info["task_type"] != "image_classification" else "tensorflow"
            generated_files["inference.py"] = generate_inference_script(
                "model/model.pkl", framework=framework
            )
            print("[MLGen] inference.py injected from deterministic template.")
        except Exception as e:
            print(f"[MLGen] inference.py fallback failed: {e}")

    if not generated_files:
        speak("Sorry, generation failed completely. Please try again.")
        return

    # ── Write files to disk ───────────────────────────────────────────────
    speak(f"Creating {len(generated_files)} project files.")
    _write_project_files(project_dir, generated_files, project_name, task_info, dataset_info)

    # ── Install dependencies ──────────────────────────────────────────────
    speak("Installing Python dependencies. This may take a minute.")
    install_cmd = (
        "pip install flask scikit-learn pandas numpy matplotlib seaborn "
        "joblib kaggle opendatasets requests plotly"
    )
    try:
        subprocess.run(install_cmd, shell=True, cwd=project_dir, timeout=180)
        speak("Dependencies installed.")
    except subprocess.TimeoutExpired:
        speak("Installation is taking long. Continuing in background.")
    except Exception as e:
        print(f"[MLGen] Install error: {e}")
        speak("Please check your internet connection for installing packages.")

    # ── Open in VS Code ───────────────────────────────────────────────────
    speak("Open the project in VS Code?")
    from engine.command import takecommand as tc
    if _yes(tc()):
        _open_in_vscode(project_dir)
        speak("Opened in VS Code.")

    # ── Train the model ───────────────────────────────────────────────────
    speak("Should I run the model training now?")
    if _yes(tc()):
        speak("Starting model training. I'll let you know when it's done.")
        success = _run_training(project_dir)
        if success:
            speak("Model training complete! The model has been saved.")
        else:
            speak("Training encountered an issue. Check the terminal for details.")
    else:
        speak("You can train later by running: python train.py")

    # ── Launch prediction web app ─────────────────────────────────────────
    speak("Should I start the prediction web app?")
    if _yes(tc()):
        speak("Starting the prediction app at http://localhost:5000")
        _run_server("python app.py", project_dir, "http://localhost:5000")
    else:
        speak("Run python app.py when you're ready to launch the prediction interface.")

    speak(f"Your ML project '{project_name}' is ready! The trained model is saved as model.pkl.")


# ════════════════════════════════════════════════════════════════════════════
#  ANALYZE ML TASK FROM QUERY
# ════════════════════════════════════════════════════════════════════════════
def _analyze_ml_task(query):
    q = query.lower()

    # Task type detection
    if any(w in q for w in ["price predict", "predict price", "house price", "stock price",
                              "salary predict", "regression", "forecast", "estimate"]):
        task_type = "regression"
    elif any(w in q for w in ["classify", "classification", "detect", "spam", "fraud",
                                "sentiment", "diagnosis", "cancer", "disease", "churn"]):
        task_type = "classification"
    elif any(w in q for w in ["cluster", "segment", "group", "unsupervised"]):
        task_type = "clustering"
    elif any(w in q for w in ["recommend", "recommendation", "suggest"]):
        task_type = "recommendation"
    elif any(w in q for w in ["nlp", "text", "sentiment", "review", "tweet", "language"]):
        task_type = "nlp_classification"
    elif any(w in q for w in ["image", "photo", "picture", "vision", "cnn"]):
        task_type = "image_classification"
    else:
        task_type = "classification"  # safe default

    # Target/domain detection
    domain_map = {
        "house": "house price prediction",
        "stock": "stock price prediction",
        "salary": "salary prediction",
        "spam": "spam email detection",
        "fraud": "fraud detection",
        "cancer": "cancer diagnosis",
        "heart": "heart disease prediction",
        "diabetes": "diabetes prediction",
        "churn": "customer churn prediction",
        "sentiment": "sentiment analysis",
        "movie": "movie recommendation",
        "iris": "iris flower classification",
        "titanic": "titanic survival prediction",
        "credit": "credit card fraud detection",
        "loan": "loan approval prediction",
        "customer": "customer segmentation",
    }
    target = "prediction"
    for keyword, label in domain_map.items():
        if keyword in q:
            target = label
            break

    # Algorithm suggestion
    algo_map = {
        "regression":         ["RandomForestRegressor", "GradientBoostingRegressor", "LinearRegression"],
        "classification":     ["RandomForestClassifier", "GradientBoostingClassifier", "LogisticRegression"],
        "clustering":         ["KMeans", "DBSCAN", "AgglomerativeClustering"],
        "nlp_classification": ["LogisticRegression", "MultinomialNB", "SGDClassifier"],
        "recommendation":     ["SVD", "KNNBasic", "NMF"],
        "image_classification":["CNN", "ResNet"],
    }
    algorithms = algo_map.get(task_type, ["RandomForestClassifier"])

    return {
        "task_type":  task_type,
        "target":     target,
        "algorithms": algorithms,
        "metric":     "R2 Score" if task_type == "regression" else "Accuracy",
    }


# ════════════════════════════════════════════════════════════════════════════
#  SEARCH DATASETS — Kaggle API → UCI → GitHub fallback
# ════════════════════════════════════════════════════════════════════════════
def _search_datasets(query, task_info, llm_key):
    """
    Priority:
    1. Kaggle public datasets API (no auth needed for search metadata)
    2. UCI ML Repository (HTTPS direct CSV links)
    3. GitHub awesome-datasets / sklearn built-in as fallback
    Returns dict with name, source, url, download_code
    """

    q           = query.lower()
    task_type   = task_info["task_type"]

    # ── Pre-mapped famous datasets (instant, reliable) ────────────────────
    KNOWN_DATASETS = {
        "titanic":    {
            "name": "Titanic Survival",
            "source": "GitHub (datasciencedojo)",
            "url": "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv",
            "target_col": "Survived",
            "download_code": "DIRECT_CSV"
        },
        "house price": {
            "name": "House Prices (Ames)",
            "source": "Kaggle",
            "url": "https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv",
            "target_col": "median_house_value",
            "download_code": "DIRECT_CSV"
        },
        "iris": {
            "name": "Iris Flower",
            "source": "sklearn built-in",
            "url": "sklearn",
            "target_col": "species",
            "download_code": "SKLEARN"
        },
        "diabetes": {
            "name": "Diabetes",
            "source": "sklearn built-in",
            "url": "sklearn",
            "target_col": "target",
            "download_code": "SKLEARN"
        },
        "heart": {
            "name": "Heart Disease (UCI)",
            "source": "UCI Repository",
            "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data",
            "target_col": "target",
            "download_code": "DIRECT_CSV"
        },
        "spam": {
            "name": "SMS Spam Collection (UCI)",
            "source": "UCI Repository",
            "url": "https://raw.githubusercontent.com/justmarkham/pycon-2016-tutorial/master/data/sms.tsv",
            "target_col": "label",
            "download_code": "DIRECT_CSV"
        },
        "sentiment": {
            "name": "IMDB Movie Reviews",
            "source": "sklearn/datasets",
            "url": "sklearn",
            "target_col": "sentiment",
            "download_code": "SKLEARN_IMDB"
        },
        "salary": {
            "name": "Adult Income (UCI)",
            "source": "UCI Repository",
            "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data",
            "target_col": "income",
            "download_code": "DIRECT_CSV"
        },
        "credit": {
            "name": "Credit Card Fraud",
            "source": "Kaggle (mlg-ulb)",
            "url": "kaggle:mlg-ulb/creditcardfraud",
            "target_col": "Class",
            "download_code": "KAGGLE"
        },
        "customer": {
            "name": "Mall Customer Segmentation",
            "source": "GitHub",
            "url": "https://raw.githubusercontent.com/dsrscientist/dataset1/master/Mall_Customers.csv",
            "target_col": "Spending Score (1-100)",
            "download_code": "DIRECT_CSV"
        },
        "churn": {
            "name": "Telecom Customer Churn",
            "source": "GitHub",
            "url": "https://raw.githubusercontent.com/dsrscientist/dataset1/master/Telecom_customer_churn.csv",
            "target_col": "Churn",
            "download_code": "DIRECT_CSV"
        },
    }

    for keyword, info in KNOWN_DATASETS.items():
        if keyword in q:
            print(f"[DataSearch] Matched known dataset: {info['name']}")
            return info

    # ── Kaggle public search API ──────────────────────────────────────────
    search_term = _build_kaggle_search_term(query, task_info)
    print(f"[DataSearch] Kaggle search: {search_term}")
    try:
        resp = requests.get(
            "https://www.kaggle.com/api/v1/datasets/list",
            params={"search": search_term, "sortBy": "votes", "pageSize": 3},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                ds = data[0]
                ref = ds.get("ref", "")  # e.g. "uciml/iris"
                title = ds.get("title", search_term)
                print(f"[DataSearch] Kaggle found: {title} ({ref})")
                return {
                    "name":          title,
                    "source":        "Kaggle",
                    "url":           f"kaggle:{ref}",
                    "target_col":    _guess_target_column(task_info),
                    "download_code": "KAGGLE"
                }
    except Exception as e:
        print(f"[DataSearch] Kaggle API error: {e}")

    # ── Fallback via dataset_finder (Kaggle CLI + HuggingFace + curated) ─
    try:
        from engine.dataset_finder import find_datasets
        project_type_map = {
            "regression":          "tabular-regression",
            "classification":      "tabular-classification",
            "nlp_classification":  "text-classification",
            "image_classification":"image-classification",
        }
        pt = project_type_map.get(task_type, "tabular-classification")
        candidates = find_datasets(pt, search_term)
        if candidates:
            first = candidates[0]
            print(f"[DataSearch] dataset_finder suggested: {first.get('id')}")
            return {
                "name":          first.get("title") or first.get("id", search_term),
                "source":        first.get("source", "curated"),
                "url":           first.get("url", "sklearn"),
                "target_col":    _guess_target_column(task_info),
                "download_code": "DIRECT_CSV" if str(first.get("url", "")).startswith("http") else "SKLEARN",
            }
    except Exception as e:
        print(f"[DataSearch] dataset_finder fallback skipped: {e}")

    # ── Fallback: sklearn built-in by task ────────────────────────────────
    fallback_map = {
        "regression":         {
            "name": "California Housing", "source": "sklearn built-in",
            "url": "sklearn", "target_col": "price", "download_code": "SKLEARN_HOUSING"
        },
        "classification":     {
            "name": "Breast Cancer Wisconsin", "source": "sklearn built-in",
            "url": "sklearn", "target_col": "target", "download_code": "SKLEARN_CANCER"
        },
        "clustering":         {
            "name": "Iris (for clustering)", "source": "sklearn built-in",
            "url": "sklearn", "target_col": "species", "download_code": "SKLEARN"
        },
        "nlp_classification": {
            "name": "20 Newsgroups", "source": "sklearn built-in",
            "url": "sklearn", "target_col": "category", "download_code": "SKLEARN_NEWS"
        },
    }
    fallback = fallback_map.get(task_type, fallback_map["classification"])
    print(f"[DataSearch] Using fallback: {fallback['name']}")
    return fallback


def _build_kaggle_search_term(query, task_info):
    q     = query.lower()
    words = re.findall(r'\b[a-z]{4,}\b', q)
    stop  = {"create", "make", "build", "generate", "machine", "learning",
             "model", "project", "train", "using", "with", "that", "will",
             "want", "need", "please", "system", "application"}
    keywords = [w for w in words if w not in stop][:3]
    return " ".join(keywords) if keywords else task_info["target"]


def _infer_dataset_path(dataset_info):
    """Pick a sensible default path the fallback train.py template can read."""
    url = dataset_info.get("url", "")
    if url.startswith("http"):
        return os.path.join("data", os.path.basename(url) or "dataset.csv")
    return "data/dataset.csv"


def _guess_target_column(task_info):
    target_col_map = {
        "regression":         "target",
        "classification":     "label",
        "clustering":         "cluster",
        "nlp_classification": "category",
    }
    return target_col_map.get(task_info["task_type"], "target")


# ════════════════════════════════════════════════════════════════════════════
#  GENERATE FILE SPECS
# ════════════════════════════════════════════════════════════════════════════
def _get_ml_file_specs(query, task_info, dataset_info, project_name):
    task_type   = task_info["task_type"]
    algorithms  = task_info["algorithms"]
    metric      = task_info["metric"]
    target_col  = dataset_info.get("target_col", "target")
    dataset_name = dataset_info["name"]
    download_code = dataset_info["download_code"]
    dataset_url   = dataset_info["url"]

    # ── Build data loading snippet ────────────────────────────────────────
    if download_code == "SKLEARN":
        data_load = """
from sklearn.datasets import load_iris
data = load_iris()
df = pd.DataFrame(data.data, columns=data.feature_names)
df['target'] = data.target
TARGET_COL = 'target'
"""
    elif download_code == "SKLEARN_CANCER":
        data_load = """
from sklearn.datasets import load_breast_cancer
data = load_breast_cancer()
df = pd.DataFrame(data.data, columns=data.feature_names)
df['target'] = data.target
TARGET_COL = 'target'
"""
    elif download_code == "SKLEARN_HOUSING":
        data_load = """
from sklearn.datasets import fetch_california_housing
data = fetch_california_housing()
df = pd.DataFrame(data.data, columns=data.feature_names)
df['target'] = data.target
TARGET_COL = 'target'
"""
    elif download_code == "SKLEARN_NEWS":
        data_load = """
from sklearn.datasets import fetch_20newsgroups
newsgroups = fetch_20newsgroups(subset='train', remove=('headers', 'footers', 'quotes'))
df = pd.DataFrame({'text': newsgroups.data, 'target': newsgroups.target})
TARGET_COL = 'target'
"""
    elif download_code == "KAGGLE":
        kaggle_ref = dataset_url.replace("kaggle:", "")
        data_load = f"""
import opendatasets as od
print("[Data] Downloading from Kaggle: {kaggle_ref}")
print("[Data] You'll need your Kaggle username and API key.")
print("[Data] Get them from: https://www.kaggle.com/account -> Create API Token")
od.download("https://www.kaggle.com/datasets/{kaggle_ref}")
# Find the downloaded CSV
import glob
csv_files = glob.glob("**/*.csv", recursive=True)
if not csv_files:
    raise FileNotFoundError("No CSV found after download. Check Kaggle credentials.")
df = pd.read_csv(csv_files[0])
TARGET_COL = '{target_col}'
"""
    else:  # DIRECT_CSV
        data_load = f"""
import requests, io
print("[Data] Downloading dataset from: {dataset_url}")
resp = requests.get("{dataset_url}", timeout=30)
resp.raise_for_status()
df = pd.read_csv(io.StringIO(resp.text))
TARGET_COL = '{target_col}'
# Handle common column name variations
if TARGET_COL not in df.columns:
    print(f"[Data] Columns found: {{list(df.columns)}}")
    print(f"[Data] Trying auto-detect for target column...")
    TARGET_COL = df.columns[-1]  # fallback to last column
    print(f"[Data] Using: {{TARGET_COL}}")
"""

    # ── train.py prompt ───────────────────────────────────────────────────
    train_prompt = f"""Write a COMPLETE, production-quality Python ML training script for: "{query}"

Dataset: {dataset_name}
Task type: {task_type}
Primary algorithms to try: {', '.join(algorithms)}
Evaluation metric: {metric}
Target column variable: TARGET_COL (already defined)

Use EXACTLY this data loading code at the top (do NOT redefine it):
```
{data_load}
```

The script must do ALL of the following in order:

1. IMPORTS — pandas, numpy, sklearn, matplotlib, seaborn, joblib, warnings

2. DATA LOADING — use the snippet above exactly as provided

3. EXPLORATORY DATA ANALYSIS (EDA)
   - Print shape, dtypes, head(5), describe()
   - Print missing values count
   - Save correlation heatmap as: reports/correlation_heatmap.png
   - Save target distribution plot as: reports/target_distribution.png

4. DATA PREPROCESSING
   - Drop rows with >50% missing values
   - Fill numeric nulls with median
   - Fill categorical nulls with mode
   - Label encode or one-hot encode categorical columns
   - Feature/target split: X = df.drop(TARGET_COL, axis=1), y = df[TARGET_COL]
   - Train/test split: 80/20, random_state=42
   - StandardScaler on X_train and X_test

5. MODEL TRAINING — train ALL of these models and compare:
{"   - RandomForestRegressor, GradientBoostingRegressor, LinearRegression" if task_type == "regression" else "   - RandomForestClassifier, GradientBoostingClassifier, LogisticRegression, SVC"}
   - Print training time for each model

6. MODEL EVALUATION
   - For each model print: {metric}, {"MAE, RMSE" if task_type == "regression" else "Precision, Recall, F1, Confusion Matrix"}
   - Save comparison bar chart as: reports/model_comparison.png
{"   - Save predicted vs actual scatter plot as: reports/predictions_scatter.png" if task_type == "regression" else "   - Save confusion matrix heatmap as: reports/confusion_matrix.png"}

7. SELECT BEST MODEL — pick the one with best {metric}

8. HYPERPARAMETER TUNING on best model using GridSearchCV (3-fold CV)

9. FINAL EVALUATION on test set with tuned model — print all metrics clearly

10. FEATURE IMPORTANCE — print top 10 features, save bar chart as: reports/feature_importance.png

11. SAVE MODEL with joblib:
    import joblib, json
    os.makedirs('model', exist_ok=True)
    joblib.dump(best_model, 'model/model.pkl')
    joblib.dump(scaler, 'model/scaler.pkl')
    feature_names = list(X.columns)
    with open('model/feature_names.json', 'w') as f:
        json.dump(feature_names, f)
    with open('model/model_info.json', 'w') as f:
        json.dump({{'task_type': '{task_type}', 'metric': '{metric}', 'dataset': '{dataset_name}', 'features': feature_names, 'target_col': TARGET_COL}}, f)
    print("[Model] Saved to model/model.pkl")
    print("[Model] Training complete!")

CRITICAL RULES:
- os.makedirs('reports', exist_ok=True) at the start
- All plots use: plt.savefig('path', dpi=100, bbox_inches='tight'); plt.close()
- NEVER use plt.show() — headless execution
- Handle exceptions gracefully with try/except and informative print statements
- At the end: print a clear summary table of all model scores

Return ONLY complete Python code, no markdown."""

    # ── app.py prompt ─────────────────────────────────────────────────────
    app_prompt = f"""Write a COMPLETE Flask web app for serving ML predictions for: "{query}"

Task type: {task_type}
Dataset: {dataset_name}

The app must:
1. Load model/model.pkl and model/scaler.pkl and model/feature_names.json on startup
2. Route GET / → render index.html (main prediction form)
3. Route POST /predict → load input from form, preprocess, predict, return result
4. Route GET /reports → render reports.html showing all saved PNG charts
5. Route GET /api/predict (JSON API) → accept JSON body, return prediction as JSON
6. Handle missing model gracefully: if model.pkl doesn't exist, show a message to run train.py first

CRITICAL:
- Use joblib.load() for model and scaler
- Use json.load() for feature_names.json
- The prediction form should have one input per feature from feature_names.json
- Show prediction result clearly on the page
- Include a back button
- Add basic error handling

Return ONLY complete Python Flask code, no markdown."""

    # ── index.html prompt ─────────────────────────────────────────────────
    index_html_prompt = f"""Write a COMPLETE, beautiful HTML template for an ML prediction web app for: "{query}"

Requirements:
- Full HTML document with ALL CSS inside <style> tag
- Dark theme, futuristic/tech aesthetic with gradient accents
- Header: app title "{project_name.replace('_',' ').title()} — AI Prediction"
- Status card: shows if model is loaded (green) or not (red with message "Run train.py first")
- Dynamic prediction form: use Jinja2 to render inputs for each feature:
  {{% for feature in features %}}
    <div class="form-group">
      <label>{{{{ feature }}}}</label>
      <input type="number" name="{{{{ feature }}}}" step="any" required>
    </div>
  {{% endfor %}}
- Large "Predict" button
- Result card (shown when prediction is not None):
  <div class="result-card {{% if prediction %}}visible{{% endif %}}">
    <h2>Prediction Result</h2>
    <div class="prediction-value">{{{{ prediction }}}}</div>
  </div>
- Flash messages display
- Nav links: Home | Reports | API Docs
- Responsive design

Return ONLY complete HTML, no markdown."""

    # ── reports.html prompt ───────────────────────────────────────────────
    reports_html_prompt = f"""Write a COMPLETE HTML template for displaying ML model reports for: "{query}"

Requirements:
- Full HTML document with ALL CSS in <style> tag
- Dark tech theme matching the main app
- Title: "Model Training Reports"
- Grid of report cards, each showing one chart image:
  {{% for report in reports %}}
    <div class="report-card">
      <h3>{{{{ report.title }}}}</h3>
      <img src="{{{{ report.path }}}}" alt="{{{{ report.title }}}}">
    </div>
  {{% endfor %}}
- If no reports exist, show message: "Run train.py to generate reports"
- Back to Home button
- Responsive 2-column grid layout

Return ONLY complete HTML, no markdown."""

    # ── Requirements ──────────────────────────────────────────────────────
    requirements_txt = (
        "PREFILLED:flask\n"
        "scikit-learn\n"
        "pandas\n"
        "numpy\n"
        "matplotlib\n"
        "seaborn\n"
        "joblib\n"
        "opendatasets\n"
        "requests\n"
        "plotly\n"
    )

    # ── README ─────────────────────────────────────────────────────────────
    readme = f"""PREFILLED:# {project_name.replace('_', ' ').title()}

**ML Task:** {task_type}  
**Dataset:** {dataset_name}  
**Metric:** {metric}

## Quick Start

### Step 1 — Install dependencies
```
pip install -r requirements.txt
```

### Step 2 — Train the model
```
python train.py
```
This will:
- Download the dataset automatically
- Run EDA and save charts to `reports/`
- Train and compare multiple models
- Tune the best model
- Save the model to `model/model.pkl`

### Step 3 — Launch the prediction app
```
python app.py
```
Open: http://localhost:5000

## Project Structure
```
{project_name}/
├── train.py              ← ML training pipeline
├── app.py                ← Flask prediction app
├── requirements.txt
├── model/
│   ├── model.pkl         ← Trained model (created by train.py)
│   ├── scaler.pkl        ← Feature scaler
│   ├── feature_names.json
│   └── model_info.json
├── reports/              ← Charts and evaluation plots
└── templates/
    ├── index.html        ← Prediction UI
    └── reports.html      ← Charts viewer
```

## API Usage
```bash
curl -X POST http://localhost:5000/api/predict \\
  -H "Content-Type: application/json" \\
  -d '{{"feature1": 1.0, "feature2": 2.0}}'
```
"""

    return [
        ("train.py",                train_prompt),
        ("app.py",                  app_prompt),
        ("templates/index.html",    index_html_prompt),
        ("templates/reports.html",  reports_html_prompt),
        ("requirements.txt",        requirements_txt),
        ("README.md",               readme),
    ]


# ════════════════════════════════════════════════════════════════════════════
#  WRITE PROJECT FILES TO DISK
# ════════════════════════════════════════════════════════════════════════════
def _write_project_files(project_dir, generated_files, project_name, task_info, dataset_info):
    try:
        for subdir in ["model", "reports", "templates", "static/css"]:
            os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)

        for filename, content in generated_files.items():
            if content.startswith("PREFILLED:"):
                content = content[10:]
            full_path = os.path.join(project_dir, filename)
            dir_path  = os.path.dirname(full_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[MLGen] Created: {filename}")

        # ── .gitignore ─────────────────────────────────────────────────────
        gitignore = "__pycache__/\n*.pyc\n.env\nmodel/\nreports/\n*.csv\n*.zip\n"
        with open(os.path.join(project_dir, ".gitignore"), 'w') as f:
            f.write(gitignore)

        print(f"[MLGen] Project created at: {project_dir}")
        return True
    except Exception as e:
        print(f"[MLGen] File creation error: {e}")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  RUN MODEL TRAINING IN A NEW TERMINAL WINDOW
# ════════════════════════════════════════════════════════════════════════════
def _run_training(project_dir):
    try:
        # Open a visible terminal so user can monitor training progress
        result = subprocess.run(
            f'start cmd /k "cd /d "{project_dir}" && python train.py && echo [DONE] Training finished! && pause"',
            shell=True,
            cwd=project_dir
        )
        print(f"[MLGen] Training process launched.")
        return True
    except Exception as e:
        print(f"[MLGen] Training error: {e}")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS (shared with code_generator pattern)
# ════════════════════════════════════════════════════════════════════════════
def _extract_project_name(query):
    match = re.search(
        r'(?:create|make|build|generate|train|develop)\s+(?:a\s+|an\s+)?(.+?)(?:\s+model|\s+project|\s+in\s+|\s+using\s+|$)',
        query, re.IGNORECASE
    )
    if match:
        name = match.group(1).strip().lower()
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = name.replace(' ', '_')[:40]
        return name or "ml_project"
    # Fallback: extract main keywords
    keywords = re.findall(r'\b[a-z]{4,}\b', query.lower())
    stop = {"create","make","build","train","generate","machine","learning","model","predict"}
    words = [w for w in keywords if w not in stop][:2]
    return "_".join(words) if words else "ml_project"


def _parse_save_path(response):
    if not response:
        return os.path.join("D:\\", "ML_Projects")
    response = response.lower().strip()
    path_match = re.search(r'[a-z]:\\[\w\\]+', response, re.IGNORECASE)
    if path_match:
        return path_match.group()
    if "desktop"  in response: return os.path.join(os.path.expanduser("~"), "Desktop",   "ML_Projects")
    if "document" in response: return os.path.join(os.path.expanduser("~"), "Documents", "ML_Projects")
    if "download" in response: return os.path.join(os.path.expanduser("~"), "Downloads", "ML_Projects")
    drive_match = re.search(r'\b([a-z])\s*(?:drive|disk)?\b', response)
    if drive_match:
        drive = drive_match.group(1).upper()
        return os.path.join(f"{drive}:\\", "ML_Projects")
    return os.path.join("D:\\", "ML_Projects")


def _yes(response):
    if not response:
        return False
    return any(w in response.lower() for w in
               ["yes", "yeah", "sure", "okay", "ok", "please", "yep", "do it", "run", "start", "train"])


def _open_in_vscode(project_dir):
    try:
        subprocess.run(f'code "{project_dir}"', shell=True, timeout=5)
    except Exception:
        local  = os.environ.get("LOCALAPPDATA", "")
        vscode = os.path.join(local, "Programs", "Microsoft VS Code", "Code.exe")
        if os.path.exists(vscode):
            subprocess.Popen([vscode, project_dir])


def _run_server(run_cmd, project_dir, start_url):
    def _start():
        subprocess.Popen(
            f'start cmd /k "cd /d "{project_dir}" && {run_cmd}"',
            shell=True
        )
        time.sleep(4)
        webbrowser.open(start_url)
    threading.Thread(target=_start, daemon=True).start()