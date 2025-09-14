from app.db.session import SessionLocal
from app.core.token import verify_access_token
from app.db.models.user import User
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.crud.user import get_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = verify_access_token(token, credentials_exception)
    user = get_user(db, token.id)
    if not user:
        raise credentials_exception

    return user


def get_user_from_token(
    token: str , db: Session
) -> User | None:
    try:
        token_data = verify_access_token(token, None)
        user = get_user(db, token_data.id)
        return user
    except Exception:
        return None
