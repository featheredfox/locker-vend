import sys
import time
import msvcrt
from typing import TypeVar, Type, Optional, List, Tuple
from inputimeout import inputimeout, TimeoutOccurred
from business_logic.services import AuthService
from core.enums import UI, SystemMessage
from presentation.views import View
from data_access.models import SessionLocal
from data_access.repositories import UserRepository
from business_logic.services import DatabaseSeeder
import business_logic.rules as rules



T = TypeVar('T')

class VendingMachineCLI:

    def __init__(self):
        self.session = SessionLocal()
        
        self.page = 0
        self.transaction_type = 0

        self.view = View()
        
        self.user_repo = UserRepository(self.session)
        self.auth = AuthService(self.user_repo)

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
            self._execute_action(action=action, timeout=5)
            return
        
        # action = rules.get_dashboard_action(selection)
        # self._execute_action(action)
        
        # FOR TESTING
        if selection:
            input("\nSELECTION SUCCESSFUL")
            return
        else:
            input("\nSELECTION FAILED")
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
    
    def _execute_action(self, action: tuple, **kwargs):
        """Dynamically executes a method based on the rulebook's routing instructions."""
        OBJECT = 0
        METHOD = 1
        
        obj_name = action[OBJECT]
        method_name = action[METHOD]
        
        if not method_name:
            return 

        if obj_name is None:
            method_to_call = getattr(self, method_name)
        else:
            obj = getattr(self, obj_name)
            method_to_call = getattr(obj, method_name)
            
        return method_to_call(**kwargs)
            
            
