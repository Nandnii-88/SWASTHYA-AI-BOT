import os
import base64
from pathlib import Path

from dotenv import load_dotenv

# Gemini
from google import genai
from google.genai import types

# OpenAI
from openai import OpenAI

# Groq
from groq import Groq


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ============================================================
# MODELS
# ============================================================

# Gemini is responsible for ACTUAL IMAGE ANALYSIS.
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)

# OpenAI is TEXT ONLY in this application.
# Put a model available to your OpenAI API account here.
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5"
)

# Groq is TEXT ONLY in this application.
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)


# ============================================================
# CLIENT INITIALIZATION
# ============================================================

gemini_client = None
openai_client = None
groq_client = None


if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception as e:
        print(
            "WARNING: Gemini client initialization failed:",
            repr(e)
        )


if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY
        )
    except Exception as e:
        print(
            "WARNING: OpenAI client initialization failed:",
            repr(e)
        )


if GROQ_API_KEY:
    try:
        groq_client = Groq(
            api_key=GROQ_API_KEY
        )
    except Exception as e:
        print(
            "WARNING: Groq client initialization failed:",
            repr(e)
        )


# ============================================================
# LANGUAGES
# ============================================================

LANGUAGES = {
    "English": "English",
    "Hindi": "Hindi",
    "Bengali": "Bengali",
    "Telugu": "Telugu",
    "Marathi": "Marathi",
    "Tamil": "Tamil",
    "Gujarati": "Gujarati",
    "Kannada": "Kannada",
    "Malayalam": "Malayalam",
    "Punjabi": "Punjabi",
    "Urdu": "Urdu",
    "Odia": "Odia",
    "Assamese": "Assamese",
    "Sanskrit": "Sanskrit",

    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "te": "Telugu",
    "mr": "Marathi",
    "ta": "Tamil",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "or": "Odia",
    "as": "Assamese",
    "sa": "Sanskrit",
}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are SWASTHYAAI, a multilingual health-awareness assistant.

You provide health information and education.

You are NOT a doctor and must not present yourself as one.

IMPORTANT SAFETY RULES:

1. Never claim certainty about a diagnosis.

2. Never say that an image proves a disease or condition.

3. When discussing symptoms or images:
   - distinguish observations from possibilities
   - explain uncertainty
   - mention limitations
   - recommend appropriate professional care

4. For images:
   - describe only what is visibly present
   - do not invent details
   - do not diagnose from visual appearance alone
   - clearly state when image quality limits assessment

5. Do not prescribe prescription medication.

6. Do not tell users to start, stop, increase,
   or decrease prescribed medication.

7. If potentially serious warning signs are present,
   recommend urgent medical attention.

8. For users in India, emergency services can be reached
   through 112.

9. Respond entirely in the requested language.

10. Be helpful, calm, clear, and concise.

11. Never reveal internal API details, model names,
    provider results, internal confidence values,
    or implementation details to the user.
"""


# ============================================================
# HELPERS
# ============================================================

def get_language(language):
    """
    Convert a language code/name into the language name.
    """

    if not language:
        return "English"

    return LANGUAGES.get(
        language,
        str(language)
    )


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# EMERGENCY DETECTION
# ============================================================

EMERGENCY_KEYWORDS = [

    # Cardiac / breathing
    "chest pain",
    "chest pressure",
    "chest tightness",
    "difficulty breathing",
    "trouble breathing",
    "can't breathe",
    "cannot breathe",
    "shortness of breath",
    "severe breathlessness",

    # Neurological
    "stroke",
    "face drooping",
    "slurred speech",
    "can't speak",
    "cannot speak",
    "weakness on one side",
    "one side weakness",
    "paralysis",
    "seizure",
    "convulsion",
    "unconscious",
    "unresponsive",
    "passed out",
    "fainted",

    # Bleeding / trauma
    "severe bleeding",
    "heavy bleeding",
    "uncontrolled bleeding",
    "major injury",
    "severe injury",

    # Allergic reaction
    "anaphylaxis",
    "severe allergic reaction",
    "swelling of throat",
    "throat swelling",

    # Poisoning
    "overdose",
    "poisoning",
    "poison",

    # Burns
    "severe burn",

    # Mental-health emergency
    "suicidal",
    "suicide",
    "kill myself",
]


def detect_emergency(text):
    """
    Basic emergency keyword detection.

    Returns:
        True  -> potentially urgent symptom detected
        False -> no emergency keyword detected

    This is only a basic safety layer and does NOT
    replace professional medical assessment.
    """

    if not text:
        return False

    text_lower = str(text).lower()

    for keyword in EMERGENCY_KEYWORDS:

        if keyword in text_lower:
            return True

    return False


# ============================================================
# GEMINI TEXT
# ============================================================

def ask_gemini_text(
    message,
    history="",
    language="English"
):

    if gemini_client is None:

        print(
            "GEMINI TEXT: client unavailable"
        )

        return None

    language_name = get_language(
        language
    )

    prompt = f"""
{SYSTEM_PROMPT}

