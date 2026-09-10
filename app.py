
import os
import math
import requests
from pathlib import Path

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    url_for
)

from flask_cors import CORS

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user
)

from flask_dance.contrib.google import (
    make_google_blueprint,
    google
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from dotenv import load_dotenv

from models import db, User, Message

from chatbot import (
    ask_gemini,
    analyze_image,
    detect_emergency,
    get_api_status
)


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)


app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "swasthyaai-dev-secret-key"
)


app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///" + str(
        BASE_DIR / "healthbot.db"
    )
)


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024


# ============================================================
# GOOGLE OAUTH
# ============================================================

app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv(
    "GOOGLE_OAUTH_CLIENT_ID"
)

app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv(
    "GOOGLE_OAUTH_CLIENT_SECRET"
)


# ============================================================
# DATABASE / LOGIN
# ============================================================

db.init_app(app)

CORS(
    app,
    supports_credentials=True
)


login_manager = LoginManager()

login_manager.login_view = None

login_manager.init_app(app)


# ============================================================
# OPTIONAL GOOGLE LOGIN
# ============================================================

if (
    app.config["GOOGLE_OAUTH_CLIENT_ID"]
    and
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"]
):

    google_bp = make_google_blueprint(
        scope=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email"
        ],
        redirect_to="google_authorized"
    )

    app.register_blueprint(
        google_bp,
        url_prefix="/login"
    )


# ============================================================
# DATABASE INIT
# ============================================================

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):

    try:
        return User.query.get(int(user_id))

    except Exception:
        return None


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# OLD DASHBOARD REDIRECT
# ============================================================

@app.route("/dashboard")
def dashboard():

    return redirect(
        url_for("home")
    )


# ============================================================
# BASIC HEALTH CHECK
# ============================================================

@app.route(
    "/api/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "status": "ok",
        "service": "SWASTHYAAI API"
    })


# ============================================================
# API STATUS
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def api_status():

    status = get_api_status()

    return jsonify({
        "success": True,
        "apis": {
            "gemini": status["gemini"],
            "openai": status["openai"],
            "groq": status["groq"]
        },
        "models": {
            "gemini": status["gemini_model"],
            "openai": status["openai_model"],
            "groq": status["groq_model"],
            "groq_vision": status["groq_vision_model"]
        }
    })


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/api/register",
    methods=["POST"]
)
def register():

    data = request.get_json(
        silent=True
    ) or {}

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    if not name or not email or not password:

        return jsonify({
            "error": "All fields are required"
        }), 400


    existing_user = User.query.filter_by(
        email=email
    ).first()


    if existing_user:

        return jsonify({
            "error": "Email already registered"
        }), 409


    user = User(
        name=name,
        email=email,
        password=generate_password_hash(
            password
        )
    )


    db.session.add(user)

    db.session.commit()

    login_user(user)


    return jsonify({
        "message": "User registered successfully",
        "user_id": user.id,
        "name": user.name,
        "authenticated": True
    }), 201


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/api/login",
    methods=["POST"]
)
def login():

    data = request.get_json(
        silent=True
    ) or {}


    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )


    if not email or not password:

        return jsonify({
            "error": "Email and password are required"
        }), 400


    user = User.query.filter_by(
        email=email
    ).first()


    if (
        not user
        or
        not check_password_hash(
            user.password,
            password
        )
    ):

        return jsonify({
            "error": "Invalid email or password"
        }), 401


    login_user(user)


    return jsonify({
        "message": "Login successful",
        "user_id": user.id,
        "name": user.name,
        "authenticated": True
    }), 200


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    logout_user()

    return redirect(
        url_for("home")
    )


# ============================================================
# GOOGLE AUTHORIZED
# ============================================================

@app.route("/google/authorized")
def google_authorized():

    if not google.authorized:

        return redirect(
            url_for("home")
        )


    try:

        response = google.get(
            "/oauth2/v2/userinfo"
        )


        if not response.ok:

            return redirect(
                url_for("home")
            )


        info = response.json()


        email = info.get("email")

        name = (
            info.get("name")
            or
            info.get("given_name")
            or
            "User"
        )


        if not email:

            return redirect(
                url_for("home")
            )


        email = email.lower()


        user = User.query.filter_by(
            email=email
        ).first()


        if not user:

            user = User(
                name=name,
                email=email,
                password=generate_password_hash(
                    os.urandom(24).hex()
                )
            )

            db.session.add(user)

            db.session.commit()


        login_user(user)


        return redirect(
            url_for("home")
        )


    except Exception as e:

        print(
            "GOOGLE OAUTH ERROR:",
            repr(e)
        )

        return redirect(
            url_for("home")
        )


