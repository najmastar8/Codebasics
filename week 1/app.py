import os

import streamlit as st
from dotenv import load_dotenv
from groq import Groq


load_dotenv()

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


def generate_workout_plan(
    fitness_goal: str,
    experience_level: str,
    days_per_week: int,
    equipment_access: str,
    limitations: str,
) -> str:
    """Generate a practical weekly plan from a user's structured fitness profile."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return "I could not generate your plan because `GROQ_API_KEY` is missing. Add it to the `.env` file and try again."

    if not 1 <= days_per_week <= 7:
        return "Please choose between 1 and 7 workout days per week."

    limitations_text = limitations.strip() or "No injuries or limitations provided."
    prompt = f"""
You are an experienced, safety-conscious personal trainer. Create a personalized,
realistic weekly workout plan using the profile below.

Profile:
- Fitness goal: {fitness_goal}
- Experience level: {experience_level}
- Training days available: {days_per_week}
- Equipment access: {equipment_access}
- Injuries or limitations: {limitations_text}

Requirements:
1. Start with a brief summary of the plan's strategy and how to progress it.
2. Give exactly {days_per_week} numbered workout days. Include a warm-up, exercises,
   sets, reps or time, rest guidance, and a cool-down for each day.
3. Add rest or active-recovery guidance for the remaining days of the week.
4. Adapt exercise selection and difficulty to the experience level and equipment.
5. Respect every stated limitation. Do not diagnose injuries. Add a brief note to
   stop and consult a qualified professional if an exercise causes pain.
6. Keep the plan achievable in 30-60 minutes per session.
7. Format the response in clear Markdown with headings and bullet points.
"""

    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You create specific, safe, usable workout plans. Be concise but complete.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.65,
            max_tokens=1800,
        )
        response = completion.choices[0].message.content
        if not isinstance(response, str) or not response.strip():
            return "The model returned an empty plan. Please try again."
        return response.strip()
    except Exception as error:
        error_text = str(error).lower()
        if "model_not_found" in error_text or "does not exist" in error_text:
            return f"The configured Groq model (`{DEFAULT_MODEL}`) is unavailable. Update `GROQ_MODEL` in `.env` to a model available to your Groq account."
        if "authentication" in error_text or "invalid_api_key" in error_text or "401" in error_text:
            return "The Groq API key was rejected. Check `GROQ_API_KEY` in `.env` and try again."
        if "rate_limit" in error_text or "429" in error_text:
            return "The Groq API rate limit was reached. Wait a moment and try again."
        return "I could not reach the workout planner. Check your internet connection and Groq configuration, then try again."


st.set_page_config(
    page_title="Forge | Personal Workout Planner",
    page_icon="🏋️",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');

    :root { --ink: #17211b; --muted: #66736b; --lime: #d7f36b; --paper: #f5f7f1; --line: #dbe2d8; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; color: var(--ink); }
    .stApp { background: var(--paper); }
    [data-testid="stSidebar"] { background: #17211b; }
    [data-testid="stSidebar"] * { color: #f5f7f1; }
    .hero { padding: 1.5rem 0 1rem; border-bottom: 1px solid var(--line); margin-bottom: 1.25rem; }
    .kicker { color: #71802d; font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
    .hero h1 { font-size: clamp(2.3rem, 5vw, 4.8rem); line-height: .98; margin: .3rem 0 .7rem; max-width: 760px; }
    .hero p { color: var(--muted); font-size: 1.05rem; max-width: 620px; }
    .profile-note { background: var(--lime); color: var(--ink); padding: .8rem 1rem; font-weight: 700; margin: 1rem 0 1.2rem; }
    div.stButton > button { background: var(--ink); color: white; border: 0; border-radius: 3px; min-height: 3rem; font-weight: 700; }
    div.stButton > button:hover { background: #405047; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## FORGE")
    st.caption("A plan built around your actual week.")
    st.divider()
    st.markdown("### How it works")
    st.write("Tell us what you can commit to, what you have available, and what your body needs. The planner turns that context into a week you can follow.")
    st.divider()
    st.caption("AI-generated guidance is not medical advice. Stop if you feel pain and consult a qualified professional.")

st.markdown(
    '<div class="hero"><div class="kicker">Personal training, made practical</div><h1>Your week. Your strength.</h1><p>Build a training plan that fits your goal, your schedule, your equipment, and your real-world limitations.</p></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="profile-note">Start with the details a good trainer would ask for.</div>', unsafe_allow_html=True)

with st.form("workout_profile"):
    left, right = st.columns(2)
    with left:
        fitness_goal = st.selectbox(
            "What is your main goal?",
            ["Build muscle", "Lose fat", "General fitness", "Improve endurance"],
        )
        experience_level = st.selectbox(
            "How would you describe your experience?",
            ["Beginner", "Intermediate", "Advanced"],
        )
        days_per_week = st.slider("How many days can you train?", 1, 7, 3)
    with right:
        equipment_access = st.selectbox(
            "What equipment can you use?",
            ["No equipment", "Home dumbbells", "Full gym"],
        )
        limitations = st.text_area(
            "Injuries, limitations, or preferences (optional)",
            placeholder="e.g. bad knees, no overhead pressing, prefer short sessions",
            height=124,
        )
        submitted = st.form_submit_button("Generate my weekly plan", use_container_width=True)

if submitted:
    if not fitness_goal or not experience_level or not equipment_access:
        st.error("Please complete the required profile selections before generating a plan.")
    elif days_per_week < 1:
        st.error("Please select at least one training day.")
    else:
        with st.spinner("Building a plan around your week..."):
            plan = generate_workout_plan(
                fitness_goal,
                experience_level,
                days_per_week,
                equipment_access,
                limitations,
            )
        st.divider()
        st.markdown("## Your weekly plan")
        st.markdown(plan)