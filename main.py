from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import mysql.connector
import os

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GROQ CLIENT
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# AIVEN MYSQL CONNECTION
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT")),
    ssl_disabled=False
)

cursor = conn.cursor(dictionary=True)

# CREATE TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS feedback(
    feedback_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    rating INT,
    feedback_type VARCHAR(100),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


@app.get("/")
def home():
    return {"message": "AI Restaurant Feedback API is running"}


@app.post("/feedback")
def add_feedback(new_data: dict):
    name = new_data["name"]
    rating = new_data["rating"]
    feedback_type = new_data["feedback_type"]
    message = new_data["message"]

    query = """
    INSERT INTO feedback(name, rating, feedback_type, message)
    VALUES(%s,%s,%s,%s)
    """

    values = (name, rating, feedback_type, message)

    cursor.execute(query, values)
    conn.commit()

    return {"message": "Feedback added successfully"}


@app.get("/feedback")
def get_feedback():

    query = "SELECT * FROM feedback"

    cursor.execute(query)

    result = cursor.fetchall()

    return result

