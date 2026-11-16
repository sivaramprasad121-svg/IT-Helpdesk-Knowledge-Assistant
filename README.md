# IT Helpdesk Knowledge Assistant Using Manual RAG

## 1. Project Overview

The IT Helpdesk Knowledge Assistant is an AI-powered PDF Question Answering application built using Retrieval-Augmented Generation (RAG), Streamlit, FAISS, Google Gemini API, and MySQL.

The application allows users to upload PDF documents and ask questions based on their content. It retrieves relevant information from the uploaded documents and generates context-based answers using Google Gemini.

The system also provides an Admin Dashboard for user management and chat monitoring.

## 2. Technologies Used

- Python
- Streamlit
- MySQL
- PyMySQL
- Google Gemini API
- FAISS
- NumPy
- Pandas
- PyPDF
- Bcrypt
- Python-dotenv

## 3. Key Features

### User Features
- User authentication and login.
- Upload PDF documents.
- Extract text from PDF documents.
- Split extracted text into smaller chunks.
- Generate embeddings using Gemini.
- Retrieve relevant document information using FAISS.
- Ask questions about uploaded documents.
- Receive AI-generated answers based on retrieved content.
- View chat history.

### Admin Features
- Secure Admin Login.
- User management.
- Activate and deactivate users.
- Reset user passwords.
- Monitor user conversations.
- View chat history.
- Monitor admin activities.
- Export chat records when supported by the application.

## 4. Project Folder Structure

```text
IT_Helpdesk_Project/
│
├── .streamlit/
│   └── config.toml
│
├── app.py
├── database.py
├── pdf_loader.py
├── chunking.py
├── embeddings.py
├── vector_store.py
├── retrieval.py
├── gemini_llm.py
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 5. Database Details

The application uses MySQL to store application data.

Database name:

`pdf_qa_system`

Main database tables:

- `users` – Stores user account information and roles.
- `documents` – Stores uploaded document information.
- `user_document_access` – Manages document access for users.
- `chat_logs` – Stores user questions and AI responses.
- `admin_activity_logs` – Stores administrator activities.

The application connects to MySQL using the PyMySQL library.

## 6. Installation and Setup

### Step 1: Install Python

Install Python 3.10 or 3.11.

### Step 2: Create a Virtual Environment

For Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Required Packages

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Install and Start MySQL Server

Install MySQL Server on your computer and make sure the service is running.

MySQL Workbench is optional and can be used to manage and inspect the database.

### Step 5: Create the Database

Open MySQL Workbench and execute:

```sql
CREATE DATABASE IF NOT EXISTS pdf_qa_system;
```

The application's database initialization code creates the required tables.

### Step 6: Configure Environment Variables

Copy `.env.example` and create a new file named `.env` in the project root.

Configure your own credentials:

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=pdf_qa_system
MYSQL_PORT=3306

GEMINI_API_KEY=your_gemini_api_key
```

Use the exact variable names specified in the supplied `.env.example` and application code.

Never share the actual `.env` file or API keys.

### Step 7: Run the Application

Execute:

```powershell
python -m streamlit run app.py
```

Open the URL displayed in the terminal. Usually:

`http://localhost:8501`

## 7. Database Monitoring

Authorized administrators can monitor application records using MySQL Workbench.

Select the database:

```sql
USE pdf_qa_system;
```

View available tables:

```sql
SHOW TABLES;
```

View user records:

```sql
SELECT * FROM users;
```

View uploaded documents:

```sql
SELECT * FROM documents;
```

View chat history:

```sql
SELECT * FROM chat_logs;
```

View administrator activities:

```sql
SELECT * FROM admin_activity_logs;
```

For security, administrators should use separate database accounts with only the required permissions. Do not share the MySQL root password.

## 8. Database Transfer

If the project is installed on another computer:

1. Install MySQL Server.
2. Create the `pdf_qa_system` database.
3. Import the approved SQL database backup if one is provided.
4. Configure the local `.env` file.
5. Install Python dependencies.
6. Start the Streamlit application.

Review database exports before sharing. Remove confidential user information and passwords unless sharing has been explicitly authorized.

## 9. Security Guidelines

- Store credentials in environment variables.
- Never upload `.env` to GitHub.
- Never share database root credentials.
- Use bcrypt password hashing.
- Use parameterized SQL queries.
- Follow role-based access control.
- Do not distribute private user records without authorization.
- Use separate database accounts for application and administrator access.

## 10. Important Notes

- MySQL Server must be running for database operations.
- MySQL Workbench does not need to remain open while the application runs.
- The Gemini API key must be configured for embedding and answer generation.
- FAISS vector indexing is maintained in application memory according to the current implementation. Uploaded PDFs may need to be processed again after an application restart.
- Each system must have its own Python environment and database configuration.