# ============================================================
# CHAT
# ============================================================

@app.route(
    "/api/chat",
    methods=["POST"]
)
def chat():

    data = request.get_json(
        silent=True
    ) or {}


    message = str(
        data.get("message", "")
    ).strip()


    language = str(
        data.get("language", "English")
    ).strip() or "English"


    history = data.get(
        "history",
        ""
    )


    if not message:

        return jsonify({
            "error": "Message is required"
        }), 400


    try:

        answer = ask_gemini(
            message=message,
            history=history,
            language=language
        )


        if not answer:

            return jsonify({
                "error": (
                    "All configured AI services "
                    "are currently unavailable. "
                    "Check your API keys and terminal."
                )
            }), 503


        emergency = detect_emergency(
            message
        )

        emergency = (
            emergency
            or
            detect_emergency(answer)
        )


        if current_user.is_authenticated:

            try:

                db.session.add(
                    Message(
                        user_id=current_user.id,
                        role="user",
                        content=message
                    )
                )


                db.session.add(
                    Message(
                        user_id=current_user.id,
                        role="assistant",
                        content=answer
                    )
                )


                db.session.commit()


            except Exception as db_error:

                db.session.rollback()

                print(
                    "CHAT HISTORY ERROR:",
                    repr(db_error)
                )


        return jsonify({

            "success": True,

            "answer": answer,

            "language": language,

            "emergency": emergency

        }), 200


    except Exception as e:

        print("\n================================")
        print("CHAT ROUTE ERROR")
        print(type(e).__name__)
        print(str(e))
        print("================================\n")


        return jsonify({

            "error": "AI service unavailable",

            "details": str(e)

        }), 500


# ============================================================
# IMAGE ANALYSIS
# ============================================================

@app.route(
    "/api/analyze-image",
    methods=["POST"]
)
def analyze_image_endpoint():

    uploaded = request.files.get(
        "image"
    )


    question = str(
        request.form.get(
            "question",
            ""
        )
    ).strip()


    language = str(
        request.form.get(
            "language",
            "English"
        )
    ).strip() or "English"


    if uploaded is None:

        return jsonify({
            "error": "No image was uploaded"
        }), 400


    if not uploaded.filename:

        return jsonify({
            "error": "Please select an image"
        }), 400


    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp"
    }


    mime_type = (
        uploaded.mimetype
        or ""
    ).lower()


    if mime_type not in allowed_types:

        return jsonify({
            "error": (
                "Please upload a JPG, PNG, "
                "or WebP image."
            )
        }), 400


    image_bytes = uploaded.read()


    if not image_bytes:

        return jsonify({
            "error": "The uploaded image is empty"
        }), 400


    if len(image_bytes) > 10 * 1024 * 1024:

        return jsonify({
            "error": (
                "Image is too large. "
                "Please use an image under 10 MB."
            )
        }), 413


    if not question:

        question = (
            "Please analyze this image "
            "and tell me what I should know."
        )


    try:

        answer = analyze_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            question=question,
            language=language
        )


        if not answer:

            return jsonify({
                "error": (
                    "All configured image-analysis "
                    "services are unavailable. "
                    "Check your API keys."
                )
            }), 503


        emergency = detect_emergency(
            answer
        )


        if current_user.is_authenticated:

            try:

                db.session.add(
                    Message(
                        user_id=current_user.id,
                        role="user",
                        content="[Image] " + question
                    )
                )


                db.session.add(
                    Message(
                        user_id=current_user.id,
                        role="assistant",
                        content=answer
                    )
                )


                db.session.commit()


            except Exception as db_error:

                db.session.rollback()

                print(
                    "IMAGE HISTORY ERROR:",
                    repr(db_error)
                )


        return jsonify({

            "success": True,

            "answer": answer,

            "language": language,

            "emergency": emergency

        }), 200


    except Exception as e:

        print("\n================================")
        print("IMAGE ROUTE ERROR")
        print(type(e).__name__)
        print(str(e))
        print("================================\n")


        return jsonify({

            "error": (
                "Image analysis is unavailable "
                "right now."
            ),

            "details": str(e)

        }), 500


# ============================================================
# DISTANCE
# ============================================================

