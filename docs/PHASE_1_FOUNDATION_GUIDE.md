# AI Gym & Fitness Assistant — Phase 1 Foundation Guide

### Complete Beginner → Working Foundation

---

## 1. What This Project Is

### The Vision
The **AI Gym & Fitness Assistant** is an intelligent personal fitness ecosystem designed to help individuals exercise safely, eat healthily, stay motivated, and build lifelong fitness habits.

### The Problem We Are Solving
Most people who start a fitness journey face major hurdles:
1. **Injuries & Bad Form:** In a gym, hiring a personal trainer is expensive, and working out alone often leads to improper exercise form and potential injuries.
2. **Generic Diet Plans:** Most fitness apps give rigid, one-size-fits-all diets that ignore individual preferences, allergies, or cultural cuisines.
3. **Loss of Motivation & Burnout:** People frequently quit after 2–3 weeks because they lack accountability and emotional support.
4. **Disconnected Data:** Workout trackers, calorie counters, and gym machines operate in separate silos rather than working together.

### The Seven Core AI Modules
To address these problems, our master architecture defines seven modular systems:
1. **AI Gym Trainer:** Uses computer vision (OpenCV & MediaPipe) to track body joints in real-time, count repetitions accurately, and correct exercise form.
2. **AI Dietician & Calorie Coach:** An NLP/LLM-powered engine that creates personalized meal plans and grocery lists based on biometric data (BMI, goals, dietary restrictions).
3. **Smart Gym Assistant (AI + IoT):** Integrates with smart gym equipment via MQTT messaging to monitor machine performance and suggest optimal weights and rest intervals.
4. **AI Fitness Habit Tracker (Behavioral AI):** Uses machine learning to detect when a user is likely to skip a workout and delivers adaptive nudges to keep them on schedule.
5. **Virtual Gym Buddy:** A conversational companion with sentiment analysis that provides emotional encouragement, answers workout questions, and prevents burnout.
6. **Pose-to-Performance Analyzer:** Computes comprehensive motion efficiency and symmetry scores to generate longitudinal weekly progress reports.
7. **Gym Recommender & Planner:** Recommends nearby gyms, personalized workout routines, and community fitness challenges.

### Why We Build in Phases
Building an ambitious, multi-module system all at once inevitably leads to unmaintainable, buggy code. We strictly follow the engineering principle:
$$\text{Learn} \longrightarrow \text{Build} \longrightarrow \text{Test} \longrightarrow \text{Integrate} \longrightarrow \text{Document} \longrightarrow \text{Continue}$$

We never reduce the project to a toy prototype or visual mock. Instead, we construct every layer cleanly and verify it before moving to the next.

### What Phase 1 Specifically Achieved
**Phase 1 is the architectural foundation of the entire system.** In Phase 1, we built:
- A production-grade relational database in **PostgreSQL 18** with a clean separation between user authentication credentials and fitness profiles.
- A **FastAPI** backend providing secure password hashing, JSON Web Token (JWT) bearer authentication, and RESTful profile endpoints.
- A **Next.js 15+ / React 19** frontend using the modern App Router, complete with dark-themed Login, Dashboard, and Profile Onboarding interfaces.
- A centralized API configuration layer connecting client and server seamlessly with Cross-Origin Resource Sharing (CORS) security.

> [!IMPORTANT]
> **Phase 1 is strictly the foundation, NOT the complete AI system.** In Phase 1, there are no computer vision models, video processing pipelines, or IoT connections yet. Those modules will be built on top of this verified foundation in Phase 2 and beyond.

---

## 2. Master Plan Position

The following diagram illustrates where Phase 1 sits in our overall development roadmap:

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: User & Profile Foundation              [COMPLETED] │
│ • PostgreSQL 18 Schema (users & profiles)                   │
│ • FastAPI Backend + Security + JWT                          │
│ • Next.js Frontend (Login, Dashboard, Profile Onboarding)   │
│ • Centralized API Configuration + CORS                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Computer Vision & AI Gym Trainer      [NEXT PHASE] │
│ ├── Step 1: Exercise Catalogue & Workout Database Models    │
│ ├── Step 2: OpenCV & MediaPipe Pose Landmark Pipeline       │
│ ├── Step 3: Joint Angle Calculation (Trigonometry)          │
│ ├── Step 4: Exercise State Machines & Repetition Counting   │
│ └── Step 5: Real-Time Form Analysis & Visual Feedback       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Pose-to-Performance Analyzer       [NOT STARTED]   │
│ • Motion efficiency, symmetry, stability scoring            │
│ • Weekly performance reports and aggregation                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: AI Dietician & Calorie Coach       [NOT STARTED]   │
│ • BMI engine, macro targets, LLM meal planning, groceries   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: Virtual Gym Buddy & Sentiment      [NOT STARTED]   │
│ • Conversational LLM with sentiment guardrails              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 6: Behavioral AI & Habit Tracker      [NOT STARTED]   │
│ • Scikit-learn classification for skip prediction           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 7: Gym Recommender & Planner          [NOT STARTED]   │
│ • Content & distance-based recommendation engine            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 8: Smart Gym Assistant (AI + IoT)     [NOT STARTED]   │
│ • MQTT broker, virtual hardware simulator, Node-RED flows   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 9: Analytics, Hardening & Deployment  [NOT STARTED]   │
│ • Plotly/D3 charts, admin analytics, production deployment  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Before We Started

### Development Environment
The baseline environment on our development machine:
* **Operating System:** Windows 11 Home / Pro (64-bit)
* **Code Editor:** Visual Studio Code (VS Code)
* **Python Runtime:** `3.14.2`
* **Node.js Runtime:** `v24.19.0`
* **Package Manager (Node):** `npm 11.17.0`
* **Version Control:** `Git 2.55.0.windows.2`
* **Database Engine:** `PostgreSQL 18.6`
* **Containerization:** Docker was *not* used (all services run natively for rapid iteration and transparent debugging).
* **Project Root Path:** `C:\Users\anand\AI-Gym-Fitness-Assistant`

### Windows PATH Challenges Encountered
During early PostgreSQL setup, running `psql` in PowerShell returned:
```text
'psql' is not recognized as an internal or external command, operable program or batch file.
```

**Why this happened:**  
The standard PostgreSQL Windows installer installs executable binaries into `C:\Program Files\PostgreSQL\18\bin`, but does not automatically add that directory to the Windows System or User `PATH` environment variable.

