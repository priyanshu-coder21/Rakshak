# ==========================================
# 1. IMPORTS
# ==========================================
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated, Literal
import string
import secrets
from psycopg2.extras import Json
import psycopg2, os
from tokenizers import Tokenizer
import ollama
import json
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# ==========================================
# 2. ENVIRONMENT & APP INITIALIZATION
# ==========================================
# Load the env file to access Postgres credentials securely
load_dotenv()

# Load a pre-trained fast tokenizer (e.g., standard BERT) to manage text length for the AI
tokenizer = Tokenizer.from_pretrained("bert-base-uncased")

# Initialize the FastAPI application instance
app = FastAPI()

# Mount static folder to serve frontend assets (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="src"), name="static")


# ==========================================
# 3. PYDANTIC MODELS (Data Validation)
# ==========================================
# Defines the expected payload when a victim submits a distress signal
class DistressRequest(BaseModel):
    raw_message: str = Field(..., description='Message of the victim')
    latitude: float = Field(..., ge=-90.0, le=90.0, example=30.3165)
    longitude: float = Field(..., ge=-180.0, le=180.0, example=78.0322)

# Defines the structured response sent back to the victim
class DistressResponse(BaseModel):
    token_id: str
    status: str
    extracted_data: dict
    message: str

# Defines the expected payload when registering a new rescue team
class RescueRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, example=30.3165)
    longitude: float = Field(..., ge=-180.0, le=180.0, example=78.0322)
    team_capacity: int = Field(..., ge=5)

# Defines the structured response after a rescue team registers
class RescueResponse(BaseModel):
    team_id: str
    status: Literal['Available', 'In_Transit', 'Assigned']
    message: str


# ==========================================
# 4. HELPER & UTILITY FUNCTIONS
# ==========================================
# establish the connection with database using environment variables
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT")
    )

# token id generation to create an anonymous tracking ID (PID paradigm) for victims
def token_id_generator(prefix="TK-2026-UK") -> str:
    random_chars = ''.join(
        secrets.choice(string.ascii_uppercase + string.digits)
        for _ in range(6)
    )
    # OR
    # characters = []
    # for _ in range(6):
    #     character = secrets.choice(
    #         string.ascii_uppercase + string.digits
    #     )
    #     characters.append(character)
    # random_chars = ''.join(characters)

    return f"{prefix}-{random_chars}"

# team_id generation to uniquely identify rescue units
def team_id_generator(prefix='UK-2026-RES') -> str:
    random_chars = ''.join(
        secrets.choice (string.ascii_uppercase + string.digits)
        for _ in range(4)
    )

    return f"{prefix}-{random_chars}"

# Passes the raw message to a local LLM to extract structured severity and vulnerability metrics
def extract_disaster_metrics(text: str) -> dict:
    # 1. Hugging Face Tokenization: Convert text into AI token IDs
    encoded = tokenizer.encode(text)
    
    # 2. Truncate strictly to your safety limit (e.g., max 120 tokens)
    truncated_ids = encoded.ids[:120]
    
    # 3. Decode the token IDs back into a clean string for Ollama
    clean_text = tokenizer.decode(truncated_ids)
    
    system_prompt = (
        "You are an emergency response AI. Extract details from the distress text. "
        "Respond ONLY with valid JSON containing these exact keys: "
        "'severity' (integer 1 to 5), "
        "'vulnerability' (integer 1 to 5 based on age or medical conditions) "
    )

    try:
        response = ollama.chat(
            model="qwen2.5:3b",
            format="json",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": clean_text}
            ]
        )
        return json.loads(response["message"]["content"])
    except Exception:
        # Fallback safe defaults if AI service encounters an issue
        return {"severity": 3, "vulnerability": 3}


# ==========================================
# 5. API ROUTES
# ==========================================

# Route to serve the frontend interface
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join("src", "index.html"))

