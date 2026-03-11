from typing import Optional
from sqlalchemy import select, func
from data_access.models import SessionLocal, UserModel
import datetime

class BaseRepository:
    def __init__(self, session):
        self.session = session

    def commit_changes(self):
        self.session.commit()

class UserRepository(BaseRepository):
    def authenticate(self, username: str, pin: str) -> Optional[UserModel]:
        if not username or not pin: return None
        return self.session.query(UserModel).filter(
            func.lower(UserModel.username) == username.lower(),
            UserModel.pin == int(pin)
        ).first(
        )
    
    def add_user(self, username: str, pin: int, level: int):
        self.session.add(UserModel(username=username, pin=pin, level=level, created_at=datetime.datetime.now()))
        self.commit_changes()

    def delete_user(self, user: UserModel):
        self.session.delete(user)
        self.commit_changes()

    def get_all_users(self):
        return self.session.query(UserModel).all()