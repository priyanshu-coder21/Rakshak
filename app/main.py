from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated, Literal
import string
import secrets
from psycopg2.extras import Json
import psycopg2, os
import ollama
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class DistressRequest(BaseModel):
    raw_message: str = Field(..., description='Message of the victim')
    latitude: float = Field(..., ge=-90.0, le=90.0, example=30.3165)
    longitude: float = Field(..., ge=-180.0, le=180.0, example=78.0322)

class DistressResponse(BaseModel):
    token_id: str
    status: str
    extracted_data: dict
    message: str

class RescueRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, example=30.3165)
    longitude: float = Field(..., ge=-180.0, le=180.0, example=78.0322)
    team_capacity: int = Field(..., ge=5)


class RescueResponse(BaseModel):
    team_id: str
    status: Literal['Available', 'In_Transit', 'Assigned']
    message: str



# establish the connection with database
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT")
    )



# token id generation
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




# team_id generation
def team_id_generator(prefix='UK-2026-RES') -> str:
    random_chars = ''.join(
        secrets.choice (string.ascii_uppercase + string.digits)
        for _ in range(4)
    )

    return f"{prefix}-{random_chars}"




def extract_disaster_metrics(text: str) -> dict:
    # Basic tokenization / truncation check for safety limit
    clean_text = " ".join(text.strip().split()[:120])
    
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




# def extract_disaster_metrics(text: str) -> dict:
#     # tokenization
#     clean_text = " ".join(text.strip().split()[:120])








# request going to db by victim
@app.post('/api/distress', response_model=DistressResponse, status_code=201)
def report_distress(distress_data: DistressRequest):

    token_id = token_id_generator()
    extracted_data = extract_disaster_metrics(distress_data.raw_message)
    extracted_json = Json(extracted_data)
    severity = 1
    vulnerability = 1

    conn = None
    cur = None

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
        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database Error. Error: {str(e)}"
        )

    finally:
        if conn:
            conn.close()

    # Return tracking token and parsed metadata to caller
    return DistressResponse(
        token_id=token_id,
        status="Pending",
        extracted_data = extracted_data,
        message="Distress report registered successfully. Keep your tracking token safe."
    )






# get data from Distress table
@app.get('/getDistress')
async def get_distress():

    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()

        query = """
        SELECT *
        FROM DistressTickets
        """
        with connection.cursor() as cursor:
            cursor.execute(query)

            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "token_id" : row[0],
                    "raw_message" : row[1], 
                    "extracted_json" : row[2], 
                    "location" : row[3], 
                    "severity" : row[4], 
                    "vulnerability" : row[5], 
                    "status" : row[6]
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







@app.post('/api/rescue', response_model=RescueResponse, status_code=201)
async def post_rescue(rescue_data:RescueRequest):

    team_id = team_id_generator()

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

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