# request going to db by victim to log their distress call
@app.post('/api/distress', response_model=DistressResponse, status_code=201)
def report_distress(distress_data: DistressRequest):

    # Generate a unique tracker and extract data via Ollama
    token_id = token_id_generator()
    extracted_data = extract_disaster_metrics(distress_data.raw_message)
    extracted_json = Json(extracted_data)
    
    # NOTE: Hardcoded metrics (can be dynamically mapped from extracted_json later)
    severity = 1
    vulnerability = 1

    conn = None
    cur = None

    # SQL string mapping coordinates to a PostGIS spatial point (SRID 4326)
    insert_sql_query = """
        INSERT INTO DistressTickets (
            token_id, raw_message, extracted_json, location, severity, vulnerability, status
        )
        VALUES (
            %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, 'Pending'
        );
    """

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Execute database insertion
            cur.execute(insert_sql_query, (
                    token_id,
                    distress_data.raw_message,
                    extracted_json,
                    distress_data.longitude,
                    distress_data.latitude,
                    severity,
                    vulnerability
                    )
            )
        # Finalize the transaction
        conn.commit()

    except Exception as e:
        # Revert changes if the database operation fails
        if conn:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database Error. Error: {str(e)}"
        )

    finally:
        # Always close connection to prevent connection pooling limits
        if conn:
            conn.close()

    # Return tracking token and parsed metadata to caller
    return DistressResponse(
        token_id=token_id,
        status="Pending",
        extracted_data = extracted_data,
        message="Distress report registered successfully. Keep your tracking token safe."
    )

