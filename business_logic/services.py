from typing import Optional
from core.enums import UserLevel
from data_access.models import UserModel
from data_access.repositories import UserRepository


# ========== USER AUTHENTIFICATION ============================================================

class AuthService:
    def __init__(self , user_repo: UserRepository):
        self.user_repo = user_repo
        self.current_user: Optional[UserModel] = None
        
    def login(self, username: str, pin: int) -> bool:
        user = self.user_repo.authenticate(username, pin)
        if user:
            self.current_user = user
            return True
        return False
    
    def logout(self):
        self.current_user = None

    def get_user_level(self) -> int:
        return self.current_user.level if self.current_user else UserLevel.OPERATOR

# ========== USER AUTHENTIFICATION ============================================================

class DatabaseSeeder:
    def __init__(self, session):
        self.session = session

    def seed(self):
        if self.session.query(UserModel).count() == 0:
            self.session.add_all([
                UserModel(username="Operator", pin="1111", level=UserLevel.OPERATOR),
                UserModel(username="Admin", pin="2222", level=UserLevel.ADMIN),
                UserModel(username="Super", pin="9999", level=UserLevel.SUPER)
            ])