import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load env vars manually or rely on pydantic later
load_dotenv("backend/.env")

# Parse URL or use default just for raw connection test
# Assuming format postgresql+asyncpg://user:password@host:port/dbname
# asyncpg connect needs dsn without +asyncpg usually, or we parse it.
db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/logistics_db")
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

print(f"Testing connection to: {db_url}")

async def check_db():
    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Connection Successful!")
        await conn.close()
        exit(0)
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(check_db())
