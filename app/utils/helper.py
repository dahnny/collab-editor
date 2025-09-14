from app.db.schemas.operation import OperationIn


def apply_operation(content: str, operation: OperationIn):
    new_content = content
    position = max(0, min(operation.position, len(content)))
    if operation.insert_text is not None:
        new_content = content[:position] + operation.insert_text + content[position:]
        
    if operation.delete_len or 0 and operation.delete_len > 0:
        delete_end = min(position + operation.delete_len, len(content))
        new_content = content[:position] + content[delete_end:]
        
    return new_content





