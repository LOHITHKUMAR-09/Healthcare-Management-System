from fastapi import FastAPI
from routers import patient, login,doctor
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(patient.router)
app.include_router(login.router)

app.include_router(doctor.router)
@app.get("/")
def home():
    return {"message": "Hospital Management API"}

