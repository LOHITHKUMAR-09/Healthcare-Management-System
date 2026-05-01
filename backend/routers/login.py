from fastapi import APIRouter, HTTPException
from utils.security import verify_password
from auth import create_access_token
from database import get_cursor
from schemas import PatientLogin, DoctorLogin

router = APIRouter()


# ---------------- PATIENT LOGIN ----------------

@router.post("/login")
def patient_login(details: PatientLogin):

    cursor = get_cursor()

    cursor.execute(
        "SELECT patient_id, name, password FROM patients WHERE patient_id = :1",
        (details.patient_id,)
    )

    user = cursor.fetchone()
    cursor.close()

    if not user:
        return {"result": "user not found"}

    stored_password = user[2]

    # verify hashed password
    if not verify_password(details.password, stored_password):
        return {"result": "incorrect password"}

    # optional token
    # token = create_access_token({"sub": user[0]})

    return {
        "result": "success"
        # "token": token
    }


# ---------------- DOCTOR LOGIN ----------------

@router.post("/doctor/login")
def doctor_login(details: DoctorLogin):

    cursor = get_cursor()

    cursor.execute(
        "SELECT doctor_id, name, password FROM doctors WHERE doctor_id = :1",
        (details.doctor_id,)
    )

    user = cursor.fetchone()
    cursor.close()

    if not user:
        return {"result": "user not found"}

    stored_password = user[2]

    if not verify_password(details.password, stored_password):
        return {"result": "incorrect password"}

    # optional token
    # token = create_access_token({"sub": user[0]})

    return {
        "result": "success"
        # "token": token
    }