from pydantic import BaseModel

class OperationIn(BaseModel):
    """Operation payload sent from client over WebSocket or REST.


    - position: index in text where op applies
    - insert_text: optional text to insert
    - delete_len: optional delete length
    - base_version: client's known document version
    """
    position: int
    insert_text: str | None = None
    delete_len: int = 0
    base_version: int
    
class OperationOut(BaseModel):
    """Operation data sent back to clients after being saved to DB.
    
    - id: operation ID
    - document_id: ID of the document
    - user_id: ID of the user who made the operation
    - position: index in text where op applies
    - insert_text: text to insert
    - delete_len: length of text to delete
    - base_version: document version before this operation
    - created_at: timestamp when operation was created
    """
    id: int
    document_id: str
    user_id: int
    position: int
    insert_text: str | None = None
    delete_len: int | None = None
    base_version: int
    created_at: str  # ISO formatted datetime string
    

    class Config:
        orm_mode = True