import sys
import time
import msvcrt
from typing import TypeVar, Type, Optional, List, Tuple
from inputimeout import inputimeout, TimeoutOccurred
from business_logic.services import AuthService
from core.enums import UI, Transaction, SystemMessage, Misc
from presentation.views import View
from data_access.models import SessionLocal
from data_access.repositories import UserRepository, ContainerRepository, DirectoryRepository
from business_logic.services import TransactionService, InventoryService, DatabaseSeeder, HardwareService
import business_logic.rules as rules
from business_logic.rules import ActionDispatcher

T = TypeVar('T')

class VendingMachineCLI:

    def __init__(self):
        self.session = SessionLocal()
        
        self.page = 0
        self.transaction_type = 0

        self.view = View()
        
        # Repositories
        self.user_repo = UserRepository(self.session)
        self.container_repo = ContainerRepository(self.session)
        self.dir_repo = DirectoryRepository(self.session)

        # Services
        self.auth = AuthService(self.user_repo)
        self.hardware = HardwareService(self.container_repo)
        self.inventory = InventoryService(self.container_repo, self.dir_repo)
        self.transaction = TransactionService(self.container_repo, self.hardware)
        
        DatabaseSeeder(self.session).seed()

    def start(self):
        while True:
            if not self.auth.current_user:
                self.login_screen()
            else:
                self.dashboard_screen()

    def login_screen(self):
        """Handles user credential input"""
        self.view.UIFormatter.clear_screen()
        self.page = UI.UIPage.LOGIN
        print(self.view.UIFormatter.page_header(page=self.page))
        
        username, msg_code = self._get_user_input(prompt=self.view.AuthPrompt.enter_username(), input_type=str, max_len=15, force_upper=True)
        pin, msg_code = self._get_user_input(prompt=self.view.AuthPrompt.enter_pin(), input_type=int, max_len=4)
        
        if not self.auth.login(username=username, pin=pin):
            comeplete, msg_code = self._get_user_input(prompt=self.view.AuthPrompt.invalid_credentials(), input_type=str)
            self.login_screen()

        print("Login successful!") # FOR TESTING

    def dashboard_screen(self):
        """Handles user selection of actions"""
        self.view.UIFormatter.clear_screen()
        self.page = UI.UIPage.DASHBOARD
        print(self.view.UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))
        
        allowed_actions = rules.get_allowed_dashboard_actions(user_level=self.auth.get_user_level())
        
        prompt_str = self.view.MenuPrompt.dashboard_options(allowed_actions=allowed_actions)
        selection, err_code = self._get_user_input(prompt=prompt_str, input_type=int, allowed_val=allowed_actions, timeout=60)
        if selection is None: 
            print(self.view.SystemMessage.get_input_error_message(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT))
            action = rules.get_input_error_action(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
            ActionDispatcher.execute(app_context=self, action=action, timeout=5)
            return
        
        action = rules.get_dashboard_action(selection=selection)
        ActionDispatcher.execute(app_context=self, action=action)

    def take_screen(self):
        """Handles user selection of item to TAKE"""
        self.view.UIFormatter.clear_screen()
        self.page = UI.UIPage.TAKE
        self.transaction_type = Transaction.Type.TAKE
        print(self.view.UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        stock = self.inventory.sort_stock_counts(sort_order=Misc.SortOrder.DESC, only_available_stock=True)

        for i, (item, count) in enumerate(stock): print(f"{View.MenuPrompt.stock_list_options(i=i, part_no=item.part_no, count=count)}")
        selection, err_code = self._get_user_input(prompt=self.view.MenuPrompt.item_selection(page=self.page, transaction_type=self.transaction_type), input_type=int, allowed_val=[i+1 for i in range(len(stock))])
        if selection is None: 
            print(self.view.SystemMessage.get_input_error_message(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT))
            action = rules.get_input_error_action(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
            ActionDispatcher.execute(app_context=self, action=action, timeout=5)
            return
        
        selected_part_no = stock[selection - 1][0].part_no
        self.transaction_screen(transaction_type=self.transaction_type, part_no=selected_part_no)

    def restock_screen(self):
        """Handles user selection of item to RESTOCK"""
        self.view.UIFormatter.clear_screen()
        self.page = UI.UIPage.RESTOCK
        self.transaction_type = Transaction.Type.RESTOCK
        print(self.view.UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        stock = self.inventory.sort_stock_counts(sort_order=Misc.SortOrder.ASC, only_available_stock=False)

        for i, (item, count) in enumerate(stock): print(f"{View.MenuPrompt.stock_list_options(i=i, part_no=item.part_no, count=count)}")
        selection, err_code = self._get_user_input(prompt=self.view.MenuPrompt.item_selection(page=self.page, transaction_type=self.transaction_type), input_type=int, allowed_val=[i+1 for i in range(len(stock))])
        if selection is None: 
            print(self.view.SystemMessage.get_input_error_message(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT))
            action = rules.get_input_error_action(err_code=err_code, timeout_action=SystemMessage.Input.TimeoutAction.LOGOUT)
            ActionDispatcher.execute(app_context=self, action=action, timeout=5)
            return
        
        selected_part_no = stock[selection - 1][0].part_no
        self.transaction_screen(transaction_type=self.transaction_type, part_no=selected_part_no)

    def transaction_screen(self, transaction_type: int, part_no: str = None):
        """Handles transaction with user"""
        self.view.UIFormatter.clear_screen()
        self.page = UI.UIPage.TRANSACTION
        self.transaction_status = Transaction.Status.NONE
        print(self.view.UIFormatter.page_header(page=self.page, username=self.auth.current_user.username.upper(), user_level=self.auth.get_user_level()))

        self.transaction_status = Transaction.Status.IN_PROGRESS
        self.transaction_status, err_code, container = self.transaction.process(transaction_type=transaction_type, part_no=part_no)
        container_id = container.id if container else 0

        if self.transaction_status is Transaction.Status.FAILED: 
            print(self.view.ServiceMessage.transaction_message(transaction_status=self.transaction_status, error_code=err_code, transaction_type=transaction_type, container_id=container_id))
            time.sleep(2)
            action = rules.get_transaction_action(transaction_status=self.transaction_status)
            ActionDispatcher.execute(app_context=self, action=action, container=container)
            return
        
        selection, input_err = self._get_user_input(prompt=self.view.ServiceMessage.transaction_message(transaction_status=self.transaction_status, error_code=err_code, transaction_type=transaction_type, container_id=container_id), input_type=int, allowed_val=[Misc.Confirm.YES, Misc.Confirm.NO])
        self.transaction_status = Transaction.Status.CONFIRMED if selection == Misc.Confirm.YES else Transaction.Status.CANCELLED
        action = rules.get_transaction_action(transaction_status=self.transaction_status)
        self.transaction_status = ActionDispatcher.execute(app_context=self, action=action, transaction_type=transaction_type, part_no=part_no, container=container)

        print(View.ServiceMessage.transaction_message(transaction_status=self.transaction_status, error_code=0, transaction_type=transaction_type, container_id=container_id))
        time.sleep(5)
        return

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
            
            