**How we solved it without risking system stability:**
1. For manual shell interaction, we used the full executable path:
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
   ```
2. For application code and automated migration scripts, we bypassed the need for `psql.exe` entirely by using **Python database drivers (`psycopg` and `SQLAlchemy`)**. Python connects directly to PostgreSQL's native TCP port (`localhost:5432`), which works independently of whether `psql.exe` is in the Windows `PATH`.

---

## 4. Why Each Technology Was Chosen

| Technology | What It Is | Why Our Project Uses It | Project Location | Real-World Analogy |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | High-level programming language | Standard language for AI, computer vision, data analysis, and modern web APIs. | `backend/`, `ml/` | The universal multi-tool in an engineer's workshop. |
| **FastAPI** | Modern, high-performance web API framework for Python | Extremely fast, supports asynchronous requests, automatic validation via Pydantic, and automatic Swagger docs. | `backend/main.py`, `backend/routers/` | An efficient restaurant receptionist who takes orders, validates them, and hands them to the kitchen. |
| **PostgreSQL** | Enterprise-grade open-source relational database | Reliable, ACID-compliant, handles relational integrity (foreign keys, cascading deletes) flawlessly. | Local database service on port `5432` (`ai_gym`) | A secure fireproof filing cabinet organized into labeled drawers and folders. |
| **SQLAlchemy** | Python Object Relational Mapper (ORM) | Allows Python code to interact with database tables using Python classes (`User`, `Profile`) instead of writing raw SQL strings. | `backend/models/`, `backend/database.py` | A professional translator between Python objects and SQL relational tables. |
| **psycopg** | PostgreSQL database adapter for Python | High-performance low-level driver enabling SQLAlchemy and Python to communicate directly with PostgreSQL. | Virtual environment (`.venv`) | The physical copper cable connecting the Python application to the database engine. |
| **Next.js** | React production framework | Provides server-side rendering, folder-based routing (App Router), optimized bundling, and fast client-side navigation. | `frontend/` | The architectural blueprints and electrical wiring that turn raw materials into a luxury building. |
| **React** | Declarative JavaScript library for user interfaces | Lets us build reactive, component-based UIs where views update automatically when state changes. | `frontend/src/app/` | Modular Lego blocks assembled into an interactive dashboard. |
| **TypeScript** | Statically typed superset of JavaScript | Catches bugs, type mismatches, and null pointer exceptions during development before code ever runs. | `frontend/src/**/*.ts`, `*.tsx` | A rigorous spell-checker and grammar inspector for software code. |
| **Tailwind CSS** | Utility-first CSS framework | Rapid styling directly inside JSX/TSX classes without maintaining bloated standalone stylesheet files. | `frontend/src/app/globals.css`, class names | Pre-cut modular building panels that snap directly into place. |
| **JWT (JSON Web Token)** | Stateless cryptographically signed security token | Allows the frontend to prove user identity on protected routes without the backend storing session state in memory. | `backend/auth/token.py` | A tamper-proof digital wristband given at the gym entrance that lets you access member rooms. |
| **Password Hashing (pwdlib / Argon2 / bcrypt)** | One-way mathematical cryptographic hashing | Ensures user passwords are never stored in plaintext. If the database were ever inspected, passwords appear only as uninvertible hashes. | `backend/auth/security.py` | A document shredder that turns a secret recipe into an irreversible fingerprint that can still be verified. |
| **Git** | Distributed version control system | Tracks every single code change, enables safe branching, and allows reverting mistakes without losing work. | `.git/` folder | A time machine for code that records history snapshot by snapshot. |
| **GitHub** | Cloud hosting for Git repositories | Offsite backup, code review collaboration, and continuous integration tracking. | Remote repository | A secure cloud vault and collaboration hub for code history. |
| **Environment Variables** | Configuration key-value pairs kept outside source code | Keeps database passwords, secret keys, and API URLs out of version control so they are never leaked to Git. | `backend/.env`, `frontend/.env.local` | A personal vault combination kept in your pocket, not written on the front door. |
| **REST API** | Architectural style for web services using HTTP | Standardized communication format where frontend uses HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`) to exchange data with backend. | `backend/routers/` | The standard menu and ordering protocol at a drive-through. |
| **JSON** | JavaScript Object Notation | Human-readable text format used to exchange structured data over HTTP. | API request/response payloads | Standardized envelopes for sending letters that any postal service understands. |

---

## 5. Complete Installation & Setup (Step-by-Step)

Follow these exact steps to reproduce Phase 1 on any Windows machine from scratch.

### Step 5.1: Install Prerequisites
1. **Python 3.14+**: Download from `python.org`. Check the box **"Add python.exe to PATH"** before clicking Install.
2. **Node.js (LTS v22 or v24)**: Download from `nodejs.org` and run the installer.
3. **Git for Windows**: Download from `git-scm.com` and use standard defaults.
4. **PostgreSQL 18**: Download from `enterprisedb.com/downloads/postgres-postgresql-downloads`. Set the default superuser password (e.g. `postgres`) and port `5432`.
5. **VS Code**: Download from `code.visualstudio.com`.

Verify installations in PowerShell:
```powershell
python --version   # Expected: Python 3.14.x
node --version     # Expected: v24.x.x
npm --version      # Expected: 11.x.x
git --version      # Expected: git version 2.x.x
```

### Step 5.2: Create Project Root & Initialize Git
```powershell
mkdir C:\Users\anand\AI-Gym-Fitness-Assistant
cd C:\Users\anand\AI-Gym-Fitness-Assistant
git init
```

### Step 5.3: Set Up the Python Backend
Navigate to the backend directory and create a virtual environment:
```powershell
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend
python -m venv .venv

# Activate virtual environment in PowerShell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell shows execution policy restrictions, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

Install the pinned backend dependencies:
```powershell
pip install fastapi uvicorn sqlalchemy psycopg psycopg-binary pwdlib argon2-cffi PyJWT python-dotenv python-multipart pydantic[email]
```

Create `backend/.env` (see Section 10 for template).

### Step 5.4: Initialize the PostgreSQL Database
Create the database `ai_gym` using the PostgreSQL interactive shell:
```sql
CREATE DATABASE ai_gym;
```

Run the database schema creation:
```powershell
python create_tables.py
```

### Step 5.5: Set Up the Next.js Frontend
In a new terminal window:
```powershell
cd C:\Users\anand\AI-Gym-Fitness-Assistant\frontend

# Install dependencies if not already present
npm install
```

Create `frontend/.env.local`:
```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

---

## 6. Project Structure

The verified, current project tree:

