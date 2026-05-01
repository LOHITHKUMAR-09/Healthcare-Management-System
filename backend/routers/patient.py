from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from database import get_cursor
import os
from twilio.rest import Client
router = APIRouter()
@router.get("/patient/medications/{userid}")
def get_medications(userid: str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT m.medicine_name,
           pm.dosage,
           pm.duration,
           d.name
    FROM prescriptions p
    JOIN prescription_medicines pm
    ON p.prescription_id = pm.prescription_id
    JOIN medicines m
    ON pm.medicine_id = m.medicine_id
    JOIN doctors d
    ON p.doctor_id = d.doctor_id
    WHERE p.patient_id = :1
    """,(userid,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "medicine":row[0],
            "dosage":row[1],
            "duration":row[2],
            "doctor":row[3]
        }
        for row in rows
    ]
@router.post("/patient/cancelAppointment")
def cancel_appointment(data: dict):

    cursor = get_cursor()

    cursor.execute(
        """
        UPDATE appointments
        SET status='CANCELLED'
        WHERE appointment_id=:1
        """,
        (data["appointment_id"],)
    )

    cursor.connection.commit()
    cursor.close()

    return {"message":"Appointment cancelled"}
@router.post("/patient/rescheduleAppointment")
def reschedule_appointment(data: dict):

    cursor = get_cursor()

    cursor.execute(
        """
        UPDATE appointments
        SET appointment_date = TO_DATE(:1,'YYYY-MM-DD'),
            time_slot = :2,
            status = 'RESCHEDULED'
        WHERE appointment_id = :3
        """,
        (
            data["date"],
            data["time_slot"],
            data["appointment_id"]
        )
    )

    cursor.connection.commit()
    cursor.close()

    return {"message": "Appointment rescheduled successfully"}
@router.get("/patient/latestAppointment/{userid}")
def latest_appointment(userid:str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT a.appointment_id,
           d.name,
           d.department,
           TO_CHAR(a.appointment_date,'DD Mon YYYY'),
           a.time_slot,
           d.doctor_id
    FROM appointments a
    JOIN doctors d
    ON a.doctor_id = d.doctor_id
    WHERE a.patient_id=:1
    ORDER BY a.created_at DESC
    FETCH FIRST 1 ROWS ONLY
    """,(userid,))

    row = cursor.fetchone()

    cursor.close()

    if not row:
        raise HTTPException(status_code=404, detail="No appointment found")

    return {
        "appointment_id":row[0],
        "doctor":row[1],
        "department":row[2],
        "date":row[3],
        "time":row[4],
        "doctor_id":row[5]
    }
@router.get("/patient/upcomingAppointments/{userid}")
def get_upcoming_appointments(userid: str):

    cursor = get_cursor()

    cursor.execute(
        """
        SELECT a.appointment_id,
               d.name,
               d.department,
               TO_CHAR(a.appointment_date,'DD Mon YYYY'),
               a.time_slot,
               d.doctor_id
        FROM appointments a
        JOIN doctors d
        ON a.doctor_id = d.doctor_id
        WHERE a.patient_id = :1
        AND a.appointment_date >= TRUNC(SYSDATE)
        ORDER BY a.appointment_date
        """,
        (userid,)
    )

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "appointment_id": row[0],
            "doctor": row[1],
            "department": row[2],
            "date": row[3],
            "time": row[4],
            "doctor_id": row[5]
        }
        for row in rows
    ]
@router.get("/patient/departments")
def get_departments():

    cursor = get_cursor()

    cursor.execute(
        "SELECT department_name FROM departments"
    )

    rows = cursor.fetchall()
    cursor.close()

    return [row[0] for row in rows]

@router.get("/patient/doctors/{department}")
def get_doctors(department: str):

    cursor = get_cursor()

    cursor.execute(
        """
        SELECT doctor_id, name
        FROM doctors
        WHERE department = :1
        """,
        (department,)
    )

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "doctor_id": row[0],
            "name": row[1]
        }
        for row in rows
    ]

