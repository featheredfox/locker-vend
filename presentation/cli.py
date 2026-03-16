import sys
import time
import msvcrt
from typing import TypeVar, Type, Optional, List, Tuple
from inputimeout import inputimeout, TimeoutOccurred
from business_logic.services import AuthService
from core.enums import UI, Transaction, SystemMessage, Misc, DirectoryOp
from presentation.views import UIFormatter, AuthPrompt, MenuPrompt, InputPrompt, ServiceMessage, SystemMessage as SysMsgView
from data_access.models import SessionLocal
from data_access.repositories import UserRepository, ContainerRepository, DirectoryRepository
from business_logic.services import TransactionService, InventoryService, DatabaseSeeder, HardwareService, DirectoryService
import business_logic.rules as rules
from business_logic.rules import ActionDispatcher

T = TypeVar('T')

class VendingMachineCLI:
    def __init__(self):
        self.session = SessionLocal()
        
        self.page = 0
        self.transaction_type = 0
        self.dir_op_type = 0
        
        # Repositories
        self.user_repo = UserRepository(self.session)
        self.container_repo = ContainerRepository(self.session)
        self.dir_repo = DirectoryRepository(self.session)

        # Services
        self.auth = AuthService(self.user_repo)
        self.hardware = HardwareService(self.container_repo)
        self.inventory = InventoryService(self.container_repo, self.dir_repo)
        self.transaction = TransactionService(self.container_repo, self.hardware)
        self.directory = DirectoryService(self.dir_repo, self.container_repo)
        
        DatabaseSeeder(self.session).seed()

    def start(self):
        while True:
            if not self.auth.current_user:
                self.login_screen()
            else:
                self.dashboard_screen()

    def login_screen(self):
        """Handles user credential input"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.LOGIN
        print(UIFormatter.page_header(page=self.page))
        
        username, msg_code = self._get_user_input(prompt=AuthPrompt.enter_username(), input_type=str, max_len=15, force_upper=True)
        pin, msg_code = self._get_user_input(prompt=AuthPrompt.enter_pin(), input_type=int, max_len=4)
        
        if not self.auth.login(username=username, pin=pin):
            complete, msg_code = self._get_user_input(prompt=AuthPrompt.invalid_credentials(), input_type=str)
            return # Returns to the while True loop instead of recursing

    def dashboard_screen(self):
        """Handles user selection of actions"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.DASHBOARD
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))
        
        allowed_actions = rules.get_allowed_dashboard_actions(user_level=self.auth.get_user_level())
        
        prompt_str = MenuPrompt.dashboard_options(allowed_actions=allowed_actions)
        selection, err_code = self._get_user_input(prompt=prompt_str, input_type=int, allowed_val=allowed_actions, timeout=60)
        
        if selection is None: 
            print(SysMsgView.get_input_error_message(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT))
            action = rules.get_input_error_action(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
            ActionDispatcher.execute(app_context=self, action=action, timeout=5)
            return
        
        action = rules.get_dashboard_action(selection=selection)
        ActionDispatcher.execute(app_context=self, action=action)

    def take_screen(self):
        """Handles user selection of item to TAKE"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.TAKE
        self.transaction_type = Transaction.Type.TAKE
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        stock = self.inventory.sort_stock_counts(sort_order=Misc.SortOrder.DESC, only_available_stock=True)

        for i, (item, count) in enumerate(stock): print(f"{MenuPrompt.stock_list_options(i=i, part_no=item.part_no, count=count)}")
        
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=self.page, transaction_type=self.transaction_type), input_type=int, allowed_val=[i+1 for i in range(len(stock))], timeout=60)
        if selection is None: 
            print(SysMsgView.get_input_error_message(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT))
            action = rules.get_input_error_action(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
            ActionDispatcher.execute(app_context=self, action=action, timeout=5)
            return
        
        selected_part_no = stock[selection - 1][0].part_no
        self.transaction_screen(transaction_type=self.transaction_type, part_no=selected_part_no)

    def restock_screen(self):
        """Handles user selection of item to RESTOCK"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.RESTOCK
        self.transaction_type = Transaction.Type.RESTOCK
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        stock = self.inventory.sort_stock_counts(sort_order=Misc.SortOrder.ASC, only_available_stock=False)

        for i, (item, count) in enumerate(stock): print(f"{MenuPrompt.stock_list_options(i=i, part_no=item.part_no, count=count)}")
        
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=self.page, transaction_type=self.transaction_type), input_type=int, allowed_val=[i+1 for i in range(len(stock))])
        if selection is None: 
            print(SysMsgView.get_input_error_message(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT))
            action = rules.get_input_error_action(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
            ActionDispatcher.execute(app_context=self, action=action, timeout=5)
            return
        
        selected_part_no = stock[selection - 1][0].part_no
        self.transaction_screen(transaction_type=self.transaction_type, part_no=selected_part_no)

    def transaction_screen(self, transaction_type: int, part_no: str = None):
        """Handles transaction with user"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.TRANSACTION
        self.transaction_status = Transaction.Status.NONE
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        self.transaction_status = Transaction.Status.IN_PROGRESS
        self.transaction_status, err_code, container = self.transaction.process(transaction_type=transaction_type, part_no=part_no)
        container_id = container.id if container else 0

        if self.transaction_status == Transaction.Status.FAILED: 
            print(ServiceMessage.transaction_message(transaction_status=self.transaction_status, error_code=err_code, transaction_type=transaction_type, container_id=container_id))
            time.sleep(2)
            action = rules.get_transaction_action(transaction_status=self.transaction_status)
            ActionDispatcher.execute(app_context=self, action=action, container=container)
            return
        
        selection, input_err = self._get_user_input(prompt=ServiceMessage.transaction_message(transaction_status=self.transaction_status, error_code=err_code, transaction_type=transaction_type, container_id=container_id), input_type=int, allowed_val=[Misc.Confirm.YES, Misc.Confirm.NO])
        self.transaction_status = Transaction.Status.CONFIRMED if selection == Misc.Confirm.YES else Transaction.Status.CANCELLED
        action = rules.get_transaction_action(transaction_status=self.transaction_status)
        self.transaction_status = ActionDispatcher.execute(app_context=self, action=action, transaction_type=transaction_type, part_no=part_no, container=container)

        print(ServiceMessage.transaction_message(transaction_status=self.transaction_status, error_code=0, transaction_type=transaction_type, container_id=container_id))
        time.sleep(5)
        return
    
    def dir_ops_screen(self):
        """Handles user selection of directory operations"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.DIR_OPS
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        selection, err_code = self._get_user_input(prompt=MenuPrompt.directory_ops_options(), input_type=int, allowed_val=[DirectoryOp.Type.ADD, DirectoryOp.Type.DELETE, DirectoryOp.Type.UPDATE], timeout=60)
        if selection is None: action, message = self._handle_input_error(err_code=err_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return

        action = rules.get_directory_action(selection=selection)
        ActionDispatcher.execute(app_context=self, action=action)

    def dir_add_screen(self):
        """Handles user input of new item to add to directory"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.ADD_DIR
        self.dir_op_type = DirectoryOp.Type.ADD
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        part_no, msg_code = self._get_user_input(prompt=InputPrompt.directory_add_string(input_type=DirectoryOp.Add.PART_NO), input_type=str, max_len=15, force_upper=True, timeout=60)
        if part_no is None: action, message = self._handle_input_error(err_code=msg_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        manufacturer, msg_code = self._get_user_input(prompt=InputPrompt.directory_add_string(input_type=DirectoryOp.Add.MANUFACTURER), input_type=str, max_len=15, force_upper=True, timeout=60)
        if manufacturer is None: action, message = self._handle_input_error(err_code=msg_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        description, msg_code = self._get_user_input(prompt=InputPrompt.directory_add_string(input_type=DirectoryOp.Add.DESCRIPTION), input_type=str, max_len=15, force_upper=True, timeout=60)
        if description is None: action, message = self._handle_input_error(err_code=msg_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        selection, err_code = self._get_user_input(prompt=InputPrompt.directory_proceed(dir_op_type=self.dir_op_type, part_no=part_no, manufacturer=manufacturer, description=description), input_type=int, allowed_val=[Misc.Confirm.YES, Misc.Confirm.NO], timeout=60)
        if selection is None: action, message = self._handle_input_error(err_code=err_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        if selection == Misc.Confirm.YES:
            self.directory.add_item(part_no=part_no, manufacturer=manufacturer, description=description)
            print(ServiceMessage.directory_message(dir_op_type=self.dir_op_type, part_no=part_no))
            time.sleep(2)
            
        return
                 
    def dir_delete_screen(self):
        """Handles user input of new item to delete from directory"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.DELETE_DIR
        self.dir_op_type = DirectoryOp.Type.DELETE
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        dir_items = self.directory.get_all_items()

        for i, item in enumerate(dir_items): print(f"{MenuPrompt.dir_list_options(i=i, part_no=item.part_no)}")
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=self.page, dir_op_type=self.dir_op_type), input_type=int, allowed_val=[i+1 for i in range(len(dir_items))])
        if selection is None: action, message = self._handle_input_error(err_code=err_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        selected_part_no = dir_items[selection - 1].part_no
        inv_present = self.directory.check_inventory(part_no=selected_part_no)
        
        if inv_present: 
            print(SysMsgView.directory_inventory_error(part_no=selected_part_no))
            time.sleep(5)
            return

        selection, err_code = self._get_user_input(prompt=InputPrompt.directory_proceed(dir_op_type=self.dir_op_type, part_no=dir_items[selection - 1].part_no, manufacturer=dir_items[selection - 1].manufacturer, description=dir_items[selection - 1].description), input_type=int, allowed_val=[Misc.Confirm.YES, Misc.Confirm.NO], timeout=60)
        if selection is None: action, message = self._handle_input_error(err_code=err_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return

        if selection == Misc.Confirm.YES:
            self.directory.delete_item(part_no=selected_part_no)
            print(ServiceMessage.directory_message(dir_op_type=self.dir_op_type, part_no=selected_part_no))
            time.sleep(2)
            
        return
    
    def dir_update_screen(self):
        """Handles user input of item to update in directory"""
        UIFormatter.clear_screen()
        self.page = UI.UIPage.UPDATE_DIR
        self.dir_op_type = DirectoryOp.Type.UPDATE
        print(UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        dir_items = self.directory.get_all_items()

        for i, item in enumerate(dir_items): print(f"{MenuPrompt.dir_list_options(i=i, part_no=item.part_no)}")
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=self.page, dir_op_type=self.dir_op_type), input_type=int, allowed_val=[i+1 for i in range(len(dir_items))])
        if selection is None: action, message = self._handle_input_error(err_code=err_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return

        part_no, msg_code = self._get_user_input(prompt=InputPrompt.directory_add_string(input_type=DirectoryOp.Update.PART_NO), input_type=str, max_len=15, force_upper=True, timeout=60)
        if part_no is None: action, message = self._handle_input_error(err_code=msg_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        manufacturer, msg_code = self._get_user_input(prompt=InputPrompt.directory_add_string(input_type=DirectoryOp.Update.MANUFACTURER), input_type=str, max_len=15, force_upper=True, timeout=60)
        if manufacturer is None: action, message = self._handle_input_error(err_code=msg_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        description, msg_code = self._get_user_input(prompt=InputPrompt.directory_add_string(input_type=DirectoryOp.Update.DESCRIPTION), input_type=str, max_len=15, force_upper=True, timeout=60)
        if description is None: action, message = self._handle_input_error(err_code=msg_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return
        
        selection, err_code = self._get_user_input(prompt=InputPrompt.directory_proceed(dir_op_type=self.dir_op_type, part_no=part_no, manufacturer=manufacturer, description=description), input_type=int, allowed_val=[Misc.Confirm.YES, Misc.Confirm.NO], timeout=60)
        if selection is None: action, message = self._handle_input_error(err_code=err_code); print(message); ActionDispatcher.execute(app_context=self, action=action); return

        if selection == Misc.Confirm.YES:
            self.directory.update_item(part_no=part_no, manufacturer=manufacturer, description=description)
            print(ServiceMessage.directory_message(dir_op_type=self.dir_op_type, part_no=part_no))
            time.sleep(2)

        return
        
    def mod_ops_screen(self):
        """Handles user selection of module operations"""
        pass

    # ========== HELPER FUNCTIONS ================================================

    def _get_user_input(self, prompt: str, input_type: Type[T], allowed_val: Optional[List[T]] = None, max_len: int = None, timeout: int = None, msg_code: str = None, force_upper: bool = True) -> Optional[T]:
        while True:
            try:
                raw_input = inputimeout(prompt=prompt, timeout=timeout) if timeout else input(prompt).strip()
            except TimeoutOccurred:
                return None, SystemMessage.Input.TIMEOUT

            if not raw_input: return None, None
            if max_len and len(raw_input) > max_len:
                return None, SystemMessage.Input.MAX_LENGTH
            
            if input_type is str and force_upper: raw_input = raw_input.upper()
            
            try:
                input_value = input_type(raw_input)
                if allowed_val is not None and input_value not in allowed_val: raise ValueError
                return input_value, None
            except ValueError:
                return None, SystemMessage.Input.INVALID
            
    def _wait_for_enter(self, timeout: int = None) -> bool:
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if msvcrt.kbhit():
                msvcrt.getch()
                print()
                return True
            time.sleep(0.05)
        return False
    
    def _handle_input_error(self, err_code: int) -> Tuple[Tuple[Optional[str], Optional[str]], str]:
        message = SysMsgView.get_input_error_message(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
        action = rules.get_input_error_action(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
        return action, message