```text
AI-Gym-Fitness-Assistant/
├── .git/                      # Git version control metadata
├── .gitignore                 # Files excluded from Git (venv, node_modules, .env)
├── PROJECT_STATE.md           # Master project status and tracking log
│
├── backend/                   # FastAPI Backend (Python)
│   ├── .venv/                 # Isolated Python virtual environment
│   ├── .env                   # Local secrets (Database URL, JWT key - Git ignored)
│   ├── .env.example           # Sanitized environment template for developers
│   ├── main.py                # FastAPI entrypoint, CORS configuration, router mounting
│   ├── database.py            # SQLAlchemy engine, sessionmaker, DeclarativeBase
│   ├── create_tables.py       # Helper script to initialize database tables
│   ├── requirements.txt       # Pinned Python package dependencies
│   │
│   ├── auth/                  # Authentication & cryptographic logic
│   │   ├── security.py        # Password hashing and verification functions
│   │   └── token.py           # JWT token generation and verification
│   │
│   ├── models/                # SQLAlchemy ORM database models
│   │   ├── __init__.py        # Exports User and Profile
│   │   ├── user.py            # User model (id, name, email, password_hash, created_at)
│   │   └── profile.py         # Profile model (user_id PK/FK, height, weight, goal, etc.)
│   │
│   ├── schemas/               # Pydantic data validation schemas
│   │   ├── __init__.py
│   │   └── auth.py            # UserRegister, UserLogin, UserProfileUpdate
│   │
│   └── routers/               # HTTP REST endpoint handlers
│       ├── health.py          # GET /health
│       ├── auth.py            # POST /auth/register, POST /auth/login, /auth/me, /auth/profile
│       └── users.py           # GET /users/me, PUT /users/me
│
├── frontend/                  # Next.js 15+ Frontend (React 19, TypeScript, Tailwind)
│   ├── .env.local             # Local client config (NEXT_PUBLIC_API_URL - Git ignored)
│   ├── package.json           # Node dependencies and npm scripts
│   ├── tsconfig.json          # TypeScript compiler config with @/* path alias
│   │
│   └── src/
│       ├── api/
│       │   └── config.ts      # Centralized API_BASE_URL export
│       │
│       └── app/               # Next.js App Router directory
│           ├── layout.tsx     # Root HTML layout and metadata
│           ├── globals.css    # Global Tailwind styles
│           ├── page.tsx       # Landing page (http://localhost:3000)
│           ├── login/
│           │   └── page.tsx   # Login page (http://localhost:3000/login)
│           ├── dashboard/
│           │   └── page.tsx   # Dashboard page (http://localhost:3000/dashboard)
│           └── profile/
│               └── page.tsx   # Profile & onboarding page (http://localhost:3000/profile)
│
├── ml/                        # Machine Learning & Computer Vision (Reconciled from ai/)
│   └── .gitkeep               # Placeholder for Phase 2 pose/CV models
│
├── iot/                       # IoT Equipment & MQTT Messaging
│   └── .gitkeep               # Placeholder for Phase 8 MQTT simulator
│
├── data/                      # Local datasets and temporary storage
│   └── .gitkeep
│
├── tests/                     # Automated test suites
│   └── .gitkeep
│
└── docs/                      # Technical documentation
    ├── .gitkeep
    └── PHASE_1_FOUNDATION_GUIDE.md  # This comprehensive guide
```

### Folder Implementation Status
* **`backend/`**: **Fully functional.** Active FastAPI server, database connection, JWT auth, and profile endpoints.
* **`frontend/`**: **Fully functional.** Next.js app with working Login, Dashboard, Profile editing, and API client.
* **`docs/`**: **Active.** Contains master architecture and Phase 1 documentation.
* **`ml/`, `iot/`, `data/`, `tests/`**: **Placeholders.** Created to maintain clean project separation; will be populated in subsequent phases.

### Why `.gitkeep` Was Used and Removed
Git by design tracks *files*, not empty directories. If an empty directory is created, Git ignores it completely. To ensure the folder structure exists when another developer clones the repository, developers place an empty file named `.gitkeep` inside empty directories. Once a real file (such as `page.tsx` or a Python script) is added to that directory, `.gitkeep` is no longer needed.

### Documenting the `ai/` $\rightarrow$ `ml/` Reconciliation
In the earliest project step, a directory named `ai/` was initialized with a `.gitkeep`. However, our master implementation guide explicitly defines the folder structure as:
```text
ai-gym-fitness/
  ├── frontend/
  ├── backend/
  ├── ml/              <-- Pose, behavior, and recommendation models
  │     ├── pose/
  │     ├── behavior/
  │     └── recommendation/
  ├── iot/
  ...
```
To maintain 100% strict compliance with the master guide, the directory was renamed from `ai/` to `ml/`. Because it contained only `.gitkeep`, no code or functionality was modified or lost.

---

## 7. Git & Version Control Foundation

### Key Concepts
* **Repository (Repo):** The complete database of project files and their revision history stored in `.git/`.
* **Commit:** A permanent snapshot of your project at a specific point in time with a descriptive message and author signature.
* **Working Tree:** The actual physical files you see and edit on your disk.
* **Staging Area (`git add`):** The preparation zone where changes are reviewed before being committed.
* **`.gitignore`:** A text file listing file patterns that Git must never track (virtual environments, cache files, build artifacts, and secret keys).

### Why Secrets Must NEVER Be Committed
If a `.env` file containing database passwords or cryptographic JWT secrets is committed to Git, it becomes baked into the Git commit history forever. Even if deleted in a later commit, anyone with repository access can inspect past commits and steal the credentials.

### Our `.gitignore` Rule Refinement
During Phase 1, we noticed that a generic rule `models/` (intended to ignore heavy machine-learning binary model checkpoints like `*.joblib` or `*.pkl`) was accidentally ignoring our Python source directory `backend/models/profile.py`.

We refined `.gitignore` with an explicit negation rule:
```gitignore
*.joblib
*.pkl
models/
!backend/models/
```
This ensures large trained model weights are ignored, while our application source code in `backend/models/` is properly tracked.

---

## 8. Python Backend Foundation

### Backend Architecture Flow
Incoming client requests travel through a clean, unidirectional pipeline:

```
[ HTTP Request from Browser / Next.js ]
                    │
                    ▼
          [ backend/main.py ]
          (CORS Middleware Check)
                    │
                    ▼
          [ backend/routers/ ]
   (/health, /auth, /users endpoints)
                    │
                    ▼
           [ Authentication ]
    (verify_access_token & get_current_user)
                    │
                    ▼
         [ Pydantic Schemas ]
       (Validate request payload)
                    │
                    ▼
        [ SQLAlchemy 2.0 ORM ]
       (User & Profile entities)
                    │
                    ▼
           [ psycopg Driver ]
                    │
                    ▼
         [ PostgreSQL 18 Database ]
```

### Key Backend Files & Responsibilities

1. **`backend/main.py`**:
   * Initializes the `FastAPI` instance.
   * Configures `CORSMiddleware` to allow requests originating from `http://localhost:3000`.
   * Mounts `health_router`, `auth_router`, and `users_router`.
   * Exposes the root route (`GET /`).

