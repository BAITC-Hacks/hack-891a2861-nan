# Career Quest recommendation system

Explainable hybrid recommender for the Career Quest case. The public input is an `employee_id`; the output contains one to three eligible events and a structured payload for a separate LLM explanation service.

## Pipeline

```text
employee_id
  -> employee and career goal
  -> target role profile and skill gaps
  -> eligibility and prerequisite filters
  -> career impact and focus/critical priority
  -> Logistic Regression completion probability
  -> history and availability scoring
  -> diversity-aware Top 3
  -> llm_payload
```

The ranker decides what to recommend. The LLM is not called by this package and must only verbalize the supplied facts.

## Data

By default the package reads `../case_1/career_quest_dataset` and expects:

- `employees_updated.json`
- `events.json`
- `skills.json`
- `activity_history.csv`
- `activity_completion_logistic.csv`

The directory can be overridden with `--data-dir`.

The serialized model from the notebook is not required. On the first run the service trains Logistic Regression from the CSV in the current Python/scikit-learn environment and atomically saves a versioned model under `.model_cache/`. Later runs reuse that compatible cache. This avoids failures caused by empty or cross-version `joblib` files.

## Run from the command line

```bash
cd recommendation_system
python3 -m career_quest_recommender E0006
python3 -m career_quest_recommender E0006 --limit 1
```

## HTTP API

The API uses Python's standard library and does not require FastAPI.

```bash
cd recommendation_system
python3 -m career_quest_recommender.api --port 8000
```

Requests:

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/recommendations/E0006
GET http://127.0.0.1:8000/recommendations/E0006?limit=1
```

## Score

```text
final_score =
    0.50 * career_impact
  + 0.20 * priority_match
  + 0.15 * completion_probability
  + 0.10 * history_fit
  + 0.05 * availability
  - repeat_failure_penalty
```

Career impact and focus/critical priority contribute 70% of the score. Logistic Regression contributes 15%, so an easy but irrelevant event cannot displace an important career step.

## LLM contract

Each result contains `llm_payload` with:

- preferred language;
- current and target role/grade;
- selected event details;
- current, required, and projected skill levels;
- completion probability;
- structured reason facts and cautions.

The payload intentionally excludes the employee's name, manager, raw history, and other employees' data. The LLM must not change the event, score, rank, or calculated levels.

## Tests

```bash
cd recommendation_system
python3 -m unittest discover -s tests -v
```
