import warnings
warnings.filterwarnings("ignore")

# Pandas and numpy are disabled for deployment
pd = None
np = None

try:
        HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not available. Some features will be limited.")
    class DummyDataFrame:
        def __getattr__(self, name):
            return self
        def __call__(self, *args, **kwargs):
            return self
    pd = DummyDataFrame()

try:
        HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("Warning: numpy not available")

try:
                HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available")
    plt = None
    mpatches = None
    FontProperties = None
import calendar
from datetime import datetime, timedelta
import os
import json
from tabulate import tabulate


class Account:
    """Account Class"""

    def __init__(self, account_id, name, initial_balance=0, currency='USD', notes=''):
        self.id = account_id
        self.name = name
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.currency = currency
        self.notes = notes
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'currency': self.currency,
            'notes': self.notes,
            'created_at': self.created_at
        }


class TradeAnalyzer:
    def __init__(self, data_dir="trading_data"):
        """
        Initialize trade analyzer (supports multiple accounts)
        """
        self.data_dir = data_dir
        self.accounts_file = os.path.join(data_dir, "accounts.json")
        self.accounts = {}
        self.current_account = None

        # Create data directory
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Load accounts
        self.load_accounts()

        # If no accounts exist, create a default account
        if not self.accounts:
            print("📢 No accounts found. Creating default account...")
            self.create_account("Default Account", 0, "USD", "Automatically created default account")

    def load_accounts(self):
        """Load all accounts"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    accounts_data = json.load(f)
                    for acc_data in accounts_data:
                        account = Account(
                            acc_data['id'],
                            acc_data['name'],
                            acc_data['initial_balance'],
                            acc_data.get('currency', 'USD'),
                            acc_data.get('notes', '')
                        )
                        account.current_balance = acc_data.get('current_balance', acc_data['initial_balance'])
                        account.created_at = acc_data.get('created_at', account.created_at)
                        self.accounts[acc_data['id']] = account
                print(f"📂 Loaded {len(self.accounts)} accounts")
            except Exception as e:
                print(f"⚠️ Failed to load accounts: {e}")

    def save_accounts(self):
        """Save all accounts"""
        accounts_data = [acc.to_dict() for acc in self.accounts.values()]
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(accounts_data, f, indent=2, ensure_ascii=False)

    def create_account(self, name, initial_balance=0, currency='USD', notes=''):
        """Create new account"""
        # Generate account ID
        account_id = f"ACC_{len(self.accounts) + 1:03d}"

        # Create account
        account = Account(account_id, name, initial_balance, currency, notes)
        self.accounts[account_id] = account

        # Create account's trade file
        self._ensure_account_file(account_id)

        # Save account information
        self.save_accounts()

        print(f"✅ Account created: {name} (ID: {account_id})")

        # If this is the first account, automatically set as current
        if len(self.accounts) == 1:
            self.current_account = account_id
            print(f"👉 Automatically set as current account")

        return account_id

    def _ensure_account_file(self, account_id):
    # Pandas not available, skip file creation
        return
# Calendar function disabled due to matplotlib dependency
def generate_monthly_calendar(self, year, month, account_id=None, save_path=None):
    print("Calendar function is currently disabled")
    return False
    def get_account_summary(self):
        """Get summary of all accounts"""
        if not self.accounts:
            print("📭 No accounts")
            return

        print("\n" + "=" * 70)
        print("🏦 All Accounts Summary".center(60))
        print("=" * 70)

        total_balance = 0
        total_initial = 0
        total_pnl_all = 0
        total_trades_all = 0

        for acc_id, acc in self.accounts.items():
            stats = self.get_account_stats(acc_id)
            total_balance += acc.current_balance
            total_initial += acc.initial_balance
            total_pnl_all += stats['total_pnl']
            total_trades_all += stats['total_trades']

            print(f"\n📌 {acc.name} [{acc_id}]")
            print(f"  Initial Balance: ${acc.initial_balance:,.2f}")
            print(f"  Current Balance: ${acc.current_balance:,.2f}")
            print(f"  Total P&L: ${stats['total_pnl']:+,.2f}")
            print(f"  Total Trades: {stats['total_trades']}")
            print(f"  Win Rate: {stats['win_rate']}")

        print("\n" + "-" * 70)
        print(f"📊 Totals:")
        print(f"  Total Initial Balance: ${total_initial:,.2f}")
        print(f"  Total Current Balance: ${total_balance:,.2f}")
        print(f"  Total P&L: ${total_pnl_all:+,.2f}")
        print(f"  Total Return: {((total_balance - total_initial) / total_initial * 100):.2f}%"
              if total_initial > 0 else "  Total Return: N/A")
        print(f"  Total Trades: {total_trades_all}")
        print("=" * 70)


# Interactive usage example
def interactive_demo():
    """Interactive demo"""
    analyzer = TradeAnalyzer()

    while True:
        print("\n" + "=" * 60)
        print("📊 Multi-Account Trade Analysis Tool".center(50))
        print("=" * 60)

        print("\n1. Account Management")
        print("2. Add Trade")
        print("3. View Trades")
        print("4. Delete Trades")
        print("5. Generate Chart")
        print("6. Account Summary")
        print("0. Exit")

        choice = input("\nSelect (0-6): ")

        if choice == '1':
            print("\n--- Account Management ---")
            print("1. Create New Account")
            print("2. Switch Current Account")
            print("3. List All Accounts")

            sub = input("Select (1-3): ")
            if sub == '1':
                name = input("Account Name: ")
                try:
                    balance = float(input("Initial Balance (default 0): ") or 0)
                except:
                    balance = 0
                currency = input("Currency (default USD): ") or "USD"
                notes = input("Notes: ")
                analyzer.create_account(name, balance, currency, notes)

            elif sub == '2':
                analyzer.list_accounts()
                acc_id = input("Enter Account ID: ")
                analyzer.switch_account(acc_id)

            elif sub == '3':
                analyzer.list_accounts()

        elif choice == '2':
            print("\n--- Add New Trade ---")
            try:
                pnl = float(input("P&L Amount (+profit/-loss): $"))
                symbol = input("Symbol (optional): ")
                direction = input("Direction (Long/Short, optional): ")
                fees = float(input("Fees (default 0): ") or 0)
                notes = input("Notes (optional): ")

                analyzer.add_trade(pnl, symbol, direction, fees, notes)
            except ValueError:
                print("❌ Please enter valid numbers")

        elif choice == '3':
            print("\n--- View Trade Records ---")
            analyzer.view_trades()

        elif choice == '4':
            print("\n--- Delete Trades ---")
            analyzer.interactive_delete_menu()

        elif choice == '5':
            print("\n--- Generate Chart ---")
            try:
                year = int(input("Year (e.g., 2026): "))
                month = int(input("Month (1-12): "))
                analyzer.generate_monthly_calendar(year, month)
            except ValueError:
                print("❌ Please enter valid numbers")

        elif choice == '6':
            analyzer.get_account_summary()

        elif choice == '0':
            print("👋 Goodbye!")
            break


if __name__ == "__main__":
    # Start interactive interface
    interactive_demo()

    def delete_account(self, account_id, confirm=True):
        """
        刪除整個帳戶（包括所有交易記錄）
        """
        if account_id not in self.accounts:
            print(f"❌ Account {account_id} not found")
            return False

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        # 確認刪除
        if confirm:
            print(f"\n⚠️  Delete account: {account.name} [{account_id}]")
            print(f"   Current balance: ${account.current_balance:,.2f}")
            print(f"   This will delete ALL trades in this account!")
            response = input("   Type 'YES' to confirm: ")
            if response != 'YES':
                print("❌ Deletion cancelled")
                return False

        # 刪除交易文件
        if os.path.exists(account_file):
            os.remove(account_file)

        # 從 accounts 字典中刪除
        del self.accounts[account_id]

        # 更新 accounts.json
        self.save_accounts()

        print(f"✅ Account {account.name} deleted successfully")

        # 如果刪除的是當前帳戶，清除 session
        return True