Requested language:
{language_name}

Conversation history:
{history}

Current user message:
{message}

Provide a useful health-awareness response.

If the user describes potentially dangerous symptoms,
clearly explain that urgent professional care may be needed.

Do not provide a definitive diagnosis.
"""

    try:

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )

        result = clean_text(
            getattr(
                response,
                "text",
                ""
            )
        )

        if result:
            return result

        print(
            "GEMINI TEXT ERROR: empty response"
        )

    except Exception as e:

        print("\n" + "=" * 70)
        print("GEMINI TEXT ERROR")
        print("TYPE:", type(e).__name__)
        print("MESSAGE:", repr(e))
        print("=" * 70 + "\n")

    return None


# ============================================================
# OPENAI TEXT
# ============================================================

def ask_openai_text(
    message,
    history="",
    language="English"
):

    if openai_client is None:

        print(
            "OPENAI TEXT: client unavailable"
        )

        return None

    language_name = get_language(
        language
    )

    prompt = f"""
{SYSTEM_PROMPT}

Requested language:
{language_name}

Conversation history:
{history}

Current user message:
{message}

Provide a useful health-awareness response.
Do not provide a definitive diagnosis.
"""

    try:

        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            store=False
        )

        result = clean_text(
            getattr(
                response,
                "output_text",
                ""
            )
        )

        if result:
            return result

        print(
            "OPENAI TEXT ERROR: empty response"
        )

    except Exception as e:

        print("\n" + "=" * 70)
        print("OPENAI TEXT ERROR")
        print("TYPE:", type(e).__name__)
        print("MESSAGE:", repr(e))
        print("=" * 70 + "\n")

    return None


# ============================================================
# GROQ TEXT
# ============================================================

def ask_groq_text(
    message,
    history="",
    language="English"
):

    if groq_client is None:

        print(
            "GROQ TEXT: client unavailable"
        )

        return None

    language_name = get_language(
        language
    )

    prompt = f"""
Requested language:
{language_name}

Conversation history:
{history}

Current user message:
{message}

Provide a cautious health-awareness response.

Do not diagnose with certainty.

Do not prescribe prescription medication.

Explain when professional care is appropriate.
"""

    try:

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.2,

            max_completion_tokens=1500
        )

        result = clean_text(
            response.choices[0]
            .message
            .content
        )

        if result:
            return result

        print(
            "GROQ TEXT ERROR: empty response"
        )

    except Exception as e:

        print("\n" + "=" * 70)
        print("GROQ TEXT ERROR")
        print("TYPE:", type(e).__name__)
        print("MESSAGE:", repr(e))
        print("=" * 70 + "\n")

    return None


# ============================================================
# MAIN CHAT FUNCTION
# ============================================================

def ask_gemini(
    message,
    history="",
    language="English"
):

    language_name = get_language(
        language
    )

    print("\n")
    print("=" * 70)
    print("SWASTHYAAI 3-API TEXT VERIFICATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Emergency layer
    # --------------------------------------------------------

    emergency = detect_emergency(
        message
    )

    # --------------------------------------------------------
    # Run all three providers
    # --------------------------------------------------------

    gemini_result = ask_gemini_text(
        message,
        history,
        language_name
    )

    openai_result = ask_openai_text(
        message,
        history,
        language_name
    )

    groq_result = ask_groq_text(
        message,
        history,
        language_name
    )

    print(
        "Gemini:",
        "SUCCESS" if gemini_result else "FAILED"
    )

    print(
        "OpenAI:",
        "SUCCESS" if openai_result else "FAILED"
    )

    print(
        "Groq:",
        "SUCCESS" if groq_result else "FAILED"
    )

    successful = [
        result
        for result in [
            gemini_result,
            openai_result,
            groq_result
        ]
        if result
    ]

    print(
        "Successful providers:",
        len(successful)
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Nothing worked
    # --------------------------------------------------------

    if not successful:

        print(
            "TEXT ANALYSIS FAILED COMPLETELY"
        )

        print("=" * 70)
        print()

        return (
            "I couldn't generate a response right now. "
            "Please check that the AI services and API keys "
            "are configured correctly."
        )

    # --------------------------------------------------------
    # Only one provider worked
    # --------------------------------------------------------

    if len(successful) == 1:

        answer = successful[0]

        if emergency:

            answer = (
                "⚠️ **Potential emergency**\n\n"
                "Some of the symptoms you described may "
                "require urgent medical attention. If the "
                "symptoms are severe, worsening, or life-threatening, "
                "please seek emergency care immediately. "
                "In India, you can call **112**.\n\n"
                + answer
            )

        return answer

    # --------------------------------------------------------
    # Multiple providers:
    # Use Gemini as final synthesis.
    # --------------------------------------------------------

    if gemini_client is not None:

        synthesis_prompt = f"""
{SYSTEM_PROMPT}

