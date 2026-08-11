import os


class Settings:
    kafka = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    topic = os.getenv("TRANSACTIONS_TOPIC", "bank.transactions.v1")
    dlq_topic = os.getenv("DLQ_TOPIC", "bank.transactions.dlq.v1")
    database_url = os.getenv("DATABASE_URL", "postgresql://fraud:fraud@localhost:5432/fraudlake")
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket = os.getenv("MINIO_BUCKET", "fraud-lakehouse")


settings = Settings()

