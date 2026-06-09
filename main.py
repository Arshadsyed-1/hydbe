from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import mysql.connector
import os
import chromadb
from sentence_transformers import SentenceTransformer

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
@app.get("/feedback/today")
def today_feedback():
    cursor.execute("""
    SELECT * FROM feedback
    WHERE DATE(created_at) = CURDATE()
    ORDER BY feedback_id DESC
    """)

    return cursor.fetchall()


@app.get("/feedback/analyze")
def analyze_feedback():
    cursor.execute("""
    SELECT feedback_type,
           COUNT(*) AS total_feedback,
           ROUND(AVG(rating), 2) AS average_rating
    FROM feedback
    WHERE DATE(created_at) = CURDATE()
    GROUP BY feedback_type
    """)

    return cursor.fetchall()


@app.get("/feedback/ai-summary")
def ai_summary():
    cursor.execute("""
    SELECT * FROM feedback
    WHERE DATE(created_at) = CURDATE()
    ORDER BY feedback_id DESC
    """)

    feedbacks = cursor.fetchall()

    if len(feedbacks) == 0:
        return {"summary": "No feedback available for today"}

    feedback_text = ""

    for item in feedbacks:
        feedback_text += f"""
Name: {item['name']}
Rating: {item['rating']}
Type: {item['feedback_type']}
Message: {item['message']}
"""

    prompt = f"""
You are an AI restaurant quality improvement assistant.

Analyze only today's customer feedback.

Your goal:
Help the restaurant owner understand today's mistakes and improve food quality, taste, and service for tomorrow.

Give the report in this format:

1. Today's Overall Feedback Summary
2. Main Mistakes Today
3. Taste Problems
4. Food Quality Problems
5. Service Problems
6. Customer Appreciations
7. What Should Improve Tomorrow
8. Action Plan for Tomorrow
9. Final Owner Advice

Keep the language simple and practical.

Today's Feedback:
{feedback_text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return {"summary": response.choices[0].message.content}


@app.delete("/feedback/{feedback_id}")
def delete_feedback(feedback_id: int):
    cursor.execute(
        "DELETE FROM feedback WHERE feedback_id=%s",
        (feedback_id,)
    )
    conn.commit()

    return {"message": "Feedback deleted successfully"}
@app.post("/feedback/rag-question")
def rag_question(data: dict):
    question = data["question"]

    question_embedding = embedding_model.encode(question).tolist()

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=5
    )

    related_feedback = results["documents"][0]

    context = "\n\n".join(related_feedback)

    prompt = f"""
You are an AI restaurant assistant.

Answer the owner's question using only the customer feedback below.

Customer Feedback:
{context}

Owner Question:
{question}

Give simple and practical answer.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return {
        "answer": response.choices[0].message.content,
        "related_feedback": related_feedback
    }
