# Week 1 Workout Planner

A single-page Streamlit app that uses the Groq API to generate a personalized weekly workout plan.

## Requirements

- Python 3.10 or newer
- A Groq API key
- Internet access for the Groq API request

## Setup on Windows

Open a terminal in this folder:

```powershell
cd "C:\Users\najma\OneDrive\Desktop\Codebasics\week 1"
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configure the Groq API

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace the placeholder API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

Get a key from [Groq Console](https://console.groq.com/keys). Never commit or share `.env`; it is excluded by `.gitignore`.

## Run the app

```powershell
streamlit run app.py
```

Streamlit will display a local URL, normally:

```text
http://localhost:8501
```

Open that URL in your browser.

## Using the app

1. Choose a fitness goal.
2. Select your experience level.
3. Choose how many days per week you can train.
4. Select your available equipment.
5. Add injuries, limitations, or preferences if applicable.
6. Click **Generate my weekly plan**.

The app returns a day-by-day plan with exercises, sets, repetitions or time, rest guidance, warm-ups, cool-downs, and recovery days.

## Troubleshooting

- If `streamlit` is not recognized, activate the virtual environment and run `python -m pip install -r requirements.txt` again.
- If the app reports a missing API key, check that `.env` exists in the same folder as `app.py`.
- If the configured model is unavailable, set `GROQ_MODEL` in `.env` to a model available to your Groq account.
- AI-generated workout guidance is not medical advice. Stop if an exercise causes pain and consult a qualified professional.
