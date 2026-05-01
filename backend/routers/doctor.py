from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from database import get_cursor
import os
router = APIRouter()
# @router.get("/doctor/departmentInfo/{doctor_id}")
# def get_department_info(doctor_id: str):

#     cursor = get_cursor()

#     cursor.execute("""
#         SELECT department,
#                specialization,
#                'Chennai Main',
#                'OP-12'
#         FROM doctors
#         WHERE doctor_id = :1
#     """,(doctor_id,))

#     row = cursor.fetchone()
#     cursor.close()

#     if not row:
#         raise HTTPException(status_code=404, detail="Doctor not found")

#     return {
#         "department": row[0],
#         "designation": row[1],
#         "branch": row[2],
#         "room": row[3]
#     }
@router.get("/doctor/todayPatients/{doctor_id}")
def get_today_patients(doctor_id:str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT
        p.name,
        p.age,
        a.reason,
        a.time_slot,
        a.status
    FROM appointments a
    JOIN patients p
    ON a.patient_id = p.patient_id
    WHERE a.doctor_id = :1
    AND TRUNC(a.appointment_date) = TRUNC(SYSDATE)
    ORDER BY a.time_slot
    """,(doctor_id,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "name":row[0],
            "age":row[1],
            "condition":row[2],
            "time":row[3],
            "status":row[4]
        }
        for row in rows
    ]
@router.get("/doctor/upcomingAppointments/{doctor_id}")
def get_upcoming_appointments(doctor_id:str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM appointments
    WHERE doctor_id = :1
    AND appointment_date > SYSDATE
    AND status != 'CANCELLED'
    """,(doctor_id,))

    count = cursor.fetchone()[0]

    cursor.close()

    return {"count":count}
@router.get("/doctor/pendingReports/{doctor_id}")
def pending_reports(doctor_id:str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM lab_test_orders l
    WHERE l.status != 'COMPLETED'
    AND EXISTS (
        SELECT 1
        FROM appointments a
        WHERE a.patient_id = l.patient_id
        AND a.doctor_id = :1
    )
    """,(doctor_id,))

    count = cursor.fetchone()[0]

    cursor.close()

    return {"count":count}
@router.get("/doctor/emergencyCases")
def emergency_cases():

    cursor = get_cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM emergency_cases
    WHERE status = 'ACTIVE'
    """)

    count = cursor.fetchone()[0]

    cursor.close()

    return {"count":count}
@router.post("/doctor/orderLabTest")
def order_lab_test(data:dict):

    cursor = get_cursor()

    cursor.execute("""
    INSERT INTO lab_test_orders
    (patient_id, doctor_id, test_name, order_date, status)
    VALUES
    (:1, :2, :3, SYSDATE, 'REQUESTED')
    """,
    (
        data["patient_id"],
        data["doctor_id"],
        data["test_name"]
    ))

    cursor.connection.commit()
    cursor.close()

    return {"message":"Lab test ordered"}
@router.get("/doctor/labOrders/{doctor_id}")
def get_lab_orders(doctor_id:str):

    cursor = get_cursor()

    cursor.execute("""
    SELECT
        TO_CHAR(l.order_date,'YYYY-MM-DD'),
        p.name,
        l.test_name,
        l.status
    FROM lab_test_orders l
    JOIN patients p
    ON l.patient_id = p.patient_id
    WHERE l.doctor_id = :1
    ORDER BY l.order_date DESC
    FETCH FIRST 10 ROWS ONLY
    """,(doctor_id,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "date":r[0],
            "patient":r[1],
            "test":r[2],
            "status":r[3]
        }
        for r in rows
    ]
@router.get("/doctor/labReports/{doctor_id}")
def get_lab_reports(doctor_id:str, search:str="", test:str=""):

    cursor = get_cursor()

    cursor.execute("""
    SELECT
    TO_CHAR(l.test_date,'YYYY-MM-DD'),
    p.name,
    l.test_name,
    l.status,
    l.report_url
FROM lab_records l
JOIN patients p
    ON l.patient_id = p.patient_id
WHERE EXISTS (
    SELECT 1
    FROM appointments a
    WHERE a.patient_id = l.patient_id
    AND a.doctor_id = :doctor_id
)
AND (
    LOWER(p.name) LIKE '%' || LOWER(:search) || '%'
    OR LOWER(p.patient_id) LIKE '%' || LOWER(:search) || '%'
)
AND (:test = 'All Tests' OR l.test_name = :test)
ORDER BY l.test_date DESC
    """,(doctor_id,search,test))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "date":r[0],
            "patient":r[1],
            "test":r[2],
            "status":r[3],
            "report":r[4]
        }
        for r in rows
    ]
