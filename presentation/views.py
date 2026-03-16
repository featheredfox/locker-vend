import os
import subprocess
from typing import Optional
from core.enums import UserLevel, PageID, DashboardAction, TxType, TxStatus, TxError, DirAction, ConfirmChoice, DirField, TimeoutAction, InputError

class UIFormatter:
    @staticmethod
    def clear_screen():
        subprocess.run('cls' if os.name == 'nt' else 'clear', shell=True)

    @staticmethod
    def page_header(page: int, width: int = 50, username: str = None, user_level: int = None) -> str:
        """Generates centered header with borders"""
        user = f'Logged in as: {username}. Level: {UIFormatter.get_user_level_name(user_level)}' if username else ''
        title = "UNKNOWN PAGE"
        match page:
            case PageID.LOGIN: title = 'USER LOGIN'
            case PageID.DASHBOARD: title = 'DASHBOARD'
            case PageID.TAKE: title = 'TAKE ITEM'
            case PageID.RESTOCK: title = 'RESTOCK ITEM'
            case PageID.TRANSACTION: title = 'TRANSACTION'
            case PageID.DIR_OPS: title = 'DIRECTORY OPERATIONS'
            case PageID.ADD_DIR: title = 'ADD ITEM TO DIRECTORY'
            case PageID.DELETE_DIR: title = 'DELETE ITEM FROM DIRECTORY'
            case PageID.UPDATE_DIR: title = 'UPDATE ITEM IN DIRECTORY'

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
    def action_string(tx_type: Optional[int] = None, dir_action: Optional[int] = None) -> str:
        match tx_type:
            case TxType.TAKE: return 'TAKE'
            case TxType.RESTOCK: return 'RESTOCK'

        match dir_action:
            case DirAction.ADD: return 'ADD'
            case DirAction.DELETE: return 'DELETE'
            case DirAction.UPDATE: return 'UPDATE'
            
        return 'PROCESS' # Fallback to prevent returning None
    
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

class InputPrompt:
    @staticmethod
    def confirm_action() -> str:
        return f"\n>> [{ConfirmChoice.YES}] Yes / [{ConfirmChoice.NO}] No: "
    
    @staticmethod
    def directory_add_string(input_type: int) -> str:
        match input_type:
            case DirField.PART_NO: return "\n>> Enter Part Number: "
            case DirField.MANUFACTURER: return "\n>> Enter Manufacturer: "
            case DirField.DESCRIPTION: return "\n>> Enter Description: "

    @staticmethod
    def directory_proceed(dir_action: int, part_no: str, manufacturer: str, description: str, width: int = 60) -> str:
        border = "=" * width
        centered_item = f"{part_no} | {manufacturer} | {description}".upper().center(width)

        match dir_action:
            case DirAction.ADD: prompt = f"\n>> Add this item to directory? {InputPrompt.confirm_action()}"
            case DirAction.DELETE: prompt = f"\n>> Delete this item from directory? {InputPrompt.confirm_action()}"
            case DirAction.UPDATE: prompt = f"\n>> Update this item in directory? {InputPrompt.confirm_action()}"

        return f"{border}\n{centered_item}\n{border}\n{prompt}"

