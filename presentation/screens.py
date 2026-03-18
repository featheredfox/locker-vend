import time
import msvcrt
from typing import TypeVar, Type, Optional, List, Tuple
from inputimeout import inputimeout, TimeoutOccurred

from core.enums import PageID, DashboardAction, InputError, TimeoutAction, ConfirmChoice, SortOrder, TxType, TxStatus, TxError, DirAction, DirField, DirMessage, CntAction, CntError, CntMessage, CntField
from presentation.views import UIFormatter, AuthPrompt, MenuPrompt, InputPrompt, ServiceMessage, SystemMessage as SysMsgView
import business_logic.rules as rules

T = TypeVar('T')

class BaseScreen:
    """The template that all screens must follow."""
    def __init__(self, app_context, **kwargs):
        self.app = app_context
        self.kwargs = kwargs

    def render(self):
        """Every screen must implement its own render logic."""
        raise NotImplementedError

    def _get_user_input(self, prompt: str, input_type: Type[T], allowed_val: Optional[List[T]] = None, max_len: int = None, timeout: int = None, force_upper: bool = True) -> Tuple[Optional[T], Optional[int]]:
        
        # Split multi-line prompts to prevent display bugs when backspacing in inputimeout
        prompt_lines = prompt.rsplit('\n', 1)
        if len(prompt_lines) > 1:
            print(prompt_lines[0])
            input_prompt = prompt_lines[1]
        else:
            input_prompt = prompt
            
        while True:
            try:
                raw_input = inputimeout(prompt=input_prompt, timeout=timeout) if timeout else input(input_prompt).strip()
            except TimeoutOccurred:
                return None, InputError.TIMEOUT

            if not raw_input: return None, None
            if max_len and len(raw_input) > max_len:
                return None, InputError.MAX_LENGTH
            
            if input_type is str and force_upper: raw_input = raw_input.upper()
            
            try:
                input_value = input_type(raw_input)
                if allowed_val is not None and input_value not in allowed_val: raise ValueError
                return input_value, None
            except ValueError:
                return None, InputError.INVALID
            
    def _wait_for_enter(self, timeout: int = None) -> bool:
        start_time = time.time()
        while timeout is None or (time.time() - start_time) < timeout:
            if msvcrt.kbhit():
                msvcrt.getch()
                print()
                return True
            time.sleep(0.05)
        return False
    
    def _handle_input_error(self, err_code: int) -> None:
        message = SysMsgView.get_input_error_message(err_code=err_code, timeout_action=TimeoutAction.LOGOUT)
        print(message)
        action = rules.get_input_error_action(err_code=err_code, timeout_action=TimeoutAction.LOGOUT)
        rules.ActionDispatcher.execute(app_context=self.app, action=action, timeout=5)

    def _get_multiple_inputs(self, field_configs: list[dict]) -> Tuple[Optional[tuple], Optional[int]]:
        """
        Iterates through a list of input configurations. 
        Returns a tuple of all results, or aborts if any single input fails/times out.
        """
        results = []
        
        for config in field_configs:
            # Unpack the dictionary directly into your existing input method
            value, err_code = self._get_user_input(**config)
            
            # If the user timed out or hit enter without typing, abort the whole chain!
            if value is None:
                return None, err_code
                
            results.append(value)
            
        # Convert the final list of answers into an immutable tuple and return it
        return tuple(results), None
        


# =========================================================================================
# INDIVIDUAL SCREENS
# =========================================================================================

# ========== USER LOGIN ===================================================================

class LoginScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.LOGIN))
        
        username, err_code = self._get_user_input(prompt=AuthPrompt.enter_username(), input_type=str, max_len=15, force_upper=True)
        pin, err_code = self._get_user_input(prompt=AuthPrompt.enter_pin(), input_type=int, max_len=4)
        
        if self.app.auth.login(username=username, pin=pin):
            self.app.set_screen('DashboardScreen')
        else:
            self._get_user_input(prompt=AuthPrompt.invalid_credentials(), input_type=str)

# ========== MAIN DASHBOARD ===============================================================

class DashboardScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.DASHBOARD, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))
        
        allowed_actions = rules.get_allowed_dashboard_actions(user_level=self.app.auth.get_user_level())
        prompt_str = MenuPrompt.dashboard_options(allowed_actions=allowed_actions)
        
        selection, err_code = self._get_user_input(prompt=prompt_str, input_type=int, allowed_val=allowed_actions, timeout=60)
        
        if selection is None: 
            self._handle_input_error(err_code)
            return
        
        action = rules.get_dashboard_action(selection=selection)
        rules.ActionDispatcher.execute(app_context=self.app, action=action)

# ========== TRANSACTIONS =================================================================

class TakeScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.TAKE, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        stock, err_code = self.app.inventory.sort_stock_counts(sort_order=SortOrder.DESC, only_available_stock=True)
        if not stock: print(ServiceMessage.inventory_error(err_code=err_code)); self._wait_for_enter(timeout=5); self.app.set_screen('DashboardScreen'); return

        for i, (item, count) in enumerate(stock): 
            print(MenuPrompt.stock_list_options(i=i, part_no=item.part_no, count=count))
        
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=PageID.TAKE, tx_type=TxType.TAKE), input_type=int, allowed_val=[i+1 for i in range(len(stock))], timeout=60)
        if selection is None: 
            self._handle_input_error(err_code)
            return
        
        selected_part_no = stock[selection - 1][0].part_no
        self.app.set_screen('TransactionScreen', tx_type=TxType.TAKE, part_no=selected_part_no)

class RestockScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.RESTOCK, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        items, err_code = self.app.inventory.sort_stock_counts(sort_order=SortOrder.ASC, only_available_stock=False)
        if not items: print(ServiceMessage.inventory_error(err_code=err_code)); self._wait_for_enter(timeout=5); self.app.set_screen('DashboardScreen'); return

        for i, (item, count) in enumerate(items): 
            print(MenuPrompt.stock_list_options(i=i, part_no=item.part_no, count=count))
        
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=PageID.RESTOCK, tx_type=TxType.RESTOCK), input_type=int, allowed_val=[i+1 for i in range(len(items))])
        if selection is None: 
            self._handle_input_error(err_code)
            return
        
        selected_part_no = items[selection - 1][0].part_no
        self.app.set_screen('TransactionScreen', tx_type=TxType.RESTOCK, part_no=selected_part_no)

class TransactionScreen(BaseScreen):
    def render(self):
        # Retrieve the variables passed into the screen!
        tx_type = self.kwargs.get('tx_type')
        part_no = self.kwargs.get('part_no')

        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.TRANSACTION, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        tx_status = TxStatus.IN_PROGRESS
        tx_status, err_code, container, cnt_assi_stat = self.app.transaction.process(tx_type=tx_type, part_no=part_no)
        container_id = container.id if container else 0

        if tx_status == TxStatus.FAILED: 
            print(ServiceMessage.transaction_message(tx_status=tx_status, error_code=err_code, tx_type=tx_type, container_id=container_id))
            time.sleep(2)
            action = rules.get_transaction_action(tx_status=tx_status)
            rules.ActionDispatcher.execute(app_context=self.app, action=action, container=container)
            self.app.set_screen('DashboardScreen') 
            return
        
        selection, input_err = self._get_user_input(prompt=ServiceMessage.transaction_message(tx_status=tx_status, error_code=err_code, tx_type=tx_type, container_id=container_id, assi_stat=cnt_assi_stat), input_type=int, allowed_val=[ConfirmChoice.YES, ConfirmChoice.NO])
        tx_status = TxStatus.CONFIRMED if selection == ConfirmChoice.YES else TxStatus.CANCELLED
        
        action = rules.get_transaction_action(tx_status=tx_status)
        tx_status = rules.ActionDispatcher.execute(app_context=self.app, action=action, tx_type=tx_type, part_no=part_no, container=container)

        print(ServiceMessage.transaction_message(tx_status=tx_status, error_code=0, tx_type=tx_type, container_id=container_id))
        time.sleep(5)
        self.app.set_screen('DashboardScreen')

# ========== DIRECTORY OPERATIONS ===============================================================

class DirectoryOpsScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.DIR_ACTIONS, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        selection, err_code = self._get_user_input(prompt=MenuPrompt.directory_ops_options(), input_type=int, allowed_val=[DirAction.ADD, DirAction.DELETE, DirAction.UPDATE], timeout=60)
        if selection is None: 
            self._handle_input_error(err_code)
            return

        action = rules.get_directory_action(selection=selection)
        rules.ActionDispatcher.execute(app_context=self.app, action=action)

class DirAddScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.ADD_DIR, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        fields_to_collect = rules.get_input_fields(page=PageID.ADD_DIR)
        results, msg_code = self._get_multiple_inputs(field_configs=fields_to_collect)
        
        # Safely catch timeouts or escapes
        if results is None: self._handle_input_error(msg_code); return
        
        part_no, manufacturer, description = results
        
        selection, err_code = self._get_user_input(
            prompt=InputPrompt.directory_proceed(dir_op_type=DirAction.ADD, part_no=part_no, manufacturer=manufacturer, description=description), 
            input_type=int, allowed_val=[ConfirmChoice.YES, ConfirmChoice.NO], timeout=60
        )
        if selection is None: self._handle_input_error(err_code); return
        if selection == ConfirmChoice.YES:
            self.app.directory.add_item(part_no=part_no, manufacturer=manufacturer, description=description)
            print(ServiceMessage.directory_message(dir_op_type=DirAction.ADD, part_no=part_no))
            time.sleep(2)
            
        self.app.set_screen('DirectoryOpsScreen')

class DirDeleteScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.DELETE_DIR, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        dir_items = self.app.directory.get_all_items()

        for i, item in enumerate(dir_items): print(MenuPrompt.dir_list_options(i=i, part_no=item.part_no))
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=PageID.DELETE_DIR, dir_action=DirAction.DELETE), input_type=int, allowed_val=[i+1 for i in range(len(dir_items))])
        
        if selection is None: 
            self._handle_input_error(err_code)
            return
        
        selected_part_no = dir_items[selection - 1].part_no
        inv_present = self.app.directory.check_inventory(part_no=selected_part_no)
        
        if inv_present: 
            print(SysMsgView.directory_inventory_error(part_no=selected_part_no))
            time.sleep(5)
            self.app.set_screen('DirectoryOpsScreen')
            return 

        selection, err_code = self._get_user_input(prompt=InputPrompt.directory_proceed(dir_action=DirAction.DELETE, part_no=dir_items[selection - 1].part_no, manufacturer=dir_items[selection - 1].manufacturer, description=dir_items[selection - 1].description), input_type=int, allowed_val=[ConfirmChoice.YES, ConfirmChoice.NO], timeout=60)
        if selection is None: self._handle_input_error(err_code); return

        if selection == ConfirmChoice.YES:
            self.app.directory.delete_item(part_no=selected_part_no)
            print(ServiceMessage.directory_message(dir_action=DirAction.DELETE, part_no=selected_part_no))
            time.sleep(2)
            
        self.app.set_screen('DirectoryOpsScreen')

class DirUpdateScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.UPDATE_DIR, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        dir_items = self.app.directory.get_all_items()

        for i, item in enumerate(dir_items): print(MenuPrompt.dir_list_options(i=i, part_no=item.part_no))
        selection, err_code = self._get_user_input(prompt=MenuPrompt.item_selection(page=PageID.UPDATE_DIR, dir_action=DirAction.UPDATE), input_type=int, allowed_val=[i+1 for i in range(len(dir_items))])
        if selection is None: self._handle_input_error(err_code); return

        fields_to_collect = rules.get_input_fields(page=PageID.UPDATE_DIR)
        results, msg_code = self._get_multiple_inputs(field_configs=fields_to_collect)
        
        # Safely catch timeouts or escapes
        if results is None: self._handle_input_error(msg_code); return
        
        part_no, manufacturer, description = results
        
        selection, err_code = self._get_user_input(prompt=InputPrompt.directory_proceed(dir_action=DirAction.ADD, part_no=part_no, manufacturer=manufacturer, description=description), input_type=int, allowed_val=[ConfirmChoice.YES, ConfirmChoice.NO], timeout=60)
        if selection is None: self._handle_input_error(err_code); return
 
        if selection == ConfirmChoice.YES:
            self.app.directory.update_item(part_no=part_no, manufacturer=manufacturer, description=description)
            print(ServiceMessage.directory_message(dir_action=DirAction.UPDATE, part_no=part_no))
            time.sleep(2)
            
        self.app.set_screen('DirectoryOpsScreen')

# ========== CONTAINER OPERATIONS ===================================================================

class ContainerOpsScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.CNT_OPS, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))

        selection, err_code = self._get_user_input(prompt=MenuPrompt.container_ops_options(), input_type=int, allowed_val=[CntAction.ADD, CntAction.DELETE, CntAction.ASSIGN, CntAction.UNASSIGN], timeout=60)
        if selection is None: 
            self._handle_input_error(err_code)
            return

        action = rules.get_cnt_action(selection=selection)
        rules.ActionDispatcher.execute(app_context=self.app, action=action)

class CntAddScreen(BaseScreen):
    def render(self):
        UIFormatter.clear_screen()
        print(UIFormatter.page_header(page=PageID.ADD_CNT, username=self.app.auth.current_user.username.upper(), user_level=self.app.auth.get_user_level()))
        
        fields_to_collect = rules.get_input_fields(page=PageID.ADD_CNT)
        results, msg_code = self._get_multiple_inputs(field_configs=fields_to_collect)
        
        # Safely catch timeouts or escapes
        if results is None: self._handle_input_error(msg_code); return
        
        selection, err_code = self._get_user_input(
            prompt=InputPrompt.container_proceed(cnt_action=CntAction.ADD, container_id=None, pins=results), 
            input_type=int, allowed_val=[ConfirmChoice.YES, ConfirmChoice.NO], timeout=60
        )
        if selection is None: self._handle_input_error(err_code); return
        if selection == ConfirmChoice.YES:
            new_container_id, msg_code = self.app.container.add(pins=results)
            print(ServiceMessage.container_message(cnt_action=CntAction.ADD, msg_code=msg_code, err_code=None, container_id=new_container_id, part_no=None))
            time.sleep(2)
            
        self.app.set_screen('DirectoryOpsScreen')

class ConfigScreen(BaseScreen):
    def render(self): pass
class ChangePinScreen(BaseScreen):
    def render(self): pass