@router.get("/doctor/prescriptionHistory/{doctor_id}")
def prescription_history(doctor_id: str, search: str = ""):

    cursor = get_cursor()

    cursor.execute("""
        SELECT
            TO_CHAR(p.prescription_date,'YYYY-MM-DD'),
            pa.name,
            p.notes,
            LISTAGG(m.medicine_name, ', ') 
                WITHIN GROUP (ORDER BY m.medicine_name)
        FROM prescriptions p
        JOIN patients pa
        ON p.patient_id = pa.patient_id
        LEFT JOIN prescription_medicines pm
        ON p.prescription_id = pm.prescription_id
        LEFT JOIN medicines m
        ON pm.medicine_id = m.medicine_id
        WHERE
        p.doctor_id = :1
        AND (
            LOWER(pa.name) LIKE '%' || LOWER(:2) || '%'
            OR LOWER(pa.patient_id) LIKE '%' || LOWER(:2) || '%'
        )
        GROUP BY p.prescription_date, pa.name, p.notes
        ORDER BY p.prescription_date DESC
    """,(doctor_id, search))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "date":row[0],
            "patient":row[1],
            "diagnosis":"Consultation",
            "medicines":row[3] if row[3] else "-",
            "notes":row[2]
        }
        for row in rows
    ]
@router.post("/doctor/createPrescription")
def create_prescription(data: dict):

    cursor = get_cursor()

    try:

        pres_id = cursor.var(int)

        cursor.execute("""
            INSERT INTO prescriptions
            (patient_id, doctor_id, prescription_date, notes)
            VALUES
            (:1, :2, SYSDATE, :3)
            RETURNING prescription_id INTO :4
        """,
        (
            data["patient_id"],
            data["doctor_id"],
            data["notes"],
            pres_id
        ))

        prescription_id = pres_id.getvalue()[0]

        for med in data["medicines"]:

            cursor.execute("""
INSERT INTO prescription_medicines
(prescription_id, medicine_id, dosage, duration)
VALUES
(:1, :2, :3, :4)
""",
(
    prescription_id,
    med["medicine_id"],
    med["dosage"],
    med["duration"]
))

        cursor.connection.commit()

    finally:
        cursor.close()

    return {"message": "Prescription saved successfully"}
@router.get("/doctor/medicines")
def get_medicines():

    cursor = get_cursor()

    cursor.execute("""
        SELECT medicine_id, medicine_name
        FROM medicines
        ORDER BY medicine_name
    """)

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "id":row[0],
            "name":row[1]
        }
        for row in rows
    ]

@router.get("/doctor/emergencyPatients")
def get_emergency_patients():

    cursor = get_cursor()

    cursor.execute("""
        SELECT
            ec.case_id,
            p.name,
            p.age,
            'Emergency Case',
            'ER-01',
            ec.status,
            TO_CHAR(ec.created_at,'HH:MI AM')
        FROM emergency_cases ec
        JOIN patients p
        ON ec.patient_id = p.patient_id
        WHERE ec.status = 'ACTIVE'
        ORDER BY ec.created_at DESC
    """)

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "case_id":row[0],
            "name":row[1],
            "age":row[2],
            "issue":row[3],
            "location":row[4],
            "priority":row[5],
            "arrived":row[6]
        }
        for row in rows
    ]
@router.get("/doctor/patientHistory/{doctor_id}")
def patient_history(doctor_id: str, search: str = ""):

    cursor = get_cursor()

    cursor.execute("""
SELECT
    TO_CHAR(mh.record_date,'YYYY-MM-DD'),
    p.name,
    mh.condition_name,
    mh.description,
    NVL(m.medicine_name,'-'),
    mh.status
FROM medical_history mh
JOIN patients p
ON mh.patient_id = p.patient_id
LEFT JOIN prescriptions pr
ON pr.patient_id = p.patient_id
LEFT JOIN prescription_medicines pm
ON pm.prescription_id = pr.prescription_id
LEFT JOIN medicines m
ON pm.medicine_id = m.medicine_id
WHERE mh.doctor_id = :1
AND (
    LOWER(p.name) LIKE '%' || LOWER(:2) || '%'
    OR LOWER(p.patient_id) LIKE '%' || LOWER(:2) || '%'
)
ORDER BY mh.record_date DESC
""",(doctor_id, search))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "date":row[0],
            "patient":row[1],
            "condition":row[2],
            "diagnosis":row[3],
            "prescription":row[4],
            "notes":row[5]
        }
        for row in rows
    ]