Requested language:
{language_name}

User message:
{message}

Independent health-information responses:

RESPONSE A:
{gemini_result or "Unavailable"}

RESPONSE B:
{openai_result or "Unavailable"}

RESPONSE C:
{groq_result or "Unavailable"}

Create ONE final answer for the user.

Rules:

- Do not mention the independent responses.
- Do not mention AI providers.
- Do not mention APIs.
- Do not mention model names.
- Do not expose internal verification.
- Resolve disagreements conservatively.
- Do not invent facts.
- Never provide a definitive diagnosis.
- Explain uncertainty when appropriate.
- Give practical next steps.
- Mention warning signs where relevant.
- Respond entirely in {language_name}.
"""

        try:

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=synthesis_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.15
                )
            )

            final_answer = clean_text(
                getattr(
                    response,
                    "text",
                    ""
                )
            )

            if final_answer:

                if emergency:

                    final_answer = (
                        "⚠️ **Potential emergency**\n\n"
                        "Some of the symptoms described may "
                        "require urgent medical attention. If "
                        "symptoms are severe, worsening, or "
                        "life-threatening, seek emergency care "
                        "immediately. In India, call **112**.\n\n"
                        + final_answer
                    )

                return final_answer

        except Exception as e:

            print("\n" + "=" * 70)
            print("TEXT SYNTHESIS ERROR")
            print("TYPE:", type(e).__name__)
            print("MESSAGE:", repr(e))
            print("=" * 70 + "\n")

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    answer = successful[0]

    if emergency:

        answer = (
            "⚠️ **Potential emergency**\n\n"
            "If the symptoms are severe, worsening, or "
            "life-threatening, seek urgent medical attention. "
            "In India, call **112**.\n\n"
            + answer
        )

    return answer


# ============================================================
# GEMINI IMAGE ANALYSIS
# ============================================================

def analyze_image_gemini(
    image_bytes,
    mime_type,
    question,
    language="English"
):

    if gemini_client is None:

        print(
            "GEMINI IMAGE ERROR: "
            "Gemini client is not initialized."
        )

        return None

    language_name = get_language(
        language
    )

    prompt = f"""
{SYSTEM_PROMPT}

Requested language:
{language_name}

The user has uploaded a health-related image.

User's question:
{question}

Carefully analyze the supplied image.

Use this structure:

VISIBLE OBSERVATIONS:
Describe only what can actually be seen.

POSSIBLE EXPLANATIONS:
Explain reasonable possibilities cautiously.
Do not diagnose with certainty.

WHAT CANNOT BE DETERMINED:
Explain what this image cannot establish.

WHAT TO DO NEXT:
Give sensible next steps.

WHEN TO SEEK URGENT CARE:
Mention relevant warning signs.

IMPORTANT:

- Never claim that the image proves a disease.
- Never give a definitive diagnosis.
- Never invent visual details.
- If image quality is poor, say so.
- Respond entirely in {language_name}.
"""

    try:

        print("\n" + "=" * 70)
        print("STARTING GEMINI IMAGE ANALYSIS")
        print("=" * 70)
        print("IMAGE PROVIDER: GEMINI")
        print("MODEL:", GEMINI_MODEL)
        print("MIME TYPE:", mime_type)
        print("IMAGE SIZE:", len(image_bytes), "bytes")
        print("=" * 70)

        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                image_part
            ],
            config=types.GenerateContentConfig(
                temperature=0.15
            )
        )

        result = clean_text(
            getattr(
                response,
                "text",
                ""
            )
        )

        if not result:

            print(
                "GEMINI IMAGE ERROR: "
                "Gemini returned an empty response."
            )

            return None

        print("=" * 70)
        print("GEMINI IMAGE SUCCESS")
        print("=" * 70)
        print()

        return result

    except Exception as e:

        print("\n" + "=" * 70)
        print("!!!!!!!! GEMINI IMAGE ERROR !!!!!!!!")
        print("ERROR TYPE:", type(e).__name__)
        print("ERROR:", repr(e))
        print("=" * 70)
        print()

        return None


# ============================================================
# OPENAI TEXT-ONLY IMAGE REVIEW
# ============================================================

def verify_image_text_with_openai(
    gemini_analysis,
    question,
    language="English"
):

    if openai_client is None:

        print(
            "OPENAI IMAGE REVIEW: "
            "client unavailable"
        )

        return None

    language_name = get_language(
        language
    )

    prompt = f"""
You are reviewing a health-awareness image assessment.

IMPORTANT:
You DID NOT see the original image.

You only have the textual assessment produced by
Gemini after analyzing the image.

Therefore, never claim that you independently saw
or interpreted the image.

Requested language:
{language_name}

User question:
{question}

Gemini's image assessment:
{gemini_analysis}

Review the assessment for:

- unsupported certainty
- potentially unsafe claims
- missing warning signs
- unreasonable recommendations
- places where uncertainty should be stated

Then provide a corrected health-awareness response.

Do not diagnose.

Do not claim to have seen the image.

Respond entirely in {language_name}.
"""

    try:

        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            store=False
        )

        result = clean_text(
            getattr(
                response,
                "output_text",
                ""
            )
        )

        if result:
            return result

    except Exception as e:

        print("\n" + "=" * 70)
        print("OPENAI IMAGE TEXT REVIEW ERROR")
        print("TYPE:", type(e).__name__)
        print("MESSAGE:", repr(e))
        print("=" * 70 + "\n")

    return None


# ============================================================
# GROQ TEXT-ONLY IMAGE REVIEW
# ============================================================

def verify_image_text_with_groq(
    gemini_analysis,
    question,
    language="English"
):

    if groq_client is None:

        print(
            "GROQ IMAGE REVIEW: "
            "client unavailable"
        )

        return None

    language_name = get_language(
        language
    )

    prompt = f"""
Review the following health-awareness image assessment.

IMPORTANT:
You DID NOT receive the original image.

You only received the text generated by another system
that analyzed the image.

Never claim to have seen the image.

Language:
{language_name}

User question:
{question}

Assessment:
{gemini_analysis}

Check for:

- unsupported medical certainty
- unsafe advice
- missing warning signs
- misleading conclusions
- places where uncertainty is needed

Return a cautious corrected health-awareness response.

Do not diagnose.

Respond entirely in {language_name}.
"""

    try:

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cautious health-information "
                        "reviewer. You cannot see the original image."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.1,

            max_completion_tokens=1500
        )

        result = clean_text(
            response.choices[0]
            .message
            .content
        )

        if result:
            return result

    except Exception as e:

        print("\n" + "=" * 70)
        print("GROQ IMAGE TEXT REVIEW ERROR")
        print("TYPE:", type(e).__name__)
        print("MESSAGE:", repr(e))
        print("=" * 70 + "\n")

    return None


# ============================================================
# MAIN IMAGE FUNCTION
# ============================================================

def analyze_image(
    image_bytes,
    mime_type,
    question,
    language="English"
):

    print("\n")
    print("=" * 70)
    print("SWASTHYAAI IMAGE ANALYSIS")
    print("=" * 70)
    print("ARCHITECTURE:")
    print("Gemini = ACTUAL IMAGE ANALYSIS")
    print("OpenAI = TEXT-ONLY REVIEW")
    print("Groq   = TEXT-ONLY REVIEW")
    print("=" * 70)

    # --------------------------------------------------------
    # STEP 1
    # Gemini sees the actual image.
    # --------------------------------------------------------

    gemini_result = analyze_image_gemini(
        image_bytes=image_bytes,
        mime_type=mime_type,
        question=question,
        language=language
    )

    print(
        "Gemini image:",
        "SUCCESS" if gemini_result else "FAILED"
    )

    # --------------------------------------------------------
    # If Gemini cannot see the image, do NOT pretend
    # the other text-only models can analyze it.
    # --------------------------------------------------------

    if not gemini_result:

        print(
            "Successful image providers: 0"
        )

        print("=" * 70)
        print("IMAGE ANALYSIS FAILED COMPLETELY")
        print("=" * 70)
        print()

        return None

    # --------------------------------------------------------
    # STEP 2
    # Other APIs review Gemini's textual interpretation.
    # They DO NOT receive the image.
    # --------------------------------------------------------

    openai_result = verify_image_text_with_openai(
        gemini_analysis=gemini_result,
        question=question,
        language=language
    )

    groq_result = verify_image_text_with_groq(
        gemini_analysis=gemini_result,
        question=question,
        language=language
    )

    print(
        "OpenAI text review:",
        "SUCCESS" if openai_result else "FAILED"
    )

    print(
        "Groq text review:",
        "SUCCESS" if groq_result else "FAILED"
    )

    # --------------------------------------------------------
    # If both reviewers fail, Gemini's image analysis
    # is still returned.
    # --------------------------------------------------------

    if not openai_result and not groq_result:

        print(
            "Using Gemini image analysis directly."
        )

        print("=" * 70)
        print()

        return gemini_result

    # --------------------------------------------------------
    # STEP 3
    # Build reviews.
    # --------------------------------------------------------

    reviews = []

    if openai_result:

        reviews.append(
            "OPENAI TEXT REVIEW:\n"
            + openai_result
        )

    if groq_result:

        reviews.append(
            "GROQ TEXT REVIEW:\n"
            + groq_result
        )

    combined_reviews = "\n\n".join(
        reviews
    )

    # --------------------------------------------------------
    # STEP 4
    # Gemini creates final response because Gemini
    # is the system that actually saw the image.
    # --------------------------------------------------------

    try:

        language_name = get_language(
            language
        )

        final_prompt = f"""
{SYSTEM_PROMPT}

