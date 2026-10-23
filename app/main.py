from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schema import DiseaseInput, HeartInput, DiabetesInput
from app.model import (load_artifacts, get_symptom_list,
                       predict_disease, predict_heart, predict_diabetes)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_artifacts()
    yield


app = FastAPI(title="Swasth Setu ML API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"success": True, "message": "Swasth Setu ML API is running"}


@app.get("/symptoms")
def symptoms():
    return {"symptoms": get_symptom_list()}


@app.post("/predict/disease")
def disease(data: DiseaseInput):
    try:
        return predict_disease(data.symptoms)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/predict/heart")
def heart(data: HeartInput):
    return predict_heart(data.model_dump())


@app.post("/predict/diabetes")
def diabetes(data: DiabetesInput):
    return predict_diabetes(data.model_dump())