@router.get("/doctor/activePatients/{doctor_id}")
def get_active_patients(doctor_id: str):

    cursor = get_cursor()

    cursor.execute("""
        SELECT DISTINCT
            p.name,
            p.age,
            mh.condition_name,
            'OP-12',
            TO_CHAR(mh.record_date,'YYYY-MM-DD') AS record_date,
            mh.status
        FROM medical_history mh
        JOIN patients p
            ON mh.patient_id = p.patient_id
        JOIN appointments a
            ON a.patient_id = p.patient_id
        WHERE a.doctor_id = :1
        ORDER BY TO_CHAR(mh.record_date,'YYYY-MM-DD') DESC
    """,(doctor_id,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "name": row[0],
            "age": row[1],
            "condition": row[2],
            "ward": "OP-12",
            "last_visit": row[4],
            "status": row[5]
        }
        for row in rows
    ]
@router.post("/doctor/applyLeave")
def apply_leave(data: dict):

    cursor = get_cursor()

    cursor.execute("""
        INSERT INTO doctor_leaves
        (doctor_id, leave_date, reason, status)
        VALUES
        (:1, TO_DATE(:2,'YYYY-MM-DD'), :3, 'PENDING')
    """,
    (
        data["doctor_id"],
        data["date"],
        data["reason"]
    ))

    cursor.connection.commit()
    cursor.close()

    return {"message":"Leave request submitted"}
@router.get("/doctor/leaves/{doctor_id}")
def get_leaves(doctor_id:str):

    cursor = get_cursor()

    cursor.execute("""
        SELECT
            TO_CHAR(leave_date,'YYYY-MM-DD'),
            reason,
            status
        FROM doctor_leaves
        WHERE doctor_id=:1
        ORDER BY leave_date DESC
    """,(doctor_id,))

    rows = cursor.fetchall()
    cursor.close()

    return[
        {
            "date":row[0],
            "reason":row[1],
            "status":row[2]
        }
        for row in rows
    ]
@router.get("/doctor/weeklySchedule/{doctor_id}")
def get_weekly_schedule(doctor_id: str):

    cursor = get_cursor()

    cursor.execute("""
        SELECT day_of_week,
               start_time,
               end_time,
               status
        FROM doctor_availability
        WHERE doctor_id = :1
        ORDER BY
        CASE day_of_week
            WHEN 'Monday' THEN 1
            WHEN 'Tuesday' THEN 2
            WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4
            WHEN 'Friday' THEN 5
            WHEN 'Saturday' THEN 6
            WHEN 'Sunday' THEN 7
        END
    """,(doctor_id,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "day": row[0],
            "from": row[1],
            "to": row[2],
            "status": row[3]
        }
        for row in rows
    ]
@router.get("/doctor/todayAppointments/{doctor_id}")
def today_appointments(doctor_id: str):

    cursor = get_cursor()

    cursor.execute("""
        SELECT
            a.time_slot,
            p.name,
            p.age,
            a.reason,
            a.status,
            p.patient_id
        FROM appointments a
        JOIN patients p
        ON a.patient_id = p.patient_id
        WHERE a.doctor_id = :1
        AND TRUNC(a.appointment_date) = TRUNC(SYSDATE)
        ORDER BY a.time_slot
    """,(doctor_id,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "time":row[0],
            "patient":row[1],
            "age":row[2],
            "condition":row[3],
            "status":row[4],
            "patient_id":row[5]
        }
        for row in rows
    ]
@router.get("/doctor/availability/{doctor_id}")
def get_doctor_availability(doctor_id: str):

    cursor = get_cursor()

    cursor.execute("""
        SELECT day_of_week,
               start_time,
               end_time
        FROM doctor_availability
        WHERE doctor_id = :1
        AND status = 'AVAILABLE'
        ORDER BY day_of_week
    """,(doctor_id,))

    rows = cursor.fetchall()
    cursor.close()

    return [
        {
            "day": row[0],
            "from": row[1],
            "to": row[2]
        }
        for row in rows
    ]
@router.get("/doctor/{doctor_id}")
def get_doctor(doctor_id: str):

    cursor = get_cursor()

    cursor.execute(
        """
        SELECT name,
               department,
               specialization,
               email
        FROM doctors
        WHERE doctor_id = :1
        """,
        (doctor_id,)
    )

    doctor = cursor.fetchone()
    cursor.close()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    return {
        "name": doctor[0],
        "department": doctor[1],
        "specialization": doctor[2],
        "email": doctor[3]
    }