2. **`backend/database.py`**:
   * Reads `DATABASE_URL` from the `.env` file.
   * Automatically adapts the URL prefix to `postgresql+psycopg://` to use the modern `psycopg` driver.
   * Defines `Base(DeclarativeBase)` as the parent class for all models.
   * Exports `SessionLocal = sessionmaker(bind=engine)` for database session management.

3. **`backend/models/user.py`**:
   * Defines the `User` SQLAlchemy model mapped to the `users` table.
   * Stores authentication identity: `id`, `name`, `email`, `password_hash`, `created_at`.
   * Defines the one-to-one relationship: `profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")`.

4. **`backend/models/profile.py`**:
   * Defines the `Profile` model mapped to the `profiles` table.
   * Defines `user_id` as both **Primary Key** and **Foreign Key** referencing `users.id` with `ondelete="CASCADE"`.
   * Stores physical metrics: `date_of_birth`, `gender`, `height_cm`, `weight_kg`, `fitness_goal`, `activity_level`, `dietary_preference`.
   * Back-populates `user = relationship("User", back_populates="profile")`.

5. **`backend/auth/security.py`**:
   * Uses `pwdlib.PasswordHash.recommended()` (Argon2/bcrypt) to hash passwords securely upon registration.
   * Provides `verify_password(plain, hashed)` to validate passwords during login.

6. **`backend/auth/token.py`**:
   * Reads `JWT_SECRET_KEY`, `JWT_ALGORITHM` ("HS256"), and `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).
   * Generates signed JWT tokens: `create_access_token(user_id)`.
   * Validates tokens and extracts `user_id`: `verify_access_token(token)`. Raises HTTP 401 if invalid or expired.

7. **`backend/routers/auth.py`**:
   * Provides `POST /auth/register` (creates user with hashed password).
   * Provides `POST /auth/login` (verifies credentials via OAuth2 form data and issues JWT).
   * Provides `get_current_user` dependency for route protection.
   * Provides backward-compatibility aliases: `GET /auth/me` and `PUT /auth/profile`.

8. **`backend/routers/users.py`**:
   * Implements the Master Implementation Guide endpoints:
     * `GET /users/me`: Returns the authenticated user's account and profile information.
     * `PUT /users/me`: Updates an existing profile or creates a new profile record if one does not exist.

---

## 9. Database Foundation

### Relational Architecture & Entity-Relationship Diagram
Our database schema cleanly separates user account authentication from fitness health metrics:

```
 ┌─────────────────────────────────────────┐
 │                  USERS                  │
 ├─────────────────────────────────────────┤
 │  id             : INTEGER (PK, Autoincrement)
 │  name           : VARCHAR(100) NOT NULL │
 │  email          : VARCHAR(255) UNIQUE   │
 │  password_hash  : VARCHAR(255) NOT NULL │
 │  created_at     : TIMESTAMP NOT NULL    │
 └────────────────────┬────────────────────┘
                      │
                      │ 1-to-1 Relationship
                      │ (Foreign Key: user_id → users.id)
                      │ (ON DELETE CASCADE)
                      ▼
 ┌─────────────────────────────────────────┐
 │                PROFILES                 │
 ├─────────────────────────────────────────┤
 │  user_id            : INTEGER (PK, FK)  │
 │  date_of_birth      : TIMESTAMP NULL    │
 │  gender             : VARCHAR(50) NULL  │
 │  height_cm          : DOUBLE PRECISION  │
 │  weight_kg          : DOUBLE PRECISION  │
 │  fitness_goal       : VARCHAR(100) NULL │
 │  activity_level     : VARCHAR(50) NULL  │
 │  dietary_preference : VARCHAR(100) NULL │
 └─────────────────────────────────────────┘
```

### Architectural Concepts Explained
* **Primary Key (PK):** A column that uniquely identifies every single row in a table. In `users`, `id` is the PK.
* **Foreign Key (FK):** A column in one table that points to the Primary Key in another table, guaranteeing relational integrity.
* **1-to-1 Relationship (`user_id` as PK and FK):** By making `profiles.user_id` both the Foreign Key pointing to `users.id` AND the Primary Key of `profiles`, the database engine strictly guarantees that a user can have at most **one** profile. It is physically impossible to create duplicate profiles for the same user.
* **Cascading Delete (`ON DELETE CASCADE`):** If a user deletes their account from `users`, PostgreSQL automatically purges their associated `profiles` row. No orphan records are left in the database.

---

## 10. Environment Variables & Secrets

### Client vs. Server Exposure Rules
* **Backend Secrets (`backend/.env`):** Only accessible to the backend Python process. **NEVER** exposed to the public browser.
* **Frontend Variables (`frontend/.env.local`):** Next.js exposes variables to the browser **ONLY** if they are prefixed with `NEXT_PUBLIC_`. 

### Backend `.env.example` Template
```env
# Database connection string
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ai_gym

# JWT Security Configuration
JWT_SECRET_KEY=generate-a-secure-random-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### Frontend `.env.local` Template
```env
# Exposed to client-side fetch calls in Next.js
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

---

## 11. Authentication & Security Flow

### 1. Registration Flow
```
User enters Name, Email, Password
            │
            ▼
POST http://127.0.0.1:8000/auth/register
            │
            ▼
FastAPI checks if Email already exists in DB
   ├── Exists: Returns HTTP 409 Conflict
   └── Unique: Hashes password with Argon2/bcrypt
            │
            ▼
Saves new row to `users` table
            │
            ▼
Returns 200 OK: {"message": "User registered successfully", "id": 1, ...}
```

### 2. Login Flow
```
User enters Email and Password
            │
            ▼
POST http://127.0.0.1:8000/auth/login (OAuth2 Form Data)
            │
            ▼
FastAPI queries `users` by email
   ├── Not found: Returns HTTP 401 Unauthorized
   └── Found: Compares password against stored password_hash
            │
            ▼
Hashes match?
   ├── No: Returns HTTP 401 Unauthorized
   └── Yes: Generates JWT token with claims: {"sub": user_id, "exp": ...}
            │
            ▼
Returns 200 OK: {"access_token": "eyJhbGci...", "token_type": "bearer"}
            │
            ▼
Next.js client stores token in localStorage("access_token")
```

### 3. Protected Request Flow (e.g., Loading Profile)
```
Next.js loads /dashboard or /profile
            │
            ▼
Reads token from localStorage.getItem("access_token")
   ├── No token: router.push("/login")
   └── Token exists:
            │
            ▼
Sends GET http://127.0.0.1:8000/users/me
Header: "Authorization: Bearer eyJhbGci..."
            │
            ▼
FastAPI dependency `get_current_user`:
   ├── Verifies signature using JWT_SECRET_KEY
   ├── Checks expiration timestamp
   ├── Extracts user_id from "sub" claim
   └── Queries user from database
            │
            ▼
