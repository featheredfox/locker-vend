import time
import threading
from datetime import datetime
from typing import Optional, Tuple
from core.enums import UserLevel, Container, Transaction, Misc
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
        msg_code = Container.Status.Hardware.Message.OPENING
        return True, msg_code
    
    def close_container(self, container: ContainerModel) -> Tuple[bool, int]:
        # Logic for triggering GPIO pins would go here (e.g., solenoid LOW)
        self.monitor_container_close(container)
        return True, Container.Status.Hardware.Message.CLOSING
    
    def is_container_open(self, container: ContainerModel) -> bool:
        if container.sens_inp_pin is None:
            return False
        
        # [HARDWARE INTEGRATION] Read actual GPIO state here!
        # state = GPIO.input(container.sens_inp_pin)
        # return state == GPIO.LOW  # (Assuming LOW means door is open)
        
        # Simulating a closed door for testing:
        return False
    
    def monitor_container_open(self, container: ContainerModel, timeout: int = 2) -> Tuple[bool, int]:
        start_time = time.time()
            
        while not self.is_container_open(container):
            if time.time() - start_time > timeout:
                return False, Container.Status.Hardware.Error.NOT_OPENED
            time.sleep(0.1)
            
        return True, Container.Status.Hardware.Message.OPEN
    
    def monitor_container_close(self, container: ContainerModel, timeout: int = 2) -> Tuple[bool, int]:
        start_time = time.time()
            
        while self.is_container_open(container):
            if time.time() - start_time > timeout:
                return False, Container.Status.Hardware.Error.NOT_CLOSED
            time.sleep(0.1)
            
        return True, Container.Status.Hardware.Message.CLOSED        
    

# ========== TRANSACTIONS =====================================================================

class TransactionService:
    def __init__(self, container_repo: ContainerRepository, hardware_service: HardwareService):
        self.container_repo = container_repo
        self.hardware_service = hardware_service
        self.active_timed_action_event = None
        self._timeout_triggered = False # FIX: Flag to escape the while loop!
        
    def process_transaction(self, transaction_type: int, part_no: str = None) -> Tuple[bool, int, Optional[ContainerModel]]:
        match transaction_type:
            case Transaction.Type.TAKE: container = self.container_repo.get_container_to_take(part_no)
            case Transaction.Type.RESTOCK: container = self.container_repo.get_container_to_restock(part_no)
        
        if not container:
            return False, Transaction.Status.NONE, None

        self.hardware_service.open_container(container)
        success, hw_msg = self.hardware_service.monitor_container_open(container)
        
        if not success: 
            return False, Transaction.Status.FAILED, container
        
        self._timeout_triggered = False
        
        def handle_timeout():
            self._timeout_triggered = True
            self.hardware_service.close_container(container)

        self._start_timed_action(on_timeout_callback=handle_timeout, timeout_seconds=120)

        while self.hardware_service.is_container_open(container):
            # FIX: Escape Hatch! If the callback ran, get out of this loop!
            if self._timeout_triggered:
                break
            time.sleep(0.5)

        self._stop_timed_action()

        # FIX: Check WHY we left the loop!
        if self._timeout_triggered:
            # You can map this to a specific Timeout/Failed status in your Enums
            return False, Transaction.Status.FAILED, container

        return True, Transaction.Status.AWAIT_CONFIRMATION, container

    def finalize_transaction(self, transaction_type: int, part_no: str, container: ContainerModel):
        match transaction_type:
            case Transaction.Type.TAKE:
                container.status = Container.Status.Content.NONE
                container.retrieved_at = datetime.now()
                container.part_no = None
            case Transaction.Type.RESTOCK:
                container.status = Container.Status.Content.PRESENT
                container.deposited_at = datetime.now()
                container.part_no = part_no
        
        self.container_repo.commit_changes()
        # Update LED here

        return True, Transaction.Status.COMPLETE

    def cancel_transaction(self, container: ContainerModel):
        return True, Transaction.Status.CANCELLED

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

    def sort_stock_counts(self, sort_order: int, only_available_stock: bool = False) -> list:
        items = self.dir_repo.get_all_items()
        item_stock_data = []
        
        for item in items:
            count = self.container_repo.get_stock_count(item.part_no)
            if only_available_stock and count <= 0:
                continue 
            item_stock_data.append((item, count))

        is_reverse = False if sort_order == Misc.SortOrder.ASC else True
        return sorted(item_stock_data, key=lambda x: x[1], reverse=is_reverse)

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
                ContainerModel(id=1,part_no='AXCELA G', status=Container.Status.Content.PRESENT),
                ContainerModel(id=2,part_no='AXCELA STRIKER G', status=Container.Status.Content.PRESENT),
                ContainerModel(id=3,part_no='AXCELA G', status=Container.Status.Content.NONE),
                ContainerModel(id=4,part_no='AXCELA STRIKER G', status=Container.Status.Content.NONE)
            ]
            self.session.add_all(containers)
            self.session.commit()