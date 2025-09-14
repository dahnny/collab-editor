from typing import List
from app.db.schemas.operation import OperationIn, OperationOut
from app.utils.simpleop import SimpleOp


def transform_insert_against_insert(in_op: SimpleOp, applied_op: SimpleOp) -> SimpleOp:
    """
    Transform `in_op` (an insert) so it can be applied after `applied_op` (also an insert).
    """
    # If our insert is strictly before the applied insert, it's unaffected.
    if in_op.pos < applied_op.pos:
        return in_op

    # If our insert is strictly after, shift it right by the length of the applied insertion.
    if in_op.pos > applied_op.pos:
        in_op.pos += len(applied_op.text or "")
        return in_op

    # If positions are equal -> tie-breaker
    # Deterministic rule: smaller user_id (lexicographically) wins and stays before.
    if (in_op.user_id or "") < (applied_op.user_id or ""):
        return in_op
    else:
        # applied op wins -> our insertion should come after it
        in_op.pos += len(applied_op.text or "")
        return in_op


def transform_insert_against_delete(in_op: SimpleOp, applied_op: SimpleOp) -> SimpleOp:
    """
    Transform `in_op` (an insert) so it can be applied after `applied_op` (a delete).
    """
    # If our insert is before the delete, it's unaffected.
    if in_op.pos <= applied_op.pos:
        return in_op

    # If our insert is after the deleted region, shift it left by the length of the deletion.
    if in_op.pos >= applied_op.pos + (applied_op.length or 0):
        in_op.pos -= applied_op.length or 0
        return in_op

    # If our insert is inside the deleted region, move it to the start of the deleted region.
    in_op.pos = applied_op.pos
    return in_op


def transform_delete_against_insert(del_op: SimpleOp, applied_op: SimpleOp) -> SimpleOp:

    ins_pos = applied_op.pos
    ins_len = len(applied_op.text or "")

    if del_op.pos >= ins_pos:
        del_op.pos += ins_len
        return del_op
    # If our delete is before the inserted text, it's unaffected.
    if del_op.pos + (del_op.length or 0) <= ins_pos:
        return del_op

    # If our delete is inside the inserted text, move it to the start of the inserted text.
    del_op.length = (del_op.length or 0) + ins_len
    return del_op


def transform_delete_against_delete(in_op: SimpleOp, applied_op: SimpleOp) -> SimpleOp:
    """
    Transform `in_op` (a delete) so it can be applied after `applied_op` (also a delete).
    """
    # If our delete is strictly before the applied delete, it's unaffected.
    if in_op.pos + (in_op.length or 0) <= applied_op.pos:
        return in_op

    # If our delete is strictly after, shift it left by the length of the applied deletion.
    if in_op.pos >= applied_op.pos + (applied_op.length or 0):
        in_op.pos -= applied_op.length or 0
        return in_op

    # If our delete overlaps with the applied delete, we need to adjust its position and length.
    overlap_start = max(in_op.pos, applied_op.pos)
    overlap_end = min(
        in_op.pos + (in_op.length or 0), applied_op.pos + (applied_op.length or 0)
    )
    overlap_length = overlap_end - overlap_start

    # Reduce the length of our delete by the length of the overlap.
    in_op.length = (in_op.length or 0) - overlap_length
    if in_op.length < 0:
        in_op.length = 0

    # If our delete starts after the applied delete, shift its position left by the length of the applied deletion.
    if in_op.pos >= applied_op.pos:
        in_op.pos -= min(in_op.pos - applied_op.pos, applied_op.length or 0)

    return in_op


def transform_incoming_operation(
    incoming: OperationIn, concurrent_ops: List[OperationOut]
) -> OperationIn:
    pos = incoming.position
    insert_text = incoming.insert_text
    delete_len = incoming.delete_len

    incoming_uid = getattr(incoming, "user_id", None)

    for op in concurrent_ops:
        applied = SimpleOp(
            type="delete" if op.delete_len else "insert",
            pos=op.position,
            length=op.delete_len or len(op.insert_text or ""),
            text=op.insert_text,
            user_id=str(op.user_id),
        )

        if delete_len > 0:
            del_so = SimpleOp(
                type="delete", pos=pos, length=delete_len, user_id=incoming_uid
            )
            transformed_del = None
            if applied.type == "insert":
                transformed_del = transform_delete_against_insert(del_so, applied)
            else:
                transformed_del = transform_delete_against_delete(del_so, applied)
            if transformed_del is None:
                # Update the position based on the transformed delete operation.
                pos = (
                    transformed_del.pos
                    if transformed_del and hasattr(transformed_del, "pos")
                    else pos
                )
                delete_len = 0
            else:
                pos = transformed_del.pos
                delete_len = transformed_del.length or 0

        if insert_text:
            ins_so = SimpleOp(
                type="insert", pos=pos, text=insert_text, user_id=incoming_uid
            )
            if applied.type == "insert":
                ins_so = transform_insert_against_insert(ins_so, applied)
            else:
                ins_so = transform_insert_against_delete(ins_so, applied)

            pos = ins_so.pos
            insert_text = ins_so.text

    return OperationIn(
        position=pos,
        insert_text=insert_text,
        delete_len=delete_len or 0,
        base_version=incoming.base_version,
    )