Token invalid or expired?
   ├── Yes: Returns HTTP 401 Unauthorized
   │        (Client removes token and redirects to /login)
   └── Valid: Returns User + Profile JSON to frontend
```

---

## 12. Actual API Endpoints (Phase 1 Catalogue)

### 1. Root & Health
* **`GET /`**
  * **Auth Required:** No
  * **Response:** `{"message": "AI Gym & Fitness Assistant API is running"}`
* **`GET /health`**
  * **Auth Required:** No
  * **Response:** `{"status": "healthy"}`

### 2. Authentication
* **`POST /auth/register`**
  * **Auth Required:** No
  * **Request Body:**
    ```json
    {
      "name": "Anand Test",
      "email": "anand@example.com",
      "password": "SecurePassword123!"
    }
    ```
  * **Response (200 OK):**
    ```json
    {
      "message": "User registered successfully",
      "id": 2,
      "name": "Anand Test",
      "email": "anand@example.com"
    }
    ```
  * **Error (409 Conflict):** `{"detail": "Email already registered"}`

* **`POST /auth/login`**
  * **Auth Required:** No
  * **Request Format:** `application/x-www-form-urlencoded`
  * **Fields:** `username=anand@example.com&password=SecurePassword123!`
  * **Response (200 OK):**
    ```json
    {
      "message": "Login successful",
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```
  * **Error (401 Unauthorized):** `{"detail": "Invalid email or password"}`

### 3. User & Profile Management
* **`GET /users/me`** (Master Guide Endpoint) & **`GET /auth/me`** (Compatibility Alias)
  * **Auth Required:** Yes (`Authorization: Bearer <token>`)
  * **Response (200 OK):**
    ```json
    {
      "id": 2,
      "name": "Anand Test",
      "email": "anand@example.com",
      "date_of_birth": "2007-01-15T00:00:00",
      "gender": "male",
      "height_cm": 175.0,
      "weight_kg": 70.0,
      "fitness_goal": "muscle_gain",
      "activity_level": "moderately_active",
      "dietary_preference": "vegetarian"
    }
    ```
  * **Error (401 Unauthorized):** `{"detail": "Invalid token"}`

* **`PUT /users/me`** (Master Guide Endpoint) & **`PUT /auth/profile`** (Compatibility Alias)
  * **Auth Required:** Yes (`Authorization: Bearer <token>`)
  * **Request Body:**
    ```json
    {
      "date_of_birth": "2007-01-15",
      "gender": "male",
      "height_cm": 176.0,
      "weight_kg": 71.5,
      "fitness_goal": "muscle_gain",
      "activity_level": "very_active",
      "dietary_preference": "vegetarian"
    }
    ```
  * **Response (200 OK):**
    ```json
    {
      "message": "Profile updated successfully",
      "profile": {
        "id": 2,
        "name": "Anand Test",
        "email": "anand@example.com",
        "date_of_birth": "2007-01-15T00:00:00",
        "gender": "male",
        "height_cm": 176.0,
        "weight_kg": 71.5,
        "fitness_goal": "muscle_gain",
        "activity_level": "very_active",
        "dietary_preference": "vegetarian"
      }
    }
    ```

---

## 13. Frontend Foundation

### Next.js App Router Architecture
Next.js uses a file-system-based router located inside `frontend/src/app`. Each directory represents a route segment, and a `page.tsx` file defines the user interface for that route:

* **`/` (`frontend/src/app/page.tsx`):** Root landing page introducing the application.
* **`/login` (`frontend/src/app/login/page.tsx`):** Interactive authentication form. Validates credentials, saves the JWT in `localStorage`, and redirects to `/dashboard`.
* **`/dashboard` (`frontend/src/app/dashboard/page.tsx`):** Displays user metrics (height, weight, goal, activity level) loaded dynamically from `GET /users/me`. Includes an **"Edit Profile"** button and a **"Logout"** button.
* **`/profile` (`frontend/src/app/profile/page.tsx`):** Onboarding and profile editing interface. Pre-fills existing data from `GET /users/me` and persists updates via `PUT /users/me`.

---

## 14. Frontend $\leftrightarrow$ Backend Connection & CORS

### Centralized API Configuration
Instead of hardcoding `"http://127.0.0.1:8000"` across multiple UI components, we centralized the backend URL in `frontend/src/api/config.ts`:

```typescript
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
```

All fetch calls import and use `API_BASE_URL`:
```typescript
fetch(`${API_BASE_URL}/users/me`, { ... })
```

**Why this is crucial:** When deploying to production (e.g., AWS, Vercel, or a custom domain), we only need to change the environment variable `NEXT_PUBLIC_API_URL` rather than hunting down hardcoded strings in dozens of source files.

### Cross-Origin Resource Sharing (CORS)
* **The Problem:** By default, web browsers enforce the **Same-Origin Policy** for security. Because our frontend runs on `http://localhost:3000` and our backend runs on `http://127.0.0.1:8000`, the browser treats them as two completely different origins. When the frontend attempts to call the backend, the browser blocks the response with a CORS error.
* **The Fix:** In `backend/main.py`, we configured FastAPI's built-in `CORSMiddleware`:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  This instructs the backend to send standard HTTP headers (`Access-Control-Allow-Origin: http://localhost:3000`) telling the browser that requests from our frontend are authorized.

---

## 15. Profile & Onboarding Lifecycle

### How Profile Management Works
1. **New User Registration:** When a user registers, an account record is inserted into `users`. The user does not yet have a profile.
2. **First Visit to Profile / Dashboard:**
   * Calling `GET /users/me` detects that `user.profile` is `None`. The API cleanly returns `null` for all physical metrics (`height_cm`, `weight_kg`, etc.) without raising an error.
   * The user is presented with the profile onboarding form.
3. **Saving the Profile:**
   * The client sends a `PUT /users/me` request.
   * The backend checks if a profile exists for this `user_id`. Since none exists, it creates a new `Profile` instance linked to the user's `id` and commits it to the `profiles` table.
4. **Subsequent Profile Updates:**
   * The client sends another `PUT /users/me` request with new values.
   * The backend detects that a `Profile` already exists for this `user_id`, updates the attributes in place, and commits the changes.
   * **Zero duplicate profiles** are ever created.

---

## 16. Real Problems Encountered & How We Solved Them

### Problem 1: `psql` Command Not Recognized in PowerShell
* **Why it happened:** PostgreSQL installer on Windows does not automatically append `C:\Program Files\PostgreSQL\18\bin` to the user's `PATH`.
* **Diagnosis:** Running `psql -U postgres` failed with command-not-found.
* **Fix:** We relied on direct Python drivers (`psycopg` and `SQLAlchemy`) for all programmatic migrations and schema creation over TCP port 5432.
* **Verification:** `python create_tables.py` and `python step_2a_migration.py` executed successfully.
* **Lesson Learned:** Modern applications should never depend on manual CLI database utilities for their automated setup.

### Problem 2: Frontend "Failed to fetch" on Login
* **Why it happened:** The Next.js client attempted to send an HTTP request to `http://127.0.0.1:8000/auth/login`, but the FastAPI backend was not running or CORS blocked the request.
* **Diagnosis:** Inspected browser console; saw `ERR_CONNECTION_REFUSED` or CORS preflight failures.
* **Fix:** Started the backend server via `uvicorn main:app --reload` and added `CORSMiddleware` to `backend/main.py`.
* **Verification:** Submitting the login form successfully received an `access_token`.
* **Lesson Learned:** Always start the backend server before testing the frontend and ensure CORS headers are active.

### Problem 3: Next.js Environment Variable Not Loaded
* **Why it happened:** We created `frontend/.env.local` while the Next.js development server (`npm run dev`) was already actively running. Next.js reads `.env.local` only upon process startup.
* **Diagnosis:** The frontend fell back to default string configurations.
* **Fix:** Restarted the Next.js server (`Ctrl+C` followed by `npm run dev`).
* **Verification:** `process.env.NEXT_PUBLIC_API_URL` successfully evaluated to `"http://127.0.0.1:8000"`.
* **Lesson Learned:** Whenever environment files (`.env` or `.env.local`) are added or edited, restart the running process immediately.

### Problem 4: Git Ignored `backend/models/profile.py`
* **Why it happened:** The root `.gitignore` had a generic line `models/` intended for binary ML weights. Git applied this rule globally to any directory named `models/`, including our backend source code.
* **Diagnosis:** Running `git status` did not show `backend/models/profile.py` as an untracked file. Running `git check-ignore -v backend/models/profile.py` identified line 125 of `.gitignore`.
* **Fix:** Added a selective un-ignore rule: `!backend/models/` in `.gitignore`.
* **Verification:** `git status` immediately tracked `backend/models/profile.py`.
* **Lesson Learned:** Always be specific with `.gitignore` paths when directory names could collide with application code.

### Problem 5: PowerShell Script Execution Policy Blocking `npx`
* **Why it happened:** Windows PowerShell restricts running unverified `.ps1` wrapper scripts (such as `npx.ps1`).
* **Diagnosis:** Running `npx tsc --noEmit` threw a `PSSecurityException`.
* **Fix:** Executed commands via `cmd.exe /c "npx tsc --noEmit"` or updated PowerShell's ExecutionPolicy to `RemoteSigned`.
* **Verification:** TypeScript compilation ran cleanly and returned exit code 0.
* **Lesson Learned:** On Windows environments, executing Node binaries through standard CMD handles execution policies seamlessly.

---

## 17. Verification & Testing

Every single component in Phase 1 was verified using live automated test scripts executed against the live PostgreSQL database and running servers:

1. **Backend Health Verification:**
   `GET /health` returns HTTP 200 with `{"status": "healthy"}`.
2. **Registration & Password Hashing Verification:**
   Registered test accounts and verified via SQL that passwords are stored strictly as Argon2/bcrypt hashes beginning with `$argon2` or `$2b$`. Plaintext passwords never exist in the database.
3. **JWT Authentication & Token Security:**
   Verified that valid logins receive an signed access token. Verified that requests with missing, corrupted, or tampered tokens return **HTTP 401 Unauthorized**.
4. **Relational Integrity & Zero Duplication:**
   Verified via SQL join queries that `users` and `profiles` maintain strict 1-to-1 cardinality (`COUNT(*) FROM users == COUNT(*) FROM profiles`) and that deleting a test user cascades and deletes the profile.
5. **Static TypeScript Checking:**
   Executed `npx tsc --noEmit` across all frontend code (`src/**/*.ts`, `src/**/*.tsx`). Passed with **0 errors and 0 warnings**.
6. **Frontend Route Availability:**
   Tested HTTP GET responses for all four client routes:
   * `http://localhost:3000/` $\rightarrow$ **200 OK**
   * `http://localhost:3000/login` $\rightarrow$ **200 OK**
   * `http://localhost:3000/dashboard` $\rightarrow$ **200 OK**
   * `http://localhost:3000/profile` $\rightarrow$ **200 OK**
7. **Profile Persistence & State Retention:**
   Updated profile metrics (height, weight, goals, dietary preference) via the `/profile` UI, refreshed the browser, and verified that all updated data persisted accurately from PostgreSQL.

---

## 18. Current Project State

| Component / Layer | Status | Notes |
| :--- | :---: | :--- |
| **Git Repository** | ✅ Complete | Initialized, structured, and cleanly tracked. |
| **Python 3.14 Environment** | ✅ Complete | Isolated virtual environment in `backend/.venv` with pinned packages. |
| **FastAPI Backend** | ✅ Complete | Modular routers (`health`, `auth`, `users`) with CORS support. |
| **PostgreSQL 18 Database** | ✅ Complete | Relational schema (`users` & `profiles`) running on port 5432. |
| **SQLAlchemy 2.0 Models** | ✅ Complete | Type-annotated `User` and `Profile` models with 1-to-1 cascade. |
| **Authentication & Security** | ✅ Complete | Passwords hashed with Argon2/bcrypt; stateless JWT bearer tokens. |
| **Next.js 15+ Frontend** | ✅ Complete | Modern App Router, TypeScript, and responsive Tailwind dark mode. |
| **Login Route (`/login`)** | ✅ Complete | Fully connected to `POST /auth/login`. |
| **Dashboard Route (`/dashboard`)** | ✅ Complete | Dynamically loads and displays profile data from `GET /users/me`. |
| **Profile Onboarding (`/profile`)** | ✅ Complete | Fully connected to `GET /users/me` and `PUT /users/me`. |
| **API Configuration Layer** | ✅ Complete | Centralized `API_BASE_URL` with `.env.local` fallback. |
| **Module 1: AI Gym Trainer** | 🟡 Planned | Next phase (OpenCV, MediaPipe, joint angles, rep counting). |
| **Module 2: AI Dietician & Calorie Coach** | 🟡 Planned | Scheduled for Phase 4. |
| **Module 3: Smart Gym Assistant (IoT)** | 🟡 Planned | Scheduled for Phase 8 (MQTT / Node-RED). |
| **Module 4: AI Fitness Habit Tracker** | 🟡 Planned | Scheduled for Phase 6 (scikit-learn). |
| **Module 5: Virtual Gym Buddy** | 🟡 Planned | Scheduled for Phase 5 (LLM / NLP). |
| **Module 6: Pose-to-Performance Analyzer**| 🟡 Planned | Scheduled for Phase 3. |
| **Module 7: Gym Recommender & Planner** | 🟡 Planned | Scheduled for Phase 7. |
| **Advanced Analytics & Charts** | 🟡 Planned | Scheduled for Phase 9 (Plotly / D3.js). |
| **Production Cloud Deployment** | 🟡 Planned | Scheduled for Phase 9. |

---

## 19. How to Run the Project (Step-by-Step)

To run the complete system on your local machine, open two separate terminal windows in VS Code:

### Terminal 1: Backend (FastAPI)
```powershell
# 1. Navigate to backend directory
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend

# 2. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Start the FastAPI development server
uvicorn main:app --reload --port 8000
```
*The backend API will be live at `http://127.0.0.1:8000` (Interactive API docs at `http://127.0.0.1:8000/docs`).*

### Terminal 2: Frontend (Next.js)
```powershell
# 1. Navigate to frontend directory
cd C:\Users\anand\AI-Gym-Fitness-Assistant\frontend

# 2. Start the Next.js development server
npm run dev
```
*The frontend web application will be live at `http://localhost:3000`.*

### Testing the User Flow in Your Browser
1. Open your web browser to **`http://localhost:3000/login`**.
2. Log in with your registered credentials (e.g. `anand@example.com` or test account).
3. The browser will redirect you to the **Dashboard** (`http://localhost:3000/dashboard`), displaying your current profile metrics.
4. Click the **"Edit Profile"** button in the top right.
5. Update your height, weight, fitness goal, or dietary preference on **`http://localhost:3000/profile`**.
6. Click **"Save Profile"**. A green confirmation alert will appear.
7. Click **"Return to Dashboard"** or refresh the page to verify that your updated metrics are permanently saved in PostgreSQL!

---

### 19.1 Master Terminal Command Reference (Complete Cheat Sheet)

Below is the exhaustive, copy-paste reference of **every single terminal command** used throughout Phase 1, categorized by operational domain:

#### A. Toolchain Version Checks
```powershell
# Verify Python runtime
python --version

# Verify Node.js runtime
node --version

# Verify npm package manager
npm --version

# Verify Git version control
git --version
```

#### B. Git Repository Initialization & Tracking
```powershell
# Create and enter the project root directory
mkdir C:\Users\anand\AI-Gym-Fitness-Assistant
cd C:\Users\anand\AI-Gym-Fitness-Assistant

# Initialize Git repository
git init

# Check working tree and modified/untracked files
git status

# Stage specific files
git add <filename>

# Stage all tracked and untracked changes
git add .

# Commit staged changes with message
git commit -m "Commit message"

# View concise commit history log
git log --oneline

# Inspect why a specific file is ignored by .gitignore
git check-ignore -v <filepath>

# Reconcile directory name from ai/ to ml/
Rename-Item -Path "C:\Users\anand\AI-Gym-Fitness-Assistant\ai" -NewName "ml"
```

#### C. Python Backend Virtual Environment & Package Management
```powershell
# Navigate to backend directory
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend

# Create isolated Python virtual environment
python -m venv .venv

# Activate virtual environment in PowerShell
.\.venv\Scripts\Activate.ps1

# (If PowerShell blocks script activation, permit signed local scripts)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Upgrade pip package installer
python -m pip install --upgrade pip

# Install all backend packages directly
pip install fastapi uvicorn sqlalchemy psycopg psycopg-binary pwdlib argon2-cffi PyJWT python-dotenv python-multipart pydantic[email]

# Or install from pinned requirements file
pip install -r requirements.txt

# Freeze installed packages into requirements.txt
pip freeze > requirements.txt
```

#### D. PostgreSQL Database Setup & Migrations
```powershell
# Connect directly to PostgreSQL interactive terminal using full binary path
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
```

Inside PostgreSQL shell (`psql`):
```sql
-- Create the project database
CREATE DATABASE ai_gym;

-- Connect to the ai_gym database
\c ai_gym;

-- List all tables in current database
\dt

-- Inspect columns and constraints of users table
\d users

-- Inspect columns and constraints of profiles table
\d profiles

-- Query user records
SELECT id, name, email, password_hash FROM users;

-- Query profile records
SELECT user_id, height_cm, weight_kg, fitness_goal FROM profiles;

-- Verify relational join
SELECT u.id, u.name, u.email, p.height_cm, p.weight_kg, p.fitness_goal
FROM users u
JOIN profiles p ON u.id = p.user_id;

-- Exit PostgreSQL interactive shell
\q
```

Automated Python Database Scripts:
```powershell
# Ensure virtual environment is active in backend/
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend
.\.venv\Scripts\Activate.ps1

# Run initial table creation script
python create_tables.py

# Run Step 2A database migration (creates profiles table & copies existing user data)
python step_2a_migration.py
```

#### E. Starting Servers (Live Execution)
```powershell
# TERMINAL 1 — Run FastAPI Backend (starts server on port 8000 with auto-reload)
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000

# TERMINAL 2 — Run Next.js Frontend (starts dev server on port 3000)
cd C:\Users\anand\AI-Gym-Fitness-Assistant\frontend
npm run dev
```

#### F. Frontend Dependencies & Build Verification
```powershell
# Navigate to frontend directory
cd C:\Users\anand\AI-Gym-Fitness-Assistant\frontend

# Install all npm dependencies
npm install

# Run static TypeScript compiler check (zero emit)
npx tsc --noEmit

# (If PowerShell execution policy blocks npx.ps1, use CMD wrapper)
cmd.exe /c "npx tsc --noEmit"

# Verify production Next.js build
npm run build
```

#### G. Automated Verification Test Suites
```powershell
# Navigate to backend directory with active virtual environment
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend
.\.venv\Scripts\Activate.ps1

# Run Step 2B ORM Model Verification (User-Profile 1-to-1 relationship)
python verify_step_2b.py

# Run Step 2C Auth/Profile API & Token Verification
python verify_step_2c.py

# Run Step 2D Complete Backend & Live PostgreSQL Verification
python verify_step_2d.py
```

#### H. Port & Process Troubleshooting Commands
```powershell
# Check which process ID (PID) is listening on Port 8000
netstat -ano | findstr :8000

# Check which process ID (PID) is listening on Port 3000
netstat -ano | findstr :3000

# Inspect a running process by PID in PowerShell
Get-Process -Id <PID>

# Terminate all running Python/Uvicorn processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Terminate all running Node.js processes
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

# Terminate a specific stuck process by PID
Stop-Process -Id <PID> -Force
```

---

## 20. Beginner Troubleshooting Guide

| Issue | Likely Cause | Exact Solution |
| :--- | :--- | :--- |
| **Backend fails to start: `DATABASE_URL not found`** | `.env` file is missing in `backend/` or malformed. | Ensure `backend/.env` exists and contains a valid `DATABASE_URL=postgresql://postgres:pass@localhost:5432/ai_gym`. |
| **Backend fails to start: `port 8000 is already in use`** | A previously running Uvicorn process is still alive. | In PowerShell: `Get-Process python \| Stop-Process` (or kill the specific PID listening on port 8000). |
| **Frontend shows: `Failed to fetch` on Login** | Backend server is offline or CORS is blocking the request. | Verify Terminal 1 is running `uvicorn main:app --reload` and listening on port 8000. |
| **Next.js shows: `401 Unauthorized` repeatedly** | The stored JWT token has expired or is invalid. | Open browser Developer Tools (`F12`), go to **Application $\rightarrow$ Local Storage**, clear `access_token`, and log in again. |
| **`psql` command not recognized in PowerShell** | PostgreSQL binary folder is not on your Windows `PATH`. | Use Python scripts or run directly with: `& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres`. |
| **TypeScript throws errors on `@/api/config`** | Path alias configuration missing in `tsconfig.json`. | Verify `frontend/tsconfig.json` contains `"paths": { "@/*": ["./src/*"] }`. |
| **Environment changes not showing in frontend** | `.env.local` was modified while Next.js was running. | Stop the frontend server in Terminal 2 (`Ctrl+C`) and restart it with `npm run dev`. |
| **Database error: `relation "profiles" does not exist`** | Step 2A migration was not run on a fresh database. | Run `python step_2a_migration.py` or `python create_tables.py` in `backend/`. |

---

## 21. Developer 4 Onboarding Checklist

Welcome to the team, Developer 4! Follow this checklist to get your local environment running smoothly:

1. [ ] **Read this entire guide** (`docs/PHASE_1_FOUNDATION_GUIDE.md`) to understand the architecture and directory layout.
2. [ ] **Clone the repository** and check out branch `main`.
3. [ ] **Verify local toolchain**: Ensure Python 3.14+, Node.js 22+, and PostgreSQL 18 are installed.
4. [ ] **Configure Backend**:
   - Create `backend/.env` using `backend/.env.example` as a template.
   - Create virtual environment: `python -m venv backend/.venv`.
   - Activate environment and run: `pip install -r backend/requirements.txt`.
5. [ ] **Initialize PostgreSQL**:
   - Create local database `ai_gym`.
   - Run `python backend/create_tables.py` and verify tables `users` and `profiles`.
6. [ ] **Configure Frontend**:
   - Run `npm install` inside `frontend/`.
   - Ensure `frontend/.env.local` exists with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.
7. [ ] **Start Services & Smoke Test**:
   - Start backend (`uvicorn main:app --reload`) and frontend (`npm run dev`).
   - Register a new account, test login, view dashboard, and update your profile.

> [!CAUTION]
> **Developer 4 Golden Rule:** Do NOT redesign, refactor, or modify existing Phase 1 architecture (authentication, database models, or API endpoints) without prior discussion and architectural review with Developer 1 (ChatGPT) and Developer 3 (Anand).

---

## 22. What We Learned (Knowledge Glossary)

* **Client / Server Architecture:** A model where the client (browser / Next.js) requests data and the server (FastAPI) processes business logic and serves the data.
* **REST API:** A standardized way for applications to communicate over the web using HTTP verbs (`GET` to fetch data, `POST` to create data, `PUT` to update data, and `DELETE` to remove data).
* **JSON (JavaScript Object Notation):** The lightweight data interchange format used in API communication.
* **Relational Database (SQL):** A database where data is organized into tables with formal relationships enforced by Primary and Foreign keys.
* **ORM (Object Relational Mapping):** A programming technique (via SQLAlchemy) that lets you interact with database tables as if they were ordinary Python classes and objects.
* **CORS (Cross-Origin Resource Sharing):** A browser security feature that restricts cross-origin HTTP requests unless the server explicitly grants permission via HTTP headers.
* **Stateless Authentication (JWT):** A security pattern where the server issues a signed digital token to the client. The client presents this token with every request, allowing the server to verify identity without storing session state in memory.
* **Cryptographic Password Hashing:** A one-way mathematical function that transforms a plaintext password into an irreversible hash. Plaintext passwords must never be stored.
* **Environment Variables:** Configuration values injected into software from the operating system or `.env` files to keep sensitive credentials out of version control.

---

## 23. Phase 1 Verification Checklist

- [x] Project workspace initialized with Git repository
- [x] Python virtual environment configured with pinned dependencies
- [x] PostgreSQL 18 database `ai_gym` created and connected
- [x] Relational schema designed with `users` and `profiles` tables (1-to-1 relationship with `ON DELETE CASCADE`)
- [x] Password hashing implemented using modern Argon2/bcrypt
- [x] Stateless JWT bearer token authentication implemented
- [x] FastAPI backend operational with `/health`, `/auth/*`, and `/users/*` routers
- [x] CORS middleware configured for `http://localhost:3000`
- [x] Next.js frontend initialized with App Router, TypeScript, and Tailwind CSS
- [x] Centralized frontend API configuration layer (`API_BASE_URL`) established
- [x] Working Login interface (`/login`)
- [x] Working Dashboard interface (`/dashboard`)
- [x] Working Profile Onboarding interface (`/profile`)
- [x] End-to-end profile persistence verified across browser refreshes
- [x] Folder structure reconciled: `ai/` $\rightarrow$ `ml/` matching the master plan
- [x] Zero TypeScript errors (`npx tsc --noEmit`)
- [x] Comprehensive technical documentation completed

**PHASE 1 STATUS: COMPLETE & FULLY VERIFIED ✅**

---

## 24. Next Step: Phase 2 Kickoff

With Phase 1 complete and verified, the project is ready to begin **Phase 2 — Computer Vision & AI Gym Trainer**.

The upcoming Phase 2 implementation sequence will be:
1. **Exercise Catalogue & Workout Data Models:** Create database tables for `exercises`, `workout_sessions`, and `pose_metrics`.
2. **OpenCV & MediaPipe Pose Pipeline:** Capture live camera frames and detect body landmarks (shoulders, elbows, wrists, hips, knees, ankles) inside `ml/pose/`.
3. **Joint Angle Trigonometry:** Build pure mathematical functions to compute 2D/3D angles between joint triplets.
4. **Exercise State Machine:** Implement rep-counting logic for our first exercise (e.g. Squats or Bicep Curls) using state transitions (UP $\rightarrow$ DOWN $\rightarrow$ UP).
5. **Real-Time Visual & Audio Feedback:** Overlay joint angles, repetition counters, and posture warnings onto the live video feed.

*(Developer 2 has stopped here. Phase 2 implementation will begin upon explicit instruction from Developer 3.)*
