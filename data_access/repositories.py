from typing import Optional
from sqlalchemy import select, func
from data_access.models import SessionLocal, UserModel, ItemDirectoryModel, ContainerModel
from core.enums import Container
from typing import List
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
    
class DirectoryRepository(BaseRepository):
    def get_all_items(self) -> List[ItemDirectoryModel]:
        return self.session.query(ItemDirectoryModel).all()

    def get_item(self, part_no: str) -> Optional[ItemDirectoryModel]:
        return self.session.query(ItemDirectoryModel).filter(ItemDirectoryModel.part_no == part_no).first()

    def add_item(self, item: ItemDirectoryModel):
        self.session.add(item)
        self.commit_changes()

    def delete_item(self, item: ItemDirectoryModel):
        self.session.delete(item)
        self.commit_changes()

class ContainerRepository(BaseRepository):
    def get_all_containers(self) -> List[ContainerModel]:
        return self.session.query(ContainerModel).order_by(ContainerModel.id).all()

    def get_stock_count(self, part_no: str) -> int:
        return self.session.query(ContainerModel).filter(ContainerModel.part_no == part_no, ContainerModel.status == Container.Status.Content.PRESENT).count()

    def get_container_to_take(self, part_no: str) -> Optional[ContainerModel]:
        stmt = select(ContainerModel).where(ContainerModel.part_no == part_no).where(ContainerModel.status == Container.Status.Content.PRESENT).order_by(ContainerModel.deposited_at.asc())
        return self.session.execute(stmt).scalars().first()

    def get_container_to_restock(self, part_no: str) -> Optional[ContainerModel]:
        stmt = select(ContainerModel).where(ContainerModel.part_no == part_no).where(ContainerModel.status == Container.Status.Content.NONE)
        return self.session.execute(stmt).scalars().first()

    def get_free_container(self) -> Optional[ContainerModel]:
        return self.session.query(ContainerModel).filter(ContainerModel.part_no == None).first()
    
    def get_container_status(self, container_id: int) -> int:
        stmt = select(ContainerModel.status).where(ContainerModel.id == container_id)
        return self.session.execute(stmt).scalar() or 0
        