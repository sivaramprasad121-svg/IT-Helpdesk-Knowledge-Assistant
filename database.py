
import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()

# MySQL configuration
DB_HOST = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("MYSQL_USER") or os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME", "pdf_qa_system")
DB_PORT = int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT", "3306"))


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=DictCursor,
        autocommit=False
    )


def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")

            cursor.execute("SHOW COLUMNS FROM chat_logs LIKE 'pdf_name'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE chat_logs ADD COLUMN pdf_name VARCHAR(255) NULL"
                )

            cursor.execute("SHOW COLUMNS FROM users LIKE 'security_question'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN security_question VARCHAR(255) NULL"
                )

            cursor.execute("SHOW COLUMNS FROM users LIKE 'security_answer_hash'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN security_answer_hash VARCHAR(255) NULL"
                )

        conn.commit()
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s LIMIT 1",
                (username,)
            )
            return cursor.fetchone()
    finally:
        conn.close()


def create_user(username, password_hash, role="user"):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active)
                VALUES (%s, %s, %s, 1)
                """,
                (username, password_hash, role)
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_users():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, role, is_active, created_at
                FROM users
                ORDER BY created_at DESC
                """
            )
            return cursor.fetchall()
    finally:
        conn.close()


def set_user_active(user_id, active):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (1 if active else 0, user_id)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_user_password(username, password_hash):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (password_hash, username)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ==========================================
# ADMIN SECURITY QUESTION FUNCTIONS
# ==========================================

def set_admin_security_question(username, question, answer_hash):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET security_question = %s,
                    security_answer_hash = %s
                WHERE username = %s AND role = 'admin'
                """,
                (question, answer_hash, username)
            )

            if cursor.rowcount == 0:
                raise ValueError("Admin account not found.")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_admin_recovery_data(username):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT username, security_question, security_answer_hash
                FROM users
                WHERE username = %s
                  AND role = 'admin'
                  AND is_active = 1
                LIMIT 1
                """,
                (username,)
            )
            return cursor.fetchone()
    finally:
        conn.close()


def reset_admin_password(username, new_password_hash):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE username = %s AND role = 'admin'
                """,
                (new_password_hash, username)
            )

            if cursor.rowcount == 0:
                raise ValueError("Admin account not found.")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def log_admin_action(admin_id, action, details=""):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_activity_logs (admin_id, action, details)
                VALUES (%s, %s, %s)
                """,
                (admin_id, action, details)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_chat(username, question, answer, pdf_name="", sources="", status="Success"):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s LIMIT 1",
                (username,)
            )
            user = cursor.fetchone()

            if not user:
                raise ValueError("User account not found")

            cursor.execute(
                """
                INSERT INTO chat_logs
                (user_id, document_id, pdf_name, question, answer, sources, status)
                VALUES (%s, NULL, %s, %s, %s, %s, %s)
                """,
                (
                    user["id"],
                    pdf_name,
                    question,
                    answer,
                    sources,
                    status
                )
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_chats():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    u.username,
                    c.pdf_name,
                    c.question,
                    c.answer,
                    c.sources,
                    c.status,
                    c.created_at
                FROM chat_logs c
                INNER JOIN users u ON c.user_id = u.id
                ORDER BY c.created_at DESC
                """
            )
            return cursor.fetchall()
    finally:
        conn.close()
