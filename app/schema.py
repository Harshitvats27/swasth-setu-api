from pydantic import BaseModel, Field
from typing import List


class DiseaseInput(BaseModel):
    symptoms: List[str] = Field(..., example=["itching", "skin_rash", "nodal_skin_eruptions"])


class HeartInput(BaseModel):
    age: float = Field(..., example=55)
    sex: float = Field(..., example=1)
    cp: float = Field(..., example=0)
    trestbps: float = Field(..., example=130)
    chol: float = Field(..., example=250)
    fbs: float = Field(..., example=0)
    restecg: float = Field(..., example=1)
    thalach: float = Field(..., example=150)
    exang: float = Field(..., example=0)
    oldpeak: float = Field(..., example=1.0)
    slope: float = Field(..., example=1)
    ca: float = Field(..., example=0)
    thal: float = Field(..., example=2)


class DiabetesInput(BaseModel):
    Pregnancies: float = Field(..., example=2)
    Glucose: float = Field(..., example=120)
    BloodPressure: float = Field(..., example=70)
    SkinThickness: float = Field(..., example=20)
    Insulin: float = Field(..., example=80)
    BMI: float = Field(..., example=28.5)
    DiabetesPedigreeFunction: float = Field(..., example=0.5)
    Age: float = Field(..., example=35)