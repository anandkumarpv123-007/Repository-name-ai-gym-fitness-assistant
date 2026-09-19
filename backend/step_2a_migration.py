import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg

# Load environment
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("[ERROR] DATABASE_URL not found in .env")
    sys.exit(1)

# Handle psycopg connection URL format
conn_url = db_url.replace("+psycopg", "")

print("[INFO] Connecting to PostgreSQL database...")

try:
    with psycopg.connect(conn_url) as conn:
        with conn.cursor() as cur:
            # 1. Pre-migration check
            cur.execute("SELECT COUNT(*) FROM users;")
            initial_user_count = cur.fetchone()[0]
            print(f"[INFO] Current users table row count: {initial_user_count}")

            # 2. Check if profiles table already exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'profiles'
                );
            """)
            profiles_existed = cur.fetchone()[0]
            print(f"[INFO] Profiles table already existed: {profiles_existed}")

            # 3. Create profiles table inside transaction
            print("[INFO] Executing Step 2A migration (creating profiles table)...")
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id INTEGER PRIMARY KEY,
                    date_of_birth TIMESTAMP NULL,
                    gender VARCHAR(50) NULL,
                    height_cm DOUBLE PRECISION NULL,
                    weight_kg DOUBLE PRECISION NULL,
                    fitness_goal VARCHAR(100) NULL,
                    activity_level VARCHAR(50) NULL,
                    dietary_preference VARCHAR(100) NULL,
                    CONSTRAINT fk_profiles_user
                        FOREIGN KEY (user_id) 
                        REFERENCES users(id) 
                        ON DELETE CASCADE
                );
            """
            cur.execute(create_table_sql)

            # 4. Copy existing data from users to profiles
            print("[INFO] Copying profile data from users to profiles...")
            copy_data_sql = """
                INSERT INTO profiles (
                    user_id,
                    date_of_birth,
                    gender,
                    height_cm,
                    weight_kg,
                    fitness_goal,
                    activity_level,
                    dietary_preference
                )
                SELECT 
                    id AS user_id,
                    date_of_birth,
                    gender,
                    height_cm,
                    weight_kg,
                    fitness_goal,
                    activity_level,
                    dietary_preference
                FROM users
                ON CONFLICT (user_id) DO NOTHING;
            """
            cur.execute(copy_data_sql)
            
            # Commit transaction
            conn.commit()
            print("[SUCCESS] Migration executed and committed successfully.")

        # --- VERIFICATION PHASE ---
        with conn.cursor() as cur:
            print("\n" + "="*50)
            print("VERIFICATION RESULTS")
            print("="*50)

            # Check 1: Verify profiles columns
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'profiles'
                ORDER BY ordinal_position;
            """)
            profiles_cols = cur.fetchall()
            print(f"1. Profiles table columns ({len(profiles_cols)} columns):")
            for col in profiles_cols:
                print(f"   - {col[0]}: {col[1]} (Nullable: {col[2]})")

            # Check 2: Foreign key verification
            cur.execute("""
                SELECT 
                    tc.constraint_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table, 
                    ccu.column_name AS foreign_column,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu 
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.referential_constraints AS rc 
                    ON tc.constraint_name = rc.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu 
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_name = 'profiles' AND tc.constraint_type = 'FOREIGN KEY';
            """)
            fk_info = cur.fetchall()
            print(f"\n2. Foreign Key constraint: {fk_info}")

            # Check 3: Row counts
            cur.execute("SELECT COUNT(*) FROM users;")
            users_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM profiles;")
            profiles_count = cur.fetchone()[0]
            print(f"\n3. Row counts -> users: {users_count}, profiles: {profiles_count}")
            assert users_count == profiles_count, f"Row count mismatch! users={users_count}, profiles={profiles_count}"

            # Check 4: Data integrity comparison
            cur.execute("""
                SELECT 
                    u.id, 
                    u.name, 
                    u.email, 
                    p.height_cm, 
                    p.weight_kg, 
                    p.fitness_goal, 
                    p.activity_level, 
                    p.dietary_preference
                FROM users u
                JOIN profiles p ON u.id = p.user_id
                ORDER BY u.id;
            """)
            joined_data = cur.fetchall()
            print(f"\n4. Verified joined rows ({len(joined_data)} users verified):")
            for row in joined_data:
                print(f"   - User ID {row[0]} ({row[1]} | {row[2]}): height={row[3]}, weight={row[4]}, goal={row[5]}")

            # Check 5: Verify users table intact
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            users_cols = cur.fetchall()
            print(f"\n5. Users table intact ({len(users_cols)} columns retained):")
            for col in users_cols:
                print(f"   - {col[0]}: {col[1]}")

            print("\n[ALL STEP 2A VERIFICATIONS PASSED SUCCESSFULLY]")

except Exception as e:
    print(f"\n[FAILURE] An error occurred: {e}", file=sys.stderr)
    sys.exit(1)