# get data from Distress table for the command dashboard
@app.get('/getDistress')
async def get_distress():

    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()

        # Query all active distress tickets
        query = """
        SELECT *
        FROM DistressTickets
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

            # Map tuples to a list of dictionaries for clean JSON response
            result = []
            for row in rows:
                result.append({
                    "token_id" : row[0],
                    "raw_message" : row[1], 
                    "extracted_json" : row[2], 
                    "location" : row[3], 
                    "severity" : row[4], 
                    "vulnerability" : row[5],
                    "wait_time_start" : row[6],
                    "vwps_score" : row[7],
                    "status" : row[8]
                })

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error. Error: {str(e)}"
        )

    finally:
        if connection:
            connection.close()

# Register a new rescue team to the system
@app.post('/api/rescue', response_model=RescueResponse, status_code=201)
async def post_rescue(rescue_data:RescueRequest):

    # Create a unique ID for the team
    team_id = team_id_generator()

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        # Insert team with PostGIS spatial point
        query = """
        INSERT INTO RescueTeams (
        team_id, current_location, team_capacity)
        VALUES (%s,  ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
        """

        with connection.cursor() as cursor:
            cursor.execute(query, (
                team_id,
                rescue_data.longitude,
                rescue_data.latitude,
                rescue_data.team_capacity
            ))

        # Commit transaction
        connection.commit()

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database Error. Error: {str(e)}"
        )

    finally:
        if connection:
            connection.close()

    return RescueResponse(
        team_id=team_id,
        status="Available",
        message="The Rescue has been registered."
    )

# Retrieve all active rescue teams for the dashboard
@app.get('/getRescue')
async def get_rescue():

    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()

        query = """
        SELECT *
        FROM RescueTeams
        """
        with connection.cursor() as cursor:
            cursor.execute(query)

            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "team_id" : row[0],
                    "location" : row[1], 
                    "status": row[2],
                    "capacity" : row[3]
                })

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error. Error: {str(e)}"
        )

    finally:
        if connection:
            connection.close()

# Triggers the VWPS spatial matching algorithm to dispatch the nearest team
@app.post('/api/dispatch/run', status_code=200)
async def dispatch_run():
    connection = None

    try:
        connection = get_db_connection()

        # select the token_id and location of 1 victim (based on vwps_score, token_id)
        # token_id used as tie breaker in case of vwps_score collision.
        query1 = """
        SELECT token_id, location
        FROM DistressTickets
        WHERE status = 'Pending'
        ORDER BY vwps_score DESC, token_id ASC
        LIMIT 1;
        """

        # PostGIS query to find the nearest available team, utilizing row locking to prevent race conditions
        query2 = """
        SELECT team_id,
            ST_Distance(
                current_location,
                %s
                ) AS dist
        FROM RescueTeams
        WHERE status = 'Available'
        ORDER BY dist ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED;
        """

        # 3. The three atomic updates (logging the run, and updating statuses)
        query_log = "INSERT INTO Dispatch_Logs (token_id, team_id) VALUES (%s, %s)"
        query_update_victim = "UPDATE DistressTickets SET status = 'Dispatched' WHERE token_id = %s"
        query_update_team = "UPDATE RescueTeams SET status = 'In_Transit' WHERE team_id = %s"

        with connection.cursor() as cursor:
            # Step A: Identify the highest priority victim
            cursor.execute(query1)
            victim_row = cursor.fetchone()
            if victim_row is None:
                raise HTTPException(
                    status = 404,
                    detail='Ticket not found.'
                )
            token_id = victim_row[0]
            victim_location = victim_row[1]

            # Step B: Identify the closest team
            cursor.execute(query2, (victim_location,))
            rescue_row = cursor.fetchone()
            if rescue_row is None:
                raise HTTPException(
                    status_code= 404,
                    detail='Rescue Team not available.'
                )
            team_id = rescue_row[0]


            # Step C: Execute the updates atomically
            cursor.execute(query_log, (token_id, team_id))
            cursor.execute(query_update_victim, (token_id,))
            cursor.execute(query_update_team, (team_id,))

            # Permanently save the transaction to the database
            connection.commit()

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if connection:
            connection.close()
    
# Retrieve the history of all automated dispatch events
@app.get('/getDispatchLogs')
async def getDispatchLogs():

    conn = None
    cur = None

    try:
        conn = get_db_connection()

        query = """
        SELECT *
        FROM Dispatch_Logs
        """

        with conn.cursor() as cur:
            cur.execute(query)

            rows = cur.fetchall()

            result = []
            for row in rows:
                result.append({
                    'log_id': row[0],
                    'token_id': row[1],
                    'team_id': row[2],
                    'dispatch_time': row[3],
                    'sns_alert_sent': row[4]
                })

            return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error. Error: {str(e)}"
        )
    
    finally:
        if conn:
            conn.close()


# ==========================================
# 6. ARCHIVED / COMMENTED CODE
# ==========================================
# @app.post("/api/distress", response_model=DistressResponse, status_code= 201)
# def report_distress(distress_message: DistressRequest):
#     # for generating tokenID
#     token_id = token_id_generator()

#     # sending message to ollama model so that it can refine the message
#     extracted_data = message_extraction(distress_message.raw_message)
#     severity

#     # Write to PostgreSQL (PostGIS Point: Longitude first, then Latitude)
#     insert_sql = """
#         INSERT INTO DistressTickets (
#             token_id, raw_message, extracted_json, location, severity, vulnerability, status
#         )
#         VALUES (
#             %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, 'Pending'
#         );
#     """

#     conn = None
#     try:
#         conn = get_db_connection()
#         with conn.cursor() as cursor:
#             cursor.execute(
#                 insert_sql,
#                 (
#                     token_id,
#                     extracted_data.raw_message,
#                     Json(extracted_data),
#                     extracted_data.longitude,  # PostGIS takes X (lon) first
#                     extracted_data.latitude,   # PostGIS takes Y (lat) second
#                     severity,
#                     vulnerability
#                 )
#             )
#             conn.commit()
#     except Exception as db_err:
#         if conn:
#             conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Database transaction error: {str(db_err)}")
#     finally:
#         if conn:
#             conn.close()