import json
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.db.crud.document import get_document
from app.db.models.document import Document
from app.db.models.operation import Operation
from app.db.schemas.operation import OperationIn
from app.db.session import SessionLocal
from app.utils.helper import apply_operation
from app.utils.transformation import transform_incoming_operation
from app.utils.websocket import manager

from app.api.deps import get_user_from_token

router = APIRouter()


@router.websocket("/ws/{doc_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    doc_id: str,
):
    # get token from query parameters
    token = websocket.query_params.get("token")
    print(token)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)  # Policy Violation
        return

    # Get the database session
    db = SessionLocal()
    try:
        user = await run_in_threadpool(get_user_from_token, token, db)
        print(user)
        if not user:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION
            )  # Policy Violation
            return
        # User is authenticated, proceed with the connection
        print(f"User {user.id} connected to document {doc_id}")
        await manager.connect(websocket, doc_id)
        # Fetch the document from the database
        doc = await run_in_threadpool(get_document, db, doc_id)
        # Check if document exists
        if not doc:
            # If document does not exist, send an error message and close the connection
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Document not found"})
            )
            await websocket.close()
            manager.disconnect(websocket, doc_id)
            return

        # Send the initial document content and version to the client
        await websocket.send_text(
            json.dumps({"type": "init", "content": doc.content, "version": doc.version})
        )

        while True:
            try:
                # Receive the raw message from the WebSocket
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                # Handle disconnection
                manager.disconnect(websocket, doc_id)
                break

            try:
                data = json.loads(raw)
                json.dumps({"type": "data", "message": data})  # Validate JSON format
                # parse and validate the incoming message using OperationIn schema
                op_in = OperationIn(**data)
            except Exception as e:
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": f"Invalid message format: {e}"}
                    )
                )
                continue
            # Simple server-authoritative check: client's base_version must match server's current version
            if op_in.base_version != doc.version:
                # Ask client to sync (client should request latest ops or snapshot)
                await websocket.send_text(json.dumps({
                "type": "sync_needed",
                "content": doc.content,
                "version": doc.version,
                }))
                continue

            def persist_and_update():
                session = SessionLocal()
                try:
                    doc = (
                        session.query(Document)
                        .filter(Document.id == doc_id)
                        .with_for_update()
                        .first()
                    )
                    if not doc:
                        session.rollback()
                        return None, "Document not found"

                    concurrent_ops = (
                        session.query(Operation)
                        .filter(
                            Operation.document_id == doc_id,
                            Operation.applied_version > op_in.base_version,
                        )
                        .order_by(Operation.applied_version.asc())
                        .all()
                    )

                    # Transform incoming op against that history
                    transformed = transform_incoming_operation(op_in, concurrent_ops)
                    # transformed: position, delete_len, insert_text

                    # 4. Apply the transformed op to d.content
                    if transformed.delete_len or transformed.insert_text:
                        doc.content = apply_operation(doc.content, transformed)

                    doc.version += 1  # Increment document version
                    # Create and add the operation record
                    session.add(doc)
                    session.flush()

                    op_record = Operation(
                        document_id=doc.id,
                        user_id=user.id,
                        base_version=op_in.base_version,
                        position=transformed.position,
                        insert_text=transformed.insert_text,
                        delete_len=transformed.delete_len or 0,
                        applied_version=doc.version,
                    )
                    session.add(op_record)
                    session.commit()
                    session.refresh(op_record)
                    return op_record, doc.version
                except Exception as e:
                    session.rollback()
                    raise
                finally:
                    session.close()

            # Run the database operation in a thread pool
            try:
                op_record, updated_version = await run_in_threadpool(persist_and_update)
            except Exception as e:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Database error: {e}",
                        }
                    )
                )
                continue
            if not op_record:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "sync_needed",
                            "content": doc.content,
                            "version": updated_version,
                        }
                    )
                )
                continue
            message = {
                "type": "op",
                "op": {
                    "id": op_record.id,
                    "doc_id": op_record.document_id,
                    "user_id": op_record.user_id,
                    "base_version": op_record.base_version,
                    "position": op_record.position,
                    "insert_text": op_record.insert_text,
                    "delete_len": op_record.delete_len,
                    "created_at": op_record.created_at.isoformat(),
                },
                "updated_version": updated_version,
            }

            try:
                # Send ack to the sender with updated version
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "ack",
                            "op": message["op"],
                            "updated_version": updated_version,
                        }
                    )
                )
                await manager.broadcast(doc_id, message, exclude=websocket)
            except Exception as e:
                print(f"Broadcast error: {e}")
                pass
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)  # Policy Violation
        return