def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    earth_radius = 6371000.0


    p1 = math.radians(lat1)

    p2 = math.radians(lat2)


    dp = math.radians(
        lat2 - lat1
    )

    dl = math.radians(
        lon2 - lon1
    )


    a = (
        math.sin(dp / 2) ** 2
        +
        math.cos(p1)
        *
        math.cos(p2)
        *
        math.sin(dl / 2) ** 2
    )


    return (
        earth_radius
        *
        2
        *
        math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )


# ============================================================
# OVERPASS QUERY
# ============================================================

def hospital_query(
    lat,
    lng,
    radius
):

    return f"""
[out:json][timeout:30];

(
  nwr[
    "amenity"="hospital"
  ](
    around:{radius},
    {lat},
    {lng}
  );

  nwr[
    "healthcare"="hospital"
  ](
    around:{radius},
    {lat},
    {lng}
  );
);

out center tags;
"""


# ============================================================
# OVERPASS REQUEST
# ============================================================

def fetch_overpass(
    url,
    query
):

    headers = {
        "User-Agent": (
            "SWASTHYAAI/1.0 "
            "(health awareness project)"
        )
    }


    try:

        response = requests.post(
            url,
            data=query,
            headers=headers,
            timeout=30
        )


        response.raise_for_status()


        data = response.json()


        if not isinstance(
            data,
            dict
        ):

            return []


        return data.get(
            "elements",
            []
        )


    except Exception as e:

        print(
            "OVERPASS ERROR:",
            url,
            repr(e)
        )

        return []


# ============================================================
# HOSPITALS
# ============================================================