@router.get("/patient/availableDates/{doctor_id}")
def get_available_dates(doctor_id: str):

    cursor = get_cursor()

    cursor.execute(
        """
        SELECT DISTINCT
               TO_CHAR(a.appointment_date,'YYYY-MM-DD')
        FROM appointments a
        WHERE a.doctor_id = :1
        """,
        (doctor_id,)
    )

    booked = [row[0] for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT TO_CHAR(leave_date,'YYYY-MM-DD')
        FROM doctor_leaves
        WHERE doctor_id = :1
        """,
        (doctor_id,)
    )

    leaves = [row[0] for row in cursor.fetchall()]

    cursor.close()

    return {
        "booked_dates": booked,
        "leave_dates": leaves
    }

@router.get("/patient/availableSlots/{doctor_id}/{date}")
def get_slots(doctor_id: str, date: str):

    cursor = get_cursor()

    cursor.execute(
        """
        SELECT start_time,end_time
        FROM doctor_availability
        WHERE doctor_id = :1
        AND status='AVAILABLE'
        """,
        (doctor_id,)
    )

    rows = cursor.fetchall()

    slots = []

    for row in rows:
        slots.append(row[0])

    cursor.execute(
        """
        SELECT time_slot
        FROM appointments
        WHERE doctor_id = :1
        AND TO_CHAR(appointment_date,'YYYY-MM-DD')=:2
        """,
        (doctor_id, date)
    )

    booked = [r[0] for r in cursor.fetchall()]

    cursor.close()

    available = [slot for slot in slots if slot not in booked]

    return available

@router.post("/patient/bookAppointment")
def book_appointment(data: dict):

    cursor = get_cursor()

    try:

        # Insert appointment
        cursor.execute(
            """
            INSERT INTO appointments
            (patient_id,
             doctor_id,
             appointment_date,
             time_slot,
             reason,
             status,
             created_at)
            VALUES
            (:1,
             :2,
             TO_DATE(:3,'YYYY-MM-DD'),
             :4,
             :5,
             'PENDING',
             SYSDATE)
            """,
            (
                data["patient_id"],
                data["doctor_id"],
                data["date"],
                data["time_slot"],
                data["reason"]
            )
        )

        # Get patient details
        cursor.execute(
            """
            SELECT name, phone
            FROM patients
            WHERE patient_id = :1
            """,
            (data["patient_id"],)
        )

        patient = cursor.fetchone()
        patient_name = patient[0]
        phone = "+91" + patient[1]

        # Get doctor details
        cursor.execute(
            """
            SELECT name, department
            FROM doctors
            WHERE doctor_id = :1
            """,
            (data["doctor_id"],)
        )

        doctor = cursor.fetchone()
        doctor_name = doctor[0]
        department = doctor[1]

        cursor.connection.commit()

        # Twilio configuration
        account_sid = "ACdeb37d4ccea493a5bbfa29fc53ac52fc"
        auth_token = "33ded110f0f088b1b0a7d3225edc8fb1"

        client = Client(account_sid, auth_token)

        message = f"""
CuraSphere Hospital

Appointment Confirmed

Patient: {patient_name}
Doctor: {doctor_name}
Department: {department}

Date: {data['date']}
Time: {data['time_slot']}

Please arrive 10 minutes early.
"""

        client.messages.create(
            body=message,
            from_="+15015014702",
            to=phone
        )

    finally:
        cursor.close()

    return {"message": "Appointment booked successfully"}

@router.get("/patient/history/{patient_id}")
def get_medical_history(patient_id: str):

    cursor = get_cursor()

    try:

        cursor.execute(
            """
            SELECT CONDITION_NAME,
                   DOCTOR_NAME,
                   DESCRIPTION,
                   STATUS,
                   TO_CHAR(RECORD_DATE,'DD Mon YYYY')
            FROM MEDICAL_HISTORY
            WHERE PATIENT_ID = :pid
            ORDER BY RECORD_DATE DESC
            """,
            {"pid": patient_id}
        )

        rows = cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No medical history found")

    return [
        {
            "condition_name": row[0],
            "doctor_name": row[1],
            "description": row[2],
            "status": row[3],
            "record_date": row[4]
        }
        for row in rows
    ]

@router.get("/patient/emergencyContacts/{userid}")
def get_emergency_contacts(userid: str):

    cursor = get_cursor()

    try:
        cursor.execute(
            """
            SELECT CONTACT_NAME, RELATIONSHIP, CONTACT_TYPE, PHONE_NUMBER
            FROM EMERGENCY_CONTACTS
            WHERE PATIENT_ID = :1
            """,
            (userid,)
        )

        rows = cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No emergency contacts found")

    return [
        {
            "name": row[0],
            "relationship": row[1],
            "type": row[2],
            "phone": row[3]
        }
        for row in rows
    ]


# -----------------------------
# Insurance Claims
# -----------------------------
@router.get("/patient/insuranceClaims/{userid}")
def get_insurance_claims(userid: str):

    cursor = get_cursor()

    try:
        cursor.execute(
            """
            SELECT CLAIM_ID, CLAIM_TYPE, PROVIDER, CLAIM_AMOUNT, STATUS
            FROM INSURANCE_CLAIMS
            WHERE PATIENT_ID = :1
            """,
            (userid,)
        )

        rows = cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No claims found")

    return [
        {
            "claimId": row[0],
            "claimType": row[1],
            "provider": row[2],
            "amount": row[3],
            "status": row[4]
        }
        for row in rows
    ]


# -----------------------------
# Bills
# -----------------------------
@router.get("/patient/bills/{userid}")
def get_patient_bills(userid: str):

    cursor = get_cursor()

    try:
        cursor.execute(
            """
            SELECT BILL_ID,
                   DESCRIPTION,
                   AMOUNT,
                   TO_CHAR(DUE_DATE,'DD Mon YYYY'),
                   STATUS
            FROM BILLS
            WHERE PATIENT_ID = :1 AND STATUS = 'PENDING'
            """,
            (userid,)
        )

        rows = cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No outstanding bills")

    return [
        {
            "bill_id": row[0],
            "description": row[1],
            "amount": row[2],
            "due_date": row[3],
            "status": row[4]
        }
        for row in rows
    ]


# -----------------------------
# Appointment History
# -----------------------------
@router.get("/patient/appointmentHistory/{userid}")
def get_appointment_history(userid: str):

    cursor = get_cursor()

    try:
        cursor.execute(
            """
            SELECT TO_CHAR(a.APPOINTMENT_DATE,'DD Mon YYYY'),
                   d.NAME,
                   d.DEPARTMENT,
                   a.STATUS
            FROM APPOINTMENTS a
            JOIN DOCTORS d
            ON a.DOCTOR_ID = d.DOCTOR_ID
            WHERE a.PATIENT_ID = :1
            ORDER BY a.APPOINTMENT_DATE DESC
            """,
            (userid,)
        )

        rows = cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No appointment history found")

    return [
        {
            "date": row[0],
            "doctor": row[1],
            "department": row[2],
            "status": row[3]
        }
        for row in rows
    ]


# -----------------------------
# Download Lab Report
# -----------------------------
@router.get("/patient/downloadReport/{filename}")
def download_report(filename: str):

    if ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join("reports", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )


# -----------------------------
# Insurance Details
# -----------------------------
@router.get("/patient/insuranceDetails/{userid}")
def get_insDetails(userid: str):

    cursor = get_cursor()

    try:
        cursor.execute(
            """
            SELECT provider,
                   policy_number,
                   coverage_type,
                   sum_insured,
                   TO_CHAR(valid_till,'DD Mon YYYY')
            FROM insurance
            WHERE patient_id = :1
            """,
            (userid,)
        )

        details = cursor.fetchone()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not details:
        raise HTTPException(status_code=404, detail="Insurance details not found")

    return {
        "provider": details[0],
        "policyNumber": details[1],
        "coverageType": details[2],
        "sumInsured": details[3],
        "validTill": details[4]
    }


# -----------------------------
# Lab Records
# -----------------------------
@router.get("/patient/labRecords/{userid}")
def get_lab_records(userid: str):

    cursor = get_cursor()

    try:
        cursor.execute(
            """
            SELECT test_name,
                   lab_name,
                   TO_CHAR(test_date,'DD Mon YYYY'),
                   report_url
            FROM lab_records
            WHERE patient_id = :1
            """,
            (userid,)
        )

        rows = cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No records found")

    return [
        {
            "testName": row[0],
            "labName": row[1],
            "testDate": row[2],
            "report": row[3]
        }
        for row in rows
    ]


# -----------------------------
# Patient Details
# -----------------------------
@router.get("/patient/{userid}")
def get_patient(userid: str):

    cursor = get_cursor()

    try:
        cursor.execute(
            """
            SELECT name,
                   age,
                   gender,
                   blood_group,
                   phone,
                   email
            FROM patients
            WHERE patient_id = :1
            """,
            (userid,)
        )

        user = cursor.fetchone()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()

    if not user:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "name": user[0],
        "age": user[1],
        "gender": user[2],
        "blood_group": user[3],
        "phone": user[4],
        "email": user[5]
    }
@router.get("/patient/paymentHistory/{userid}")
def payment_history(userid: str):

    cursor = get_cursor()

    cursor.execute(
        """
        SELECT bill_id,
               description,
               amount,
               TO_CHAR(due_date,'DD Mon YYYY'),
               status
        FROM bills
        WHERE patient_id = :1
        AND status='PAID'
        ORDER BY due_date DESC
        """,
        (userid,)
    )

    rows = cursor.fetchall()

    cursor.close()

    return [
        {
            "payment_id": row[0],
            "description": row[1],
            "amount": row[2],
            "date": row[3],
            "method": "Online Payment",
            "status": row[4]
        }
        for row in rows
    ]
@router.get("/patient/healthTrends/{userid}")
def get_health_trends(userid:str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT weight,
           height,
           bmi,
           fasting_sugar,
           a1c,
           daily_avg_sugar,
           trend,
           TO_CHAR(record_date,'DD Mon YYYY')
    FROM health_metrics
    WHERE patient_id=:1
    ORDER BY record_date DESC
    FETCH FIRST 1 ROWS ONLY
    """,(userid,))

    row = cursor.fetchone()
    cursor.close()

    if not row:
        raise HTTPException(status_code=404,detail="No health data found")

    return{
        "weight":row[0],
        "height":row[1],
        "bmi":row[2],
        "sugar":row[3],
        "a1c":row[4],
        "daily":row[5],
        "trend":row[6],
        "date":row[7]
    }
