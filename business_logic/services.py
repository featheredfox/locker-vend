import time
import threading
from datetime import datetime
from typing import Optional, Tuple
from core.enums import UserLevel, ContainerContent, HardwareMessage, HardwareError, TxType, TxError, TxStatus, DirMessage, SortOrder, CntMessage, CntError, CntAction, HrdwrePins, InvError, CntAssignStat
from data_access.models import UserModel, ItemDirectoryModel, ContainerModel
from data_access.repositories import UserRepository, DirectoryRepository, ContainerRepository

# ========== USER AUTHENTIFICATION ============================================================

class AuthService:
    def __init__(self , user_repo: UserRepository, transaction: Optional['TransactionService'] = None):
        self.user_repo = user_repo
        self.current_user: Optional[UserModel] = None
        self.transaction = transaction
        
    def login(self, username: str, pin: int) -> bool:
        user = self.user_repo.authenticate(username, pin)
        if user:
            self.current_user = user
            return True
        return False
    
    def logout(self, **kwargs):
        self.current_user = None

    def get_user_level(self) -> int:
        return self.current_user.level if self.current_user else UserLevel.OPERATOR
    
# ========== HARDWARE =========================================================================

class HardwareService:
    def __init__(self, container_repo: ContainerRepository):
        self.container_repo = container_repo

    def open_container(self, container: ContainerModel) -> Tuple[bool, int]:
        # Logic for triggering GPIO pins would go here (e.g., solenoid HIGH)
        msg_code = HardwareMessage.OPENING
        return True, msg_code
    
    def close_container(self, container: ContainerModel) -> Tuple[bool, int]:
        # Logic for triggering GPIO pins would go here (e.g., solenoid LOW)
        self.monitor_container_close(container)
        return True, HardwareMessage.CLOSING
    
    def is_container_open(self, container: ContainerModel) -> bool:
        if container.sens_inp_pin is None:
            return False
        
        # [HARDWARE INTEGRATION] Read actual GPIO state here!
        # Simulating a closed door for testing:
        return False
    
    def monitor_container_open(self, container: ContainerModel, timeout: int = 2) -> Tuple[bool, int]:
        start_time = time.time()
            
        while not self.is_container_open(container):
            if time.time() - start_time > timeout:
                return False, HardwareError.NOT_OPENED
            time.sleep(0.1)
            
        return True, HardwareMessage.OPEN
    
    def monitor_container_close(self, container: ContainerModel, timeout: int = 2) -> Tuple[bool, int]:
        start_time = time.time()
            
        while self.is_container_open(container):
            if time.time() - start_time > timeout:
                return False, HardwareError.NOT_CLOSED
            time.sleep(0.1)
            
        return True, HardwareMessage.CLOSED        
    
# ========== TRANSACTIONS =====================================================================

class TransactionService:
    def __init__(self, container_repo: ContainerRepository, hardware_service: HardwareService):
        self.container_repo = container_repo
        self.hardware_service = hardware_service
        self.active_timed_action_event = None
        self._timeout_triggered = False 
        self.assign_stat = CntAssignStat.ASSIGNED
        
    def process(self, tx_type: int, part_no: str = None) -> Tuple[int, Optional[int], Optional[ContainerModel], Optional[int]]:
        match tx_type:
            case TxType.TAKE: container = self.container_repo.get_container_to_take(part_no)
            case TxType.RESTOCK: 
                container = self.container_repo.get_assigned_container_to_restock(part_no); 
                if not container: container = self.container_repo.get_unassigned_container_to_restock(part_no); self.assign_stat = CntAssignStat.UNASSIGNED
        
        if not container:
            return TxStatus.NONE, None, container, self.assign_stat

        complete, msg_code = self.hardware_service.open_container(container)
        success, hw_msg = self.hardware_service.monitor_container_open(container)

        success = True # For testing
        
        if not success: 
            return TxStatus.FAILED, TxError.UNLOCK_FAILED, container, self.assign_stat
        
        self._timeout_triggered = False
        
        def handle_timeout():
            self._timeout_triggered = True
            self.hardware_service.close_container(container)

        self._start_timed_action(on_timeout_callback=handle_timeout, timeout_seconds=120)

        # Omitted for testing:
        # while self.hardware_service.is_container_open(container):
        #     if self._timeout_triggered:
        #         break
        #     time.sleep(0.5)

        self._stop_timed_action()

        if self._timeout_triggered:
            return TxStatus.FAILED, TxError.CONTAINER_NOT_CLOSED, container, self.assign_stat

        return TxStatus.AWAIT_CONFIRMATION, None, container, self.assign_stat

    def finalize(self, tx_type: int, part_no: str, container: ContainerModel) -> int:
        match tx_type:
            case TxType.TAKE:
                container.status = ContainerContent.EMPTY
                container.retrieved_at = datetime.now()
                container.part_no = None
            case TxType.RESTOCK:
                container.status = ContainerContent.PRESENT
                container.deposited_at = datetime.now()
                container.part_no = part_no
        
        self.container_repo.commit_changes()
        return TxStatus.COMPLETE

    def cancelled(self, container: ContainerModel, **kwargs) -> int:
        return TxStatus.CANCELLED
    
    def failed(self, container: ContainerModel, **kwargs) -> int:
        container.status = ContainerContent.UNKNOWN
        self.container_repo.commit_changes()
        return TxStatus.FAILED

    def _start_timed_action(self, on_timeout_callback: callable, timeout_seconds: int = 30):
        self.active_timed_action_event = threading.Event()
        def timed_task():
            if not self.active_timed_action_event.wait(timeout=timeout_seconds):
                on_timeout_callback()
        worker = threading.Thread(target=timed_task, daemon=True)
        worker.start()

    def _stop_timed_action(self):
        if self.active_timed_action_event:
            self.active_timed_action_event.set()

