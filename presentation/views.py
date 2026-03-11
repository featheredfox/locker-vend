from core.enums import UIPage

class View:

    class UIFormatter:
        @staticmethod
        def page_header(page: int, width: int = 50) -> str:
            """Generates centered header with borders"""
            match page:
                case UIPage.LOGIN: title = "USER LOGIN"

            border = "=" * width
            centered_title = title.upper().center(width)
            return f"{border}\n{centered_title}\n{border}"

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