@app.route(
    "/api/hospitals",
    methods=["GET"]
)
def hospitals():

    lat = request.args.get(
        "lat",
        type=float
    )

    lng = request.args.get(
        "lng",
        type=float
    )


    radius = request.args.get(
        "radius",
        default=15000,
        type=int
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if lat is None or lng is None:

        return jsonify({
            "error": (
                "Latitude and longitude "
                "are required."
            )
        }), 400


    if not (
        -90 <= lat <= 90
    ):

        return jsonify({
            "error": "Invalid latitude"
        }), 400


    if not (
        -180 <= lng <= 180
    ):

        return jsonify({
            "error": "Invalid longitude"
        }), 400


    # Search between 1km and 30km.
    radius = max(
        1000,
        min(radius, 30000)
    )


    query = hospital_query(
        lat,
        lng,
        radius
    )


    servers = [

        "https://overpass-api.de/api/interpreter",

        "https://overpass.kumi.systems/api/interpreter",

        "https://overpass.private.coffee/api/interpreter"

    ]


    all_elements = []


    # --------------------------------------------------------
    # TRY MULTIPLE OVERPASS SERVERS
    # --------------------------------------------------------

    for server in servers:

        elements = fetch_overpass(
            server,
            query
        )


        if elements:

            all_elements.extend(
                elements
            )


    if not all_elements:

        return jsonify({
            "error": (
                "Hospital service is temporarily "
                "unavailable. Please try again."
            )
        }), 503


    # --------------------------------------------------------
    # CLEAN / DEDUPLICATE
    # --------------------------------------------------------

    hospitals_found = []

    seen_ids = set()

    seen_locations = set()


    for element in all_elements:

        element_id = (
            element.get("type"),
            element.get("id")
        )


        if element_id in seen_ids:

            continue


        seen_ids.add(
            element_id
        )


        tags = (
            element.get("tags")
            or {}
        )


        name = (

            tags.get("name")

            or

            tags.get("name:en")

            or

            tags.get("official_name")

            or

            tags.get("name:hi")

        )


        if not name:

            continue


        hospital_lat = (
            element.get("lat")
        )

        hospital_lng = (
            element.get("lon")
        )


        if hospital_lat is None:

            center = (
                element.get("center")
                or {}
            )


            hospital_lat = (
                center.get("lat")
            )

            hospital_lng = (
                center.get("lon")
            )


        if (
            hospital_lat is None
            or
            hospital_lng is None
        ):

            continue


        hospital_lat = float(
            hospital_lat
        )

        hospital_lng = float(
            hospital_lng
        )


        # Dedupe same hospital.
        dedupe_key = (

            str(name)
            .strip()
            .lower(),

            round(
                hospital_lat,
                5
            ),

            round(
                hospital_lng,
                5
            )

        )


        if dedupe_key in seen_locations:

            continue


        seen_locations.add(
            dedupe_key
        )


        # ----------------------------------------------------
        # REAL DISTANCE FROM USER
        # ----------------------------------------------------

        distance = calculate_distance(

            lat,
            lng,

            hospital_lat,
            hospital_lng

        )


        # ----------------------------------------------------
        # ADDRESS
        # ----------------------------------------------------

        address_parts = []


        for key in [

            "addr:housenumber",

            "addr:street",

            "addr:suburb",

            "addr:city",

            "addr:state",

            "addr:postcode"

        ]:

            value = tags.get(
                key
            )


            if value:

                address_parts.append(
                    str(value)
                )


        address = ", ".join(
            address_parts
        )


        phone = (

            tags.get("phone")

            or

            tags.get(
                "contact:phone"
            )

            or

            tags.get(
                "contact:mobile"
            )

        )


        website = (

            tags.get("website")

            or

            tags.get(
                "contact:website"
            )

        )


        emergency = (
            tags.get("emergency")
            or None
        )


        hospitals_found.append({

            "name": str(name),

            "latitude": hospital_lat,

            "longitude": hospital_lng,

            "distance_meters": round(
                distance
            ),

            "distance_km": round(
                distance / 1000,
                2
            ),

            "address": address,

            "phone": phone,

            "website": website,

            "emergency": emergency,

            "directions_url": (
                "https://www.google.com/maps/dir/"
                "?api=1"
                f"&destination="
                f"{hospital_lat},{hospital_lng}"
            )

        })


    # --------------------------------------------------------
    # CLOSEST FIRST
    # --------------------------------------------------------

    hospitals_found.sort(
        key=lambda hospital:
        hospital["distance_meters"]
    )


    # ALWAYS RETURN MAXIMUM 10.
    hospitals_found = (
        hospitals_found[:10]
    )


    return jsonify({

        "success": True,

        "user_location": {

            "latitude": lat,

            "longitude": lng

        },

        "radius_km": round(
            radius / 1000,
            1
        ),

        "count": len(
            hospitals_found
        ),

        "hospitals": hospitals_found

    }), 200


# ============================================================
# HISTORY
# ============================================================

@app.route(
    "/api/history",
    methods=["GET"]
)
def history():

    if not current_user.is_authenticated:

        return jsonify([])


    messages = (

        Message.query

        .filter_by(
            user_id=current_user.id
        )

        .order_by(
            Message.created_at.asc()
        )

        .all()

    )


    return jsonify([

        {

            "role": message.role,

            "content": message.content,

            "created_at":
                message.created_at.isoformat()

        }

        for message in messages

    ])


# ============================================================
# USER
# ============================================================

@app.route(
    "/api/user",
    methods=["GET"]
)
def user():

    if not current_user.is_authenticated:

        return jsonify({

            "authenticated": False,

            "name": "Guest"

        })


    return jsonify({

        "authenticated": True,

        "id": current_user.id,

        "name": current_user.name,

        "email": current_user.email

    })

# ============================================================
# SMS WEBHOOK (TWILIO)
# ============================================================

@app.route(
    "/sms",
    methods=["POST"]
)
def sms_reply():
    from twilio.twiml.messaging_response import MessagingResponse

    incoming_msg = str(
        request.form.get("Body", "")
    ).strip()

    if not incoming_msg:
        return str(MessagingResponse().message("Please send a valid message.")), 200, {'Content-Type': 'application/xml'}

    try:
        # Aapke existing ask_gemini function ka use karke AI response generate karna
        answer = ask_gemini(
            message=incoming_msg,
            language="English"
        )

        if not answer:
            answer = "AI service is currently unavailable. Please try again later."

        twilio_resp = MessagingResponse()
        twilio_resp.message(answer)

        return str(twilio_resp), 200, {'Content-Type': 'application/xml'}

    except Exception as e:
        print("\n================================")
        print("SMS ROUTE ERROR")
        print(type(e).__name__)
        print(str(e))
        print("================================\n")
        
        error_resp = MessagingResponse()
        error_resp.message("Sorry, an error occurred while processing your message.")
        return str(error_resp), 200, {'Content-Type': 'application/xml'}
# ============================================================
# ERRORS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    if request.path.startswith(
        "/api/"
    ):

        return jsonify({
            "error":
                "API endpoint not found"
        }), 404


    return render_template(
        "index.html"
    ), 404


@app.errorhandler(405)
def method_not_allowed(error):

    if request.path.startswith(
        "/api/"
    ):

        return jsonify({
            "error":
                "Method not allowed"
        }), 405


    return "Method Not Allowed", 405


@app.errorhandler(413)
def request_too_large(error):

    return jsonify({
        "error":
            "Uploaded file is too large."
    }), 413


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()


    app.run(

        debug=True,

        host="0.0.0.0",

        port=5000

    )

