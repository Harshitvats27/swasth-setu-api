import json
import os

from dotenv import load_dotenv

load_dotenv()

import firebase_admin
from firebase_admin import auth, credentials, firestore, storage

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"]))
    firebase_admin.initialize_app(cred, {"storageBucket": os.environ["FIREBASE_STORAGE_BUCKET"]})

DB_ID = os.environ.get("FIRESTORE_DATABASE_ID") or None
db = firestore.client(database_id=DB_ID) if DB_ID else firestore.client()
bucket = storage.bucket()
verify_id_token = auth.verify_id_token
# jhgfvcv