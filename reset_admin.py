
import getpass
import bcrypt
from database import get_connection

username = "admin"
password = getpass.getpass("Enter NEW admin password: ")

if not password:
    print("Password cannot be empty.")
    raise SystemExit

hashed = bcrypt.hashpw(
    password.encode("utf-8"),
    bcrypt.gensalt()
).decode("utf-8")

conn = get_connection()

try:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET password_hash = %s, is_active = 1, role = 'admin'
            WHERE username = %s
            """,
            (hashed, username)
        )

        if cursor.rowcount == 0:
            print("Admin account not found.")
        else:
            conn.commit()
            print("ADMIN PASSWORD RESET SUCCESSFULLY!")

except Exception as e:
    conn.rollback()
    print("Error:", e)

finally:
    conn.close()