class MenuPrompt:
    @staticmethod
    def dashboard_options(allowed_actions: list[int]) -> str:
        options = "\n>> Options:\n"
        for action in allowed_actions:
            match action:
                case DashboardAction.TAKE: options += f"\n[{DashboardAction.TAKE}] Take"
                case DashboardAction.RESTOCK: options += f"\n[{DashboardAction.RESTOCK}] Restock"
                case DashboardAction.DIR_OPS: options += f"\n[{DashboardAction.DIR_OPS}] Directory Operations"
                case DashboardAction.MOD_OPS: options += f"\n[{DashboardAction.MOD_OPS}] Module Operations"
                case DashboardAction.CONFIG: options += f"\n[{DashboardAction.CONFIG}] Configuration"
                case DashboardAction.CHNG_PIN: options += f"\n[{DashboardAction.CHNG_PIN}] Change PIN"
                case DashboardAction.LOGOUT: options += f"\n[{DashboardAction.LOGOUT}] Logout\n"
        options += "\n>> Enter selection: "
        return options
    
    @staticmethod
    def directory_ops_options() -> str:
        options = "\n>> Options:\n"
        options += f"\n[{DirAction.ADD}] Add"
        options += f"\n[{DirAction.DELETE}] Delete"
        options += f"\n[{DirAction.UPDATE}] Update\n"
        options += "\n>> Enter selection: "
        return options
    
    @staticmethod
    def stock_list_options(i: int, part_no: str, count: int) -> str:
        return f" [{i+1}] {part_no} ({count} in stock)"
    
    @staticmethod
    def dir_list_options(i: int, part_no: str) -> str:
        return f" [{i+1}] {part_no}"
    
    @staticmethod
    def item_selection(page: int, tx_type: Optional[int] = None, dir_action: Optional[int] = None) -> str:
        action_str = UIFormatter.action_string(tx_type=tx_type, dir_action=dir_action)
        if not tx_type and not dir_action: return f"\n>> No items to {action_str}. Press enter to return to dashboard..."
        return f"\n>> Select an item to {action_str}:\n"

class ServiceMessage:
    @staticmethod
    def transaction_message(transaction_status: int, error_code: int, tx_type: int, container_id: int) -> str:
        context_str = 'from' if tx_type == TxType.TAKE else 'to'
        error_msg = "Unknown error occurred." # Fallback to prevent UnboundLocalError
        
        if error_code:
            match error_code:
                case TxError.UNLOCK_FAILED: error_msg = "Container unlock failed."
                case TxError.CONTAINER_NOT_CLOSED: error_msg = f"Container not closed. Status of container #{container_id} UNKNOWN!"
                case TxError.USER_NOT_CONFIRMED: error_msg = f"Transaction not confirmed by user. Status of container #{container_id} UNKNOWN!"
       
        match transaction_status:
            case TxStatus.NONE: return "\nNo container available"
            case TxStatus.IN_PROGRESS: return f"\nPlease {UIFormatter.action_string(tx_type)} item {context_str} Container #{container_id}"
            case TxStatus.AWAIT_CONFIRMATION: return f"\nDid you successfully {UIFormatter.action_string(tx_type)} {context_str} Container #{container_id}? {InputPrompt.confirm_action()}"
            case TxStatus.CONFIRMED: return f"\nTransaction confirmed."
            case TxStatus.COMPLETE: return "\nTransaction complete."
            case TxStatus.FAILED: return f"\nTransaction failure. - {error_msg}"
            case TxStatus.CANCELLED: return f"\nTransaction with Container #{container_id} cancelled."

    @staticmethod
    def directory_message(dir_action: int, part_no: str) -> str:
        match dir_action:
            case DirAction.ADD: return f"\nItem {part_no} added to directory."
            case DirAction.DELETE: return f"\nItem {part_no} deleted from directory."
            case DirAction.UPDATE: return f"\nItem {part_no} updated in directory."
    
class SystemMessage:
    @staticmethod
    def get_input_error_message(err_code: int, timeout_action: int = None) -> str:
        timeout = "\n[TIMEOUT] Input period expired."
        match timeout_action:
            case TimeoutAction.LOGOUT: timeout += " Logging out..."
            case TimeoutAction.RETRY: timeout += " Press enter to try again..."
        
        match err_code:
            case InputError.TIMEOUT: return timeout
            case InputError.MAX_LENGTH: return "\n[ERROR] Input exceeds maximum length. Press enter to try again..."
            case InputError.INVALID: return "\n[ERROR] Invalid input or selection. Press enter to try again..."
            case _: return "\n[ERROR] An unknown error occurred."

    @staticmethod
    def directory_inventory_error(part_no: str) -> str:
        return f"\n[ERROR] Item {part_no} showing active inventory. Unable to delete entry - remove physical inventory and try again..."