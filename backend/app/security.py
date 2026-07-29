from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import crud
from . import models
from .config import get_settings
from .database import SessionLocal
from .permissions import Permission, canonical_role, has_permissions
from .schemas import TokenData

settings = get_settings()

pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/token')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(db: Session, email: str, password: str):
    user = crud.get_user_by_email(db, email=email)
    if not user:
        return None
    now = datetime.now(timezone.utc)
    locked_until = user.locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if locked_until and locked_until > now:
        return None
    company = db.query(models.Organisation).filter(models.Organisation.id == user.organisation_id).first()
    if (
        not user.is_active
        or user.is_deleted
        or company is None
        or not company.is_active
        or company.status != 'active'
    ):
        return None
    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.ACCOUNT_LOCK_MAX_FAILURES:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)
            user.failed_login_attempts = 0
        db.commit()
        return None
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    db.refresh(user)
    return user


def _user_claims(user: models.User, company: models.Organisation) -> dict:
    return {
        'sub': str(user.id),
        'uid': user.id,
        'company_id': company.id,
        'role': canonical_role(user.role),
        'permission_version': max(user.permission_version, company.permission_version),
        'session_version': user.session_version,
    }


def create_access_token(user: models.User, company: models.Organisation, expires_delta: timedelta | None = None) -> str:
    to_encode = _user_claims(user, company)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire, 'type': 'access'})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user: models.User, company: models.Organisation) -> str:
    to_encode = _user_claims(user, company)
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({'exp': expire, 'type': 'refresh'})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type: str | None = payload.get('type')
        if token_type != 'access':
            raise credentials_exception
        user_id: int | None = payload.get('uid')
        company_id: int | None = payload.get('company_id')
        role_value: str | None = payload.get('role')
        permission_version: int | None = payload.get('permission_version')
        session_version: int | None = payload.get('session_version')
        if None in {user_id, company_id, permission_version, session_version}:
            raise credentials_exception
        token_data = TokenData(
            role=role_value,
            user_id=user_id,
            company_id=company_id,
            permission_version=permission_version,
            session_version=session_version,
        )
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(
        models.User.id == token_data.user_id,
        models.User.organisation_id == token_data.company_id,
        models.User.is_deleted.is_(False),
        models.User.is_active.is_(True),
    ).first()
    company = db.query(models.Organisation).filter(
        models.Organisation.id == token_data.company_id,
        models.Organisation.is_active.is_(True),
        models.Organisation.status == 'active',
    ).first()
    if (
        user is None
        or company is None
        or user.session_version != token_data.session_version
        or max(user.permission_version, company.permission_version) != token_data.permission_version
        or token_data.role is None
        or canonical_role(user.role) != canonical_role(token_data.role.value)
    ):
        raise credentials_exception
    return user


def decode_refresh_token(refresh_token: str) -> TokenData:
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type: str | None = payload.get('type')
        user_id: int | None = payload.get('uid')
        company_id: int | None = payload.get('company_id')
        role_value: str | None = payload.get('role')
        permission_version: int | None = payload.get('permission_version')
        session_version: int | None = payload.get('session_version')
        if token_type != 'refresh' or None in {
            user_id,
            company_id,
            permission_version,
            session_version,
        }:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
        return TokenData(
            role=role_value,
            user_id=user_id,
            company_id=company_id,
            permission_version=permission_version,
            session_version=session_version,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token') from exc


def require_permissions(*permissions: Permission) -> Callable:
    def dependency(current_user=Depends(get_current_user)):
        if not has_permissions(current_user.role, permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')
        return current_user

    return dependency
