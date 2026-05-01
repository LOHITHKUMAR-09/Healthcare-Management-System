from database import get_cursor
from utils.security import hash_password

cursor = get_cursor()

cursor.execute("SELECT doctor_id, password FROM doctors")
users = cursor.fetchall()

for user in users:
    doctor_id = user[0]
    password = user[1]

    # Skip already hashed passwords
    if password.startswith("$2b$"):
        continue

    hashed = hash_password(password)

    cursor.execute(
        "UPDATE doctors SET password = :1 WHERE doctor_id = :2",
        (hashed, doctor_id)
    )

cursor.connection.commit()
cursor.close()

print("Passwords hashed successfully")