# ========== INVENTORY =====================================================================

class InventoryService:
    def __init__(self, container_repo: ContainerRepository, dir_repo: DirectoryRepository):
        self.container_repo = container_repo
        self.dir_repo = dir_repo

    def sort_stock_counts(self, sort_order: int, only_available_stock: bool = False) -> Tuple[list, int]:
        items = self.dir_repo.get_all_items()
        item_stock_data = []

        if not items: return [], InvError.NO_DIR_ITEMS
        
        for item in items:
            count = self.container_repo.get_stock_count(item.part_no)
            if only_available_stock and count <= 0:
                continue 
            item_stock_data.append((item, count))

        if not count and only_available_stock: return [], InvError.NO_STOCK

        is_reverse = False if sort_order is SortOrder.ASC else True
        return sorted(item_stock_data, key=lambda x: x[1], reverse=is_reverse), None

# ========== DIRECTORY ========================================================================

class DirectoryService:
    def __init__(self, dir_repo: DirectoryRepository, container_repo: ContainerRepository):
        self.dir_repo = dir_repo
        self.container_repo = container_repo

    def get_all_items(self) -> list:
        return sorted(self.dir_repo.get_all_items(), key=lambda x: x.description)

    def add_item(self, part_no: str, manufacturer: str, description: str) -> int:
        item = ItemDirectoryModel(part_no=part_no, manufacturer=manufacturer, description=description)
        self.dir_repo.add_item(item)
        return DirMessage.ADDED

    def delete_item(self, part_no: str) -> int:
        item = self.dir_repo.get_item(part_no)
        if item:
            self.dir_repo.delete_item(item)
        return DirMessage.DELETED

    def update_item(self, part_no: str, manufacturer: str, description: str) -> int:
        item = self.dir_repo.update_item(part_no, manufacturer, description)
        return DirMessage.UPDATED
    
    def check_inventory(self, part_no: str) -> bool:
        # FIX: Ensure true if stock > 0, false otherwise
        stock = self.container_repo.get_stock_count(part_no=part_no)
        return stock > 0
    
# ========== CONTAINERS =======================================================================

class ContainerService:
    def __init__(self, dir_repo: DirectoryRepository, container_repo: ContainerRepository):
        self.dir_repo = dir_repo
        self.container_repo = container_repo

    def add(self, pins: tuple[int, int, int, int]) -> Tuple[int, int]:
        new_id = self.container_repo.get_next_id()
        new_container = ContainerModel(
            id=new_id, 
            part_no=None, 
            item=None, 
            status=ContainerContent.EMPTY, 
            assigned_item=None, 
            deposited_at=None, 
            retrieved_at=None, 
            lock_outp_pin = pins[HrdwrePins.O_LOCK], 
            sens_inp_pin = pins[HrdwrePins.I_SENS], 
            g_led_outp_pin = pins[HrdwrePins.O_LED_G], 
            r_led_outp_pin = pins[HrdwrePins.O_LED_R]
            )
        self.container_repo.add_container(new_container)
        return new_container.id, CntMessage.ADDED
    
    def get_status(self, container_id: int) -> int:
        return self.container_repo.get_container_status(container_id)

    def delete(self, container_id: int) -> int:
        status = self.get_status(container_id)
        if status is not ContainerContent.EMPTY:
            return CntError.NOT_EMPTY if status is ContainerContent.PRESENT else CntError.CONTENT_UNKNOWN
        self.container_repo.delete_container(container_id)
        return CntMessage.DELETED
        
    def get_all(self) -> list:
        return sorted(self.container_repo.get_all_containers(), key=lambda x: x.id)
    
    def get_all_assigned(self) -> list:
        return sorted(self.container_repo.get_assigned_containers(), key=lambda x: x.id)
    
    def get_all_unassigned(self) -> list:
        return sorted(self.container_repo.get_unassigned_containers(), key=lambda x: x.id)
    
    def assign(self, container_id: int, part_no: str) -> list:
        container = self.container_repo.get_container_by_id(container_id)
        return self.container_repo.assign_container(container, part_no)

    def unassign(self, container_id: int) -> list:
        container = self.container_repo.get_container_by_id(container_id)
        return self.container_repo.unassign_container(container)

# ========== DATABASE SEEDER ==================================================================

class DatabaseSeeder:
    def __init__(self, session):
        self.session = session

    def seed(self):
        if self.session.query(UserModel).count() == 0:
            users = [
                UserModel(username="Operator", pin="1111", level=UserLevel.OPERATOR),
                UserModel(username="Admin", pin="2222", level=UserLevel.ADMIN),
                UserModel(username="Super", pin="9999", level=UserLevel.SUPER)
            ]
            self.session.add_all(users)
            self.session.commit()

        if self.session.query(ItemDirectoryModel).count() == 0:
            directory = [
                ItemDirectoryModel(part_no='AXCELA G', manufacturer='AMADA', description='80x1.6MM BANDSAW BLADE'),
                ItemDirectoryModel(part_no='AXCELA STRIKER G', manufacturer='AMADA', description='80x1.6MM BANDSAW BLADE')
            ]
            self.session.add_all(directory)
            self.session.commit()

        if self.session.query(ContainerModel).count() == 0:
            containers = [
                ContainerModel(id=1,part_no='AXCELA G', status=ContainerContent.PRESENT),
                ContainerModel(id=2,part_no='AXCELA STRIKER G', status=ContainerContent.PRESENT),
                ContainerModel(id=3,part_no='AXCELA G', status=ContainerContent.EMPTY),
                ContainerModel(id=4,part_no='AXCELA STRIKER G', status=ContainerContent.EMPTY)
            ]
            self.session.add_all(containers)
            self.session.commit()