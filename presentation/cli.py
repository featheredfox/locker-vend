import os
import subprocess
from typing import TypeVar, Type, Optional, List, Tuple
from inputimeout import inputimeout, TimeoutOccurred
from business_logic.services import AuthService
from core.enums import UIPage, SystemMessage
from presentation.views import View
from data_access.models import SessionLocal
from data_access.repositories import UserRepository
from business_logic.services import DatabaseSeeder



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

    def clear_screen(self):
        subprocess.run('cls' if os.name == 'nt' else 'clear', shell=True)

    def start(self):
        while True:
            if not self.auth.current_user:
                self.login_screen()
            else:
                self.dashboard_screen()

    def login_screen(self):
        """Handles user credential input"""
        self.clear_screen()
        self.page = UIPage.LOGIN
        print(self.view.UIFormatter.page_header(self.page))
        
        username, msg_code = self._get_user_input(prompt=self.view.AuthPrompt.enter_username(), input_type=str, max_len=15, force_upper=True)
        pin, msg_code = self._get_user_input(prompt=self.view.AuthPrompt.enter_pin(), input_type=int, max_len=4)
        
        if not self.auth.login(username=username, pin=pin):
            comeplete, msg_code = self._get_user_input(prompt=self.view.AuthPrompt.invalid_credentials(), input_type=str)
            self.login_screen()

        print("Login successful!") # FOR TESTING

    def dashboard_screen(self):
        """Handles user selection of actions"""
        self.page = UIPage.DASHBOARD
        self.view.UIFormatter.page_header(self.page)



    
    def _get_user_input(self, prompt: str, input_type: Type[T], allowed_val: Optional[List[T]] = None, max_len: int = None, timeout: int = None, msg_code: str = None, force_upper: bool = True) -> Optional[T]:
        while True:
            try:
                raw_input = inputimeout(prompt=prompt, timeout=timeout) if timeout else input(prompt).strip()
            except TimeoutOccurred:
                return None, SystemMessage.INPUT_TIMEOUT 

            if not raw_input: return None, None
            if max_len and len(raw_input) > max_len:
                return None, SystemMessage.MAX_LENGTH_EXCEEDED

            if input_type is str and force_upper: raw_input = raw_input.upper()
            
            try:
                input_value = input_type(raw_input)
                if allowed_val is not None and input_value not in allowed_val: raise ValueError
                return input_value, None
            except ValueError:
                return None, SystemMessage.INVALID_INPUT