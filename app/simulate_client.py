import asyncio
import json
import websockets
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from app.db.models.document import Document
from app.db.session import DATABASE_URL

# Setup DB session
engine = sa.create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

DOC_ID = "bfea7b38-d10f-4344-8d3c-1a810daf62a5"  # replace with your doc_id
TOKEN_A = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZWZkOGMwZTYtZThjNS00MGIzLTk0YTMtYzFlY2NhNTQ5ZWI4IiwiZXhwIjoxNzU3ODgxMzM5fQ.0N7THZcb1gl8Fu5ER6gv_nybEGFBxCDJ5bwggystmsU"  # JWT for user A
TOKEN_B = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiOGYwZGU1NWMtODU2My00ODg5LTg4NDEtN2Q2M2YzYmQyZTIyIiwiZXhwIjoxNzU3ODgxMzgzfQ.oaGThoaBwxLBaWIJEzJbJjnj_0PLkKjOCQJiZjukmWI"  # JWT for user B

WS_URL_A = f"ws://localhost:8000/ws/{DOC_ID}?token={TOKEN_A}"
WS_URL_B = f"ws://localhost:8000/ws/{DOC_ID}?token={TOKEN_B}"

async def client(name, url, ops):
    async with websockets.connect(url) as ws:
        print(f"{name} connected")

        init_msg = await ws.recv()
        print(f"{name} received init: {init_msg}")
        init_data = json.loads(init_msg)
        current_version = init_data.get("version", 0)

        # Send operations in order
        for op in ops:
            op["base_version"] = current_version  # align version
            await ws.send(json.dumps(op))
            print(f"{name} sent: {op}")

            # Listen for ack or op updates
            while True:
                response = await ws.recv()
                print(f"{name} received: {response}")
                resp = json.loads(response)
                if resp["type"] == "ack":
                    current_version = resp["updated_version"]
                    break
                elif resp["type"] == "op":
                    current_version = resp["updated_version"]
                    # break only if you want to continue to next op after receiving someone else's op

async def main():
    op_a = [{
        "id": 1,
        "doc_id": DOC_ID,
        "user_id": "userA",
        "base_version": 0,
        "position": 0,
        "insert_text": "Hello",
    }]
    op_b = [{
        "id": 2,
        "doc_id": DOC_ID,
        "user_id": "userB",
        "base_version": 0,
        "position": 0,
        "insert_text": "World",
    }]

    # Run both clients almost simultaneously
    await asyncio.gather(
        client("ClientA", WS_URL_A, op_a),
        client("ClientB", WS_URL_B, op_b)
    )

    # After operations, check DB state
    session = SessionLocal()
    doc = session.query(Document).filter_by(id=DOC_ID).first()
    print(f"Final content in DB: {doc.content}")

if __name__ == "__main__":
    asyncio.run(main())
