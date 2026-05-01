from pydantic import BaseModel

class PatientRegister(BaseModel):
    patient_id: str
    name: str
    email: str
    password: str

class PatientLogin(BaseModel):
    patient_id: str
    password: str

class DoctorLogin(BaseModel):
    doctor_id: str
    password: str