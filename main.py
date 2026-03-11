from data_access.models import init_db
from presentation.cli import VendingMachineCLI

def main():
    init_db()
    app = VendingMachineCLI()
    
    try:
        app.start()
    except KeyboardInterrupt:
        print("\n\nShutting down Vending Machine...")

if __name__ == "__main__":
    main()