import time
from data_access.models import SessionLocal
from data_access.repositories import UserRepository, ContainerRepository, DirectoryRepository
from business_logic.services import AuthService, HardwareService, InventoryService, TransactionService, DirectoryService, DatabaseSeeder, ContainerService
from presentation import screens

class VendingMachineCLI:
    def __init__(self):
        self.session = SessionLocal()
        
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
        self.container = ContainerService(self.dir_repo, self.container_repo)
        
        DatabaseSeeder(self.session).seed()
        
        # UI State Manager
        self.current_screen = None

    def set_screen(self, screen_name: str, **kwargs):
        """Dynamically instantiates and switches to a new screen."""
        screen_class = getattr(screens, screen_name, None)
        if screen_class:
            self.current_screen = screen_class(self, **kwargs)
        else:
            print(f"\n[CRITICAL ERROR] Screen '{screen_name}' does not exist!")
            time.sleep(3)

    def start(self):
        """The Master Loop."""
        # Initialize the starting screen
        self.set_screen('LoginScreen')
        
        while True:
            # Security Check: If logged out, override and force the login screen
            if not self.auth.current_user and not isinstance(self.current_screen, screens.LoginScreen):
                self.set_screen('LoginScreen')
            
            # Tell the current active screen to draw itself!
            self.current_screen.render()