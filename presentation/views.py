import os
import subprocess
from core.enums import UserLevel, UI, SystemMessage, Transaction


class View:

    class UIFormatter:

        @staticmethod
        def clear_screen():
            subprocess.run('cls' if os.name == 'nt' else 'clear', shell=True)

        @staticmethod
        def page_header(page: int, width: int = 50, username: str = None, user_level: int = None, ) -> str:
            """Generates centered header with borders"""
            user = f'Logged in as: {username}. Level: {View.UIFormatter.get_user_level_name(user_level)}' if username else ''
            title = "UNKNOWN PAGE"
            match page:
                case UI.UIPage.LOGIN: title = 'USER LOGIN'
                case UI.UIPage.DASHBOARD: title = 'DASHBOARD'
                case UI.UIPage.TAKE: title = 'TAKE ITEM'
                case UI.UIPage.RESTOCK: title = 'RESTOCK ITEM'

            border = "=" * width
            centered_title = title.upper().center(width)
            return f"{user}\n{border}\n{centered_title}\n{border}\n"
        
        @staticmethod
        def get_user_level_name(user_level: int) -> str:
            match user_level:
                case UserLevel.OPERATOR: return 'Operator'
                case UserLevel.ADMIN: return 'Admin'
                case UserLevel.SUPER: return 'Super'
            return 'Unknown'
        
        @staticmethod
        def action_string(page: int, transaction_type: int) -> str:
            TAKE = 'TAKE'
            RESTOCK = 'RESTOCK'
            ADD = 'ADD'
            DELETE = 'DELETE'
            EDIT = 'EDIT'
            
            match transaction_type:
                case Transaction.Type.TAKE: return TAKE
                case Transaction.Type.RESTOCK: return RESTOCK

        
    class AuthPrompt:
        @staticmethod
        def enter_username() -> str:
            return "\n>> Enter username: "
        
        @staticmethod
        def enter_pin() -> str:
            return "\n>> Enter pin: "
        
        @staticmethod
        def invalid_credentials() -> str:
            return "\n>> Invalid credentials. Press Enter to try again..."
        
    class MenuPrompt:
        
        @staticmethod
        def dashboard_options(allowed_actions: list[int]) -> str:
            options = "\n>> Options:\n"
            for action in allowed_actions:
                match action:
                    case UI.DashboardActions.TAKE: options += f"\n[{UI.DashboardActions.TAKE}] Take"
                    case UI.DashboardActions.RESTOCK: options += f"\n[{UI.DashboardActions.RESTOCK}] Restock"
                    case UI.DashboardActions.DIR_OPS: options += f"\n[{UI.DashboardActions.DIR_OPS}] Directory Operations"
                    case UI.DashboardActions.MOD_OPS: options += f"\n[{UI.DashboardActions.MOD_OPS}] Module Operations"
                    case UI.DashboardActions.CONFIG: options += f"\n[{UI.DashboardActions.CONFIG}] Configuration"
                    case UI.DashboardActions.CHNG_PIN: options += f"\n[{UI.DashboardActions.CHNG_PIN}] Change PIN"
                    case UI.DashboardActions.LOGOUT: options += f"\n[{UI.DashboardActions.LOGOUT}] Logout\n"
            options += "\n>> Enter selection: "
            return options
        
        @staticmethod
        def stock_list_options(i: int, part_no: str, count: int) -> str:
            return f" [{i+1}] {part_no} ({count} in stock)"
        
        @staticmethod
        def item_selection(page: int, transaction_type: int) -> str:
            return f"\n>> Select an item to {View.UIFormatter.action_string(page=page, transaction_type=transaction_type)}:\n"
        
        
    class SystemMessage:

        @staticmethod
        def get_input_error_message(err_code: int, timeout_action: int = None) -> str:
            match timeout_action:
                case SystemMessage.Input.TimeoutAction.LOGOUT: timeout = "\n[TIMEOUT] Input period expired. Logging out..."
                case SystemMessage.Input.TimeoutAction.RETRY: timeout = "\n[TIMEOUT] Input period expired. Press enter to try again..."
            
            match err_code:
                case SystemMessage.Input.TIMEOUT: return timeout
                case SystemMessage.Input.MAX_LENGTH: return "\n[ERROR] Input exceeds maximum length. Press enter to try again..."
                case SystemMessage.Input.INVALID: return "\n[ERROR] Invalid input or selection. Press enter to try again..."
                case _: return "\n[ERROR] An unknown error occurred."

        