@router.post("/patient/emergencyTrigger")
def emergency_trigger(data:dict):

    cursor = get_cursor()

    cursor.execute("""
    INSERT INTO emergency_cases
    (patient_id,status,created_at)
    VALUES
    (:1,'ACTIVE',SYSDATE)
    """,(data["patient_id"],))

    cursor.connection.commit()
    cursor.close()

    return {"message":"Emergency triggered"}
@router.get("/patient/medicines")
def get_medicines():

    cursor = get_cursor()

    cursor.execute("""
        SELECT medicine_id,
               medicine_name,
               description,
               price
        FROM medicines
    """)

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3]
        }
        for row in rows
    ]
@router.post("/patient/orderMedicine")
def order_medicine(data:dict):

    cursor = get_cursor()

    cursor.execute("""
    INSERT INTO medicine_orders
    (order_id,patient_id,medicine_id,quantity,order_date,status)
    VALUES
    (medicine_order_seq.NEXTVAL,:1,:2,:3,SYSDATE,'ORDERED')
    """,
    (
        data["patient_id"],
        data["medicine_id"],
        data["quantity"]
    ))

    cursor.connection.commit()
    cursor.close()

    return {"message":"Medicine ordered"}

@router.get("/patient/orderHistory/{userid}")
def get_order_history(userid: str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT
        mo.order_id,
        TO_CHAR(mo.order_date,'DD Mon YYYY'),
        m.medicine_name,
        m.price,
        mo.quantity,
        mo.status
    FROM medicine_orders mo
    JOIN medicines m
    ON mo.medicine_id = m.medicine_id
    WHERE mo.patient_id = :1
    ORDER BY mo.order_date DESC
    """,(userid,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "order_id": row[0],
            "date": row[1],
            "medicine": row[2],
            "price": row[3],
            "quantity": row[4],
            "status": row[5],
            "total": row[3] * row[4]
        }
        for row in rows
    ]
@router.post("/patient/orderMedicine")
def order_medicine(data:dict):

    cursor = get_cursor()

    try:

        cursor.execute("""
        INSERT INTO medicine_orders
        (patient_id,medicine_id,quantity,order_date,status)
        VALUES
        (:1,:2,:3,SYSDATE,'ORDERED')
        """,
        (
            data["patient_id"],
            data["medicine_id"],
            data["quantity"]
        ))

        cursor.connection.commit()

    finally:
        cursor.close()

    return {"message":"Medicine ordered successfully"}