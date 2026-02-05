import cv2
from inference_sdk import InferenceHTTPClient
from collections import Counter
import mysql.connector
from datetime import datetime
import logging
import time
import tempfile
import os

# -------------------------------
# Logging setup
# -------------------------------
logging.basicConfig(
    filename="detector.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------------
# Database connection
# -------------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="David@06",   # change if needed
        database="retail_db"
    )

# -------------------------------
# Initialize tables if not exists
# -------------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        item_name VARCHAR(50) PRIMARY KEY,
        quantity INT,
        price FLOAT DEFAULT 10.0,
        revenue FLOAT DEFAULT 0.0,
        last_updated TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id INT AUTO_INCREMENT PRIMARY KEY,
        item_name VARCHAR(50),
        detected_at TIMESTAMP,
        quantity INT
    )
    """)

    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")

# -------------------------------
# Roboflow Inference Client
# -------------------------------
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="XS8GEW1688EaUrYJzySD"
)

MODEL_ID = "stationery-items-kfybx-uujjr/1"  # your trained model

# -------------------------------
# Run inference using Roboflow
# -------------------------------
def run_inference(frame):
    # Save frame temporarily
    tmp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(tmp_file.name, frame)

    # Run inference
    result = CLIENT.infer(tmp_file.name, model_id=MODEL_ID)

    # Delete temp file
    tmp_path = tmp_file.name
    tmp_file.close()
    os.remove(tmp_path)

    return result

# -------------------------------
# Count items from inference results
# -------------------------------
def estimate_counts(result):
    counter = Counter()
    if "predictions" in result:
        for pred in result["predictions"]:
            item_name = pred["class"].lower()
            counter[item_name] += 1
    return counter

# -------------------------------
# Update DB inventory
# -------------------------------
def update_inventory(counts):
    conn = get_db_connection()
    cursor = conn.cursor()

    for item, qty in counts.items():
        cursor.execute("SELECT price FROM inventory WHERE item_name = %s", (item,))
        row = cursor.fetchone()
        price = row[0] if row else 10.0

        revenue = qty * price

        cursor.execute(
            """
            INSERT INTO inventory (item_name, quantity, price, revenue, last_updated)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                quantity = VALUES(quantity),
                revenue = VALUES(revenue),
                last_updated = VALUES(last_updated)
            """,
            (item, qty, price, revenue, datetime.now())
        )

        cursor.execute(
            "INSERT INTO detections (item_name, detected_at, quantity) VALUES (%s, %s, %s)",
            (item, datetime.now(), qty)
        )

    conn.commit()
    conn.close()

# -------------------------------
# Main loop
# -------------------------------
def main():
    logging.info("Starting shelf stock detector with Roboflow model...")
    init_db()

    cap = cv2.VideoCapture(0)
    last_update = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            logging.warning("Camera frame not captured.")
            break

        # Run Roboflow inference
        result = run_inference(frame)

        # Draw detections on frame
        if "predictions" in result:
            for pred in result["predictions"]:
                x, y, w, h = int(pred["x"]), int(pred["y"]), int(pred["width"]), int(pred["height"])
                cls = pred["class"]
                conf = pred["confidence"]

                # Draw bounding box
                cv2.rectangle(frame, (x - w//2, y - h//2), (x + w//2, y + h//2), (0, 255, 0), 2)
                cv2.putText(frame, f"{cls} {conf:.2f}", (x - w//2, y - h//2 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Update DB every 2 seconds
        t = time.time()
        if t - last_update > 2.0:
            counts = estimate_counts(result)
            if counts:
                update_inventory(counts)
                logging.info(f"Updated inventory with counts: {dict(counts)}")
            last_update = t

        # Show annotated frame
        cv2.imshow("Shelf Detection - Roboflow", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            logging.info("Quit signal received.")
            break

    cap.release()
    cv2.destroyAllWindows()
    logging.info("Detector stopped.")

if __name__== "_main_":
    main()