You directly analyzed the original image.

Your original image assessment:
{gemini_result}

Other systems reviewed your textual assessment.
Their reviews are below:

{combined_reviews}

User's question:
{question}

Requested language:
{language_name}

Create ONE final response for the user.

IMPORTANT:

- You are the only system here that directly saw the image.
- Do not say that the other systems saw the image.
- Do not mention AI providers.
- Do not mention APIs.
- Do not mention model names.
- Do not expose internal verification.
- Do not give a definitive diagnosis.
- Do not claim the image proves a disease.
- Correct overconfident or unsafe statements.
- Preserve useful visible observations.
- Clearly distinguish observations from possibilities.
- Explain limitations.
- Give sensible next steps.
- Mention urgent warning signs when relevant.
- Respond entirely in {language_name}.
"""

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )

        final_result = clean_text(
            getattr(
                response,
                "text",
                ""
            )
        )

        if final_result:

            print(
                "IMAGE FINAL SYNTHESIS: SUCCESS"
            )

            print("=" * 70)
            print()

            return final_result

    except Exception as e:

        print("\n" + "=" * 70)
        print("GEMINI FINAL IMAGE SYNTHESIS ERROR")
        print("TYPE:", type(e).__name__)
        print("MESSAGE:", repr(e))
        print("=" * 70 + "\n")

    # --------------------------------------------------------
    # SAFE FALLBACK
    # --------------------------------------------------------

    print(
        "IMAGE FALLBACK: "
        "RETURNING GEMINI IMAGE ANALYSIS"
    )

    print("=" * 70)
    print()

    return gemini_result


# ============================================================
# API STATUS
# ============================================================

def get_api_status():

    return {

        "gemini": {
            "configured": bool(
                GEMINI_API_KEY
            ),
            "available": (
                gemini_client is not None
            ),
            "model": GEMINI_MODEL,
            "role": "image + text"
        },

        "openai": {
            "configured": bool(
                OPENAI_API_KEY
            ),
            "available": (
                openai_client is not None
            ),
            "model": OPENAI_MODEL,
            "role": "text verification"
        },

        "groq": {
            "configured": bool(
                GROQ_API_KEY
            ),
            "available": (
                groq_client is not None
            ),
            "model": GROQ_MODEL,
            "role": "text verification"
        }
    }


# ============================================================
# OPTIONAL PROVIDER TEST
# ============================================================

def test_api_connections():

    print("\n")
    print("=" * 70)
    print("SWASTHYAAI API CONFIGURATION")
    print("=" * 70)

    status = get_api_status()

    for provider, info in status.items():

        print(
            f"{provider.upper()}: "
            f"configured={info['configured']} "
            f"available={info['available']} "
            f"model={info['model']} "
            f"role={info['role']}"
        )

    print("=" * 70)
    print()

    return status

