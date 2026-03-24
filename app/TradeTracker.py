try:
    import pandas as pd
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
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("Warning: numpy not available")

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.font_manager import FontProperties
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available")
    plt = None
    mpatches = None
    FontProperties = None
from matplotlib.font_manager import FontProperties
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
        if not HAS_PANDAS:
            return
        """Ensure account's trade file exists"""
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")
        if not os.path.exists(account_file):
            # Create empty CSV file
            df = pd.DataFrame(columns=['id', 'date', 'symbol', 'direction', 'pnl', 'fees', 'net_pnl', 'notes'])
            df.to_csv(account_file, index=False)

    def switch_account(self, account_id):
        """Switch current account"""
        if account_id in self.accounts:
            self.current_account = account_id
            print(f"✅ Switched to account: {self.accounts[account_id].name}")
            return True
        else:
            print(f"❌ Account ID not found: {account_id}")
            return False

    def list_accounts(self, show_details=True):
        """List all accounts"""
        if not self.accounts:
            print("📭 No accounts")
            return None

        accounts_list = []
        for acc_id, acc in self.accounts.items():
            # Get account statistics
            stats = self.get_account_stats(acc_id)

            # Mark current account
            current_mark = "👉 " if acc_id == self.current_account else "   "

            accounts_list.append({
                '': current_mark,
                'ID': acc_id,
                'Account Name': acc.name,
                'Initial Balance': f"${acc.initial_balance:,.2f}",
                'Current Balance': f"${acc.current_balance:,.2f}",
                'Total P&L': f"${stats['total_pnl']:+,.2f}",
                'Trades': stats['total_trades'],
                'Win Rate': stats['win_rate'],
                'Currency': acc.currency,
            })

        df = pd.DataFrame(accounts_list)
        print("\n📋 Account List:")
        print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))

        return accounts_list

    def get_account_stats(self, account_id):
        """Get account statistics"""
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        if os.path.exists(account_file):
            try:
                df = pd.read_csv(account_file)
                if len(df) > 0:
                    total_pnl = df['net_pnl'].sum()
                    total_trades = len(df)
                    winning_trades = len(df[df['net_pnl'] > 0])
                    win_rate = f"{(winning_trades / total_trades * 100):.1f}%" if total_trades > 0 else "0%"

                    return {
                        'total_pnl': total_pnl,
                        'total_trades': total_trades,
                        'win_rate': win_rate
                    }
            except:
                pass

        return {
            'total_pnl': 0,
            'total_trades': 0,
            'win_rate': "0%"
        }

    def select_account_interactive(self, prompt="Please select an account", include_current=True):
        """
        Interactive account selection
        Let user select which account to use from a list
        """
        if not self.accounts:
            print("❌ No accounts available. Please create an account first")
            return None

        # Display all accounts
        print(f"\n{prompt}:")

        # Create options list
        options = []
        for i, (acc_id, acc) in enumerate(self.accounts.items(), 1):
            current_mark = " (current)" if acc_id == self.current_account else ""
            options.append((str(i), acc_id, f"{acc.name}{current_mark}"))
            print(f"  {i}. {acc.name}{current_mark} [{acc_id}]")

        # Add cancel option
        print(f"  0. Cancel")

        while True:
            choice = input("\nEnter number: ").strip()

            if choice == '0':
                print("❌ Operation cancelled")
                return None

            try:
                idx = int(choice)
                if 1 <= idx <= len(options):
                    selected_acc_id = options[idx - 1][1]
                    return selected_acc_id
                else:
                    print(f"❌ Please enter a number between 0-{len(options)}")
            except ValueError:
                print("❌ Please enter a valid number")



    def add_trade(self, pnl, symbol='', direction='', fees=0, notes='', account_id=None, tags='', emotion='', emotion_notes=''):
        """
        添加交易到指定帳戶
        tags: 策略標籤，多個標籤用空格或逗號分隔
        emotion: 交易時的情緒
        emotion_notes: 情緒備註
        """
        if account_id is None:
            account_id = self.select_account_interactive("Please select account")
            if account_id is None:
                return False

        if account_id not in self.accounts:
            print(f"❌ Account {account_id} not found")
            return False

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        if os.path.exists(account_file):
            df = pd.read_csv(account_file)
        else:
            df = pd.DataFrame(columns=['id', 'date', 'symbol', 'direction', 'pnl', 'fees', 'net_pnl', 'notes', 'tags', 'emotion', 'emotion_notes'])

        new_trade = {
            'id': len(df) + 1,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'symbol': symbol.upper() if symbol else 'MISC',
            'direction': direction,
            'pnl': float(pnl),
            'fees': float(fees),
            'net_pnl': float(pnl) - float(fees),
            'notes': notes,
            'tags': tags,
            'emotion': emotion,
            'emotion_notes': emotion_notes
        }

        df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
        df.to_csv(account_file, index=False)

        self.accounts[account_id].current_balance += new_trade['net_pnl']
        self.save_accounts()

        status = "profit" if new_trade['net_pnl'] > 0 else "loss" if new_trade['net_pnl'] < 0 else "breakeven"
        print(f"✅ [{account.name}] Trade added: {status} ${abs(new_trade['net_pnl']):,.2f}")
        if tags:
            print(f"   Tags: {tags}")
        if emotion:
            print(f"   Emotion: {emotion}")

        return True


    def add_trade_simple(self, pnl, symbol='', direction='', fees=0, notes=''):
        """
        Simplified version of add trade (uses current account or prompts user to select)
        """
        return self.add_trade(pnl, symbol, direction, fees, notes)

    # ============ New: Delete Trade Functions ============

    def delete_trade(self, trade_id, account_id=None, confirm=True):
        """
        Delete trade by ID
        """
        # If no account specified, let user select
        if account_id is None:
            account_id = self.select_account_interactive("Please select account to delete trade from")
            if account_id is None:
                return False

        if account_id not in self.accounts:
            print(f"❌ Account ID not found: {account_id}")
            return False

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        if not os.path.exists(account_file):
            print(f"📭 Account {account.name} has no trade records")
            return False

        # Load trade records
        df = pd.read_csv(account_file)

        if len(df) == 0:
            print(f"📭 Account {account.name} has no trade records")
            return False

        # Check if trade ID exists
        if trade_id not in df['id'].values:
            print(f"❌ Trade with ID {trade_id} not found")
            return False

        # Get trade to delete
        trade_to_delete = df[df['id'] == trade_id].iloc[0]

        # Confirm deletion
        if confirm:
            print(f"\n🔍 Found trade to delete:")
            print(f"  Date: {trade_to_delete['date']}")
            print(f"  Symbol: {trade_to_delete['symbol']}")
            print(f"  P&L: ${trade_to_delete['net_pnl']:+,.2f}")

            response = input(f"\n⚠️  Confirm deletion of this trade? (y/n): ").lower()
            if response != 'y':
                print("❌ Deletion cancelled")
                return False

        # Delete trade
        df = df[df['id'] != trade_id]

        # Reorder IDs
        df['id'] = range(1, len(df) + 1)

        # Save to file
        df.to_csv(account_file, index=False)

        # Update account balance (add back the deleted trade's P&L)
        self.accounts[account_id].current_balance -= trade_to_delete['net_pnl']
        self.save_accounts()

        print(f"✅ Deleted trade ID {trade_id} from account {account.name}")
        print(f"  Account balance updated: ${self.accounts[account_id].current_balance:+,.2f}")

        return True

    def delete_trades_batch(self, trade_ids, account_id=None, confirm=True):
        """
        Batch delete multiple trades
        """
        if account_id is None:
            account_id = self.select_account_interactive("Please select account to batch delete trades from")
            if account_id is None:
                return 0

        if account_id not in self.accounts:
            print(f"❌ Account ID not found: {account_id}")
            return 0

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        if not os.path.exists(account_file):
            print(f"📭 Account {account.name} has no trade records")
            return 0

        df = pd.read_csv(account_file)

        if len(df) == 0:
            print(f"📭 Account {account.name} has no trade records")
            return 0

        # Filter existing trade IDs
        valid_ids = [tid for tid in trade_ids if tid in df['id'].values]

        if not valid_ids:
            print("❌ No valid trade IDs found")
            return 0

        # Display trades to delete
        trades_to_delete = df[df['id'].isin(valid_ids)]
        print(f"\n🔍 Found {len(valid_ids)} trades to delete:")

        for _, trade in trades_to_delete.iterrows():
            print(f"  ID {int(trade['id'])}: {trade['date']} - {trade['symbol']} - ${trade['net_pnl']:+,.2f}")

        # Calculate total P&L impact
        total_pnl_impact = trades_to_delete['net_pnl'].sum()

        # Confirm deletion
        if confirm:
            response = input(f"\n⚠️  Confirm deletion of these {len(valid_ids)} trades? (y/n): ").lower()
            if response != 'y':
                print("❌ Deletion cancelled")
                return 0

        # Delete trades
        df = df[~df['id'].isin(valid_ids)]

        # Reorder IDs
        df['id'] = range(1, len(df) + 1)

        # Save to file
        df.to_csv(account_file, index=False)

        # Update account balance
        self.accounts[account_id].current_balance -= total_pnl_impact
        self.save_accounts()

        print(f"✅ Deleted {len(valid_ids)} trades from account {account.name}")
        print(f"  Account balance updated: ${self.accounts[account_id].current_balance:+,.2f}")
        print(f"  Total P&L impact: ${total_pnl_impact:+,.2f}")

        return len(valid_ids)

    def delete_trades_by_date_range(self, start_date, end_date, account_id=None, confirm=True):
        """
        Delete trades by date range
        """
        if account_id is None:
            account_id = self.select_account_interactive("Please select account to delete trades from")
            if account_id is None:
                return 0

        if account_id not in self.accounts:
            print(f"❌ Account ID not found: {account_id}")
            return 0

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        if not os.path.exists(account_file):
            print(f"📭 Account {account.name} has no trade records")
            return 0

        df = pd.read_csv(account_file)

        if len(df) == 0:
            print(f"📭 Account {account.name} has no trade records")
            return 0

        # Convert dates
        df['date_obj'] = pd.to_datetime(df['date'])
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        # Find trades within date range
        mask = (df['date_obj'] >= start) & (df['date_obj'] <= end)
        trades_to_delete = df[mask]

        if len(trades_to_delete) == 0:
            print(f"📭 No trades found between {start_date} and {end_date}")
            return 0

        print(f"\n🔍 Found {len(trades_to_delete)} trades within date range:")
        for _, trade in trades_to_delete.iterrows():
            print(f"  ID {int(trade['id'])}: {trade['date']} - {trade['symbol']} - ${trade['net_pnl']:+,.2f}")

        total_pnl_impact = trades_to_delete['net_pnl'].sum()

        if confirm:
            response = input(f"\n⚠️  Confirm deletion of these {len(trades_to_delete)} trades? (y/n): ").lower()
            if response != 'y':
                print("❌ Deletion cancelled")
                return 0

        # Delete trades
        df = df[~mask]

        # Reorder IDs
        df['id'] = range(1, len(df) + 1)
        df = df.drop('date_obj', axis=1)

        # Save to file
        df.to_csv(account_file, index=False)

        # Update account balance
        self.accounts[account_id].current_balance -= total_pnl_impact
        self.save_accounts()

        print(f"✅ Deleted {len(trades_to_delete)} trades from account {account.name}")
        print(f"  Account balance updated: ${self.accounts[account_id].current_balance:+,.2f}")

        return len(trades_to_delete)

    def delete_all_trades(self, account_id=None, confirm=True):
        """
        Delete all trades from an account
        """
        if account_id is None:
            account_id = self.select_account_interactive("Please select account to clear trades from")
            if account_id is None:
                return False

        if account_id not in self.accounts:
            print(f"❌ Account ID not found: {account_id}")
            return False

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        if not os.path.exists(account_file):
            print(f"📭 Account {account.name} has no trade records")
            return False

        df = pd.read_csv(account_file)

        if len(df) == 0:
            print(f"📭 Account {account.name} has no trade records")
            return False

        total_trades = len(df)
        total_pnl = df['net_pnl'].sum()

        print(f"\n⚠️  Warning: You are about to delete all {total_trades} trades from account {account.name}")
        print(f"  Total P&L impact: ${total_pnl:+,.2f}")

        if confirm:
            response = input(f"Confirm clearing all trades? (enter 'YES' to confirm): ")
            if response != 'YES':
                print("❌ Operation cancelled")
                return False

        # Create empty DataFrame
        empty_df = pd.DataFrame(columns=['id', 'date', 'symbol', 'direction', 'pnl', 'fees', 'net_pnl', 'notes'])
        empty_df.to_csv(account_file, index=False)

        # Reset account balance to initial value
        self.accounts[account_id].current_balance = self.accounts[account_id].initial_balance
        self.save_accounts()

        print(f"✅ Cleared all trades from account {account.name}")
        print(f"  Account balance reset to: ${self.accounts[account_id].current_balance:+,.2f}")

        return True

    def interactive_delete_menu(self):
        """
        Interactive delete menu
        """
        if not self.accounts:
            print("📭 No accounts")
            return

        print("\n" + "=" * 50)
        print("🗑️  Delete Trade Menu".center(40))
        print("=" * 50)
        print("1. Delete single trade by ID")
        print("2. Batch delete multiple trades")
        print("3. Delete by date range")
        print("4. Clear all trades from account")
        print("0. Back")

        choice = input("\nSelect (0-4): ")

        if choice == '1':
            # Select account first
            account_id = self.select_account_interactive("Please select account to delete trade from")
            if account_id:
                # Show recent trades for that account
                self.view_trades(account_id, limit=10)

                try:
                    trade_id = int(input("\nEnter trade ID to delete: "))
                    self.delete_trade(trade_id, account_id)
                except ValueError:
                    print("❌ Please enter a valid number")

        elif choice == '2':
            account_id = self.select_account_interactive("Please select account to batch delete trades from")
            if account_id:
                self.view_trades(account_id, limit=20)

                try:
                    trade_ids_input = input("\nEnter trade IDs to delete (comma-separated, e.g., 1,3,5): ")
                    trade_ids = [int(x.strip()) for x in trade_ids_input.split(',') if x.strip().isdigit()]

                    if trade_ids:
                        self.delete_trades_batch(trade_ids, account_id)
                    else:
                        print("❌ Please enter valid trade IDs")
                except ValueError:
                    print("❌ Please enter valid numbers")

        elif choice == '3':
            account_id = self.select_account_interactive("Please select account to delete trades from")
            if account_id:
                try:
                    start_date = input("Enter start date (YYYY-MM-DD): ")
                    end_date = input("Enter end date (YYYY-MM-DD): ")

                    self.delete_trades_by_date_range(start_date, end_date, account_id)
                except Exception as e:
                    print(f"❌ Date format error: {e}")

        elif choice == '4':
            account_id = self.select_account_interactive("Please select account to clear")
            if account_id:
                self.delete_all_trades(account_id)

    def view_trades(self, account_id=None, limit=20):
        """
        View trade records
        If no account specified, show current account or let user select
        """
        # If no account specified
        if account_id is None:
            if self.current_account:
                account_id = self.current_account
                print(f"📋 Using current account: {self.accounts[account_id].name}")
            else:
                account_id = self.select_account_interactive("Please select account to view")
                if account_id is None:
                    return

        if account_id not in self.accounts:
            print(f"❌ Account ID not found: {account_id}")
            return

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        if not os.path.exists(account_file):
            print(f"📭 Account {account.name} has no trade records")
            return

        df = pd.read_csv(account_file)

        if len(df) == 0:
            print(f"📭 Account {account.name} has no trade records")
            return

        print(f"\n📋 Account: {account.name} Trade Records (Total: {len(df)} trades, Showing recent {min(limit, len(df))}):")

        # Show recent trades
        recent = df.tail(limit)[['id', 'date', 'symbol', 'direction', 'pnl', 'fees', 'net_pnl', 'notes']].copy()

        # Format amounts
        recent['pnl'] = recent['pnl'].apply(lambda x: f"${x:+,.2f}")
        recent['fees'] = recent['fees'].apply(lambda x: f"${x:,.2f}")
        recent['net_pnl'] = recent['net_pnl'].apply(lambda x: f"${x:+,.2f}")

        print(tabulate(recent, headers='keys', tablefmt='grid', showindex=False))

        # Show statistics
        total_pnl = df['net_pnl'].sum()
        winning = len(df[df['net_pnl'] > 0])
        losing = len(df[df['net_pnl'] < 0])

        print(f"\n📊 Summary Statistics:")
        print(f"  Total Trades: {len(df)}")
        print(f"  Total P&L: ${total_pnl:+,.2f}")
        print(f"  Winning Trades: {winning} | Losing Trades: {losing}")
        print(f"  Win Rate: {(winning / len(df) * 100):.1f}%" if len(df) > 0 else "  Win Rate: 0%")
        print(f"  Account Balance: ${account.current_balance:+,.2f}")

    def generate_monthly_calendar(self, year, month, account_id=None, save_path=None):
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available, calendar disabled")
        return False
        """
        Generate monthly trading calendar (specify account)
        """
        # If no account specified
        if account_id is None:
            if self.current_account:
                account_id = self.current_account
                print(f"📊 Using current account: {self.accounts[account_id].name}")
            else:
                account_id = self.select_account_interactive("Please select account to generate chart for")
                if account_id is None:
                    return

        if account_id not in self.accounts:
            print(f"❌ Account ID not found: {account_id}")
            return

        account = self.accounts[account_id]
        account_file = os.path.join(self.data_dir, f"{account_id}_trades.csv")

        # Load trade records
        if not os.path.exists(account_file):
            print(f"📭 Account {account.name} has no trade records")
            return

        df = pd.read_csv(account_file)

        # Get month name
        month_name = calendar.month_name[month]

        # Get first weekday of the month
        first_weekday = calendar.weekday(year, month, 1)

        # Get days in month
        _, days_in_month = calendar.monthrange(year, month)

        # Prepare daily data
        daily_data = {}
        for day in range(1, days_in_month + 1):
            daily_data[day] = {
                'pnl': 0.0,
                'trade_count': 0,
                'trades': []
            }

        # Aggregate daily trades
        for _, trade in df.iterrows():
            try:
                trade_date = datetime.strptime(trade['date'], '%Y-%m-%d %H:%M')
                if trade_date.year == year and trade_date.month == month:
                    day = trade_date.day
                    daily_data[day]['pnl'] += trade['net_pnl']
                    daily_data[day]['trade_count'] += 1
                    daily_data[day]['trades'].append(trade)
            except:
                continue

        # Create chart
        fig, ax = plt.subplots(figsize=(16, 10))
        ax.set_xlim(0, 8)
        ax.set_ylim(0, 7)
        ax.set_aspect('equal')

        # Hide axes
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

        # Set title (including account name)
        ax.set_title(f'{account.name} - {month_name} {year}', fontsize=20, fontweight='bold', pad=20)

        # Weekday headers
        weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day in enumerate(weekdays):
            ax.text(i + 0.5, 6.5, day, ha='center', va='center',
                    fontsize=12, fontweight='bold', color='#2c3e50')

        # Draw date grids
        day_counter = 1
        for week in range(6):
            for weekday in range(7):
                x = weekday + 0.5
                y = 6 - (week + 1)

                current_day = None
                if week == 0 and weekday >= first_weekday:
                    current_day = day_counter
                    day_counter += 1
                elif week > 0 and day_counter <= days_in_month:
                    current_day = day_counter
                    day_counter += 1

                # Draw grid border
                rect = plt.Rectangle((weekday, y), 1, 1, fill=False, edgecolor='#bdc3c7', linewidth=1)
                ax.add_patch(rect)

                if current_day and current_day <= days_in_month:
                    data = daily_data.get(current_day, {'pnl': 0, 'trade_count': 0})
                    pnl = data['pnl']
                    trade_count = data['trade_count']

                    # Set background color
                    if pnl > 0:
                        color = '#d4edda'
                        alpha = min(0.3 + (pnl / 1000) * 0.5, 0.9)
                    elif pnl < 0:
                        color = '#f8d7da'
                        alpha = min(0.3 + (abs(pnl) / 1000) * 0.5, 0.9)
                    else:
                        color = '#ffffff'
                        alpha = 0.3

                    rect_fill = plt.Rectangle((weekday, y), 1, 1, facecolor=color, alpha=alpha)
                    ax.add_patch(rect_fill)

                    # Display date
                    ax.text(x, y + 0.75, str(current_day), ha='center', va='center',
                            fontsize=10, fontweight='bold', color='#2c3e50')

                    # Display P&L
                    if pnl != 0 or trade_count > 0:
                        pnl_text = f"${pnl:+,.2f}" if abs(pnl) >= 0.01 else "$0.00"
                        ax.text(x, y + 0.45, pnl_text, ha='center', va='center',
                                fontsize=9, color='#2c3e50' if pnl >= 0 else '#c0392b',
                                fontweight='bold' if pnl != 0 else 'normal')

                        if trade_count > 0:
                            trade_text = f"{trade_count} trade{'s' if trade_count > 1 else ''}"
                            ax.text(x, y + 0.15, trade_text, ha='center', va='center',
                                    fontsize=8, color='#7f8c8d')

        # Statistics box
        month_pnl = sum(data['pnl'] for data in daily_data.values())
        month_trades = sum(data['trade_count'] for data in daily_data.values())
        trading_days = sum(1 for data in daily_data.values() if data['trade_count'] > 0)
        winning_days = sum(1 for data in daily_data.values() if data['pnl'] > 0)
        losing_days = sum(1 for data in daily_data.values() if data['pnl'] < 0)

        avg_trade_pnl = month_pnl / month_trades if month_trades > 0 else 0
        win_rate = (winning_days / trading_days * 100) if trading_days > 0 else 0

        # Draw statistics box
        stats_x_start = 7.1
        stats_x_end = 7.9
        stats_y_start = 6
        stats_y_end = 0.5

        stats_rect = plt.Rectangle((stats_x_start, stats_y_end),
                                   stats_x_end - stats_x_start,
                                   stats_y_start - stats_y_end,
                                   facecolor='#f8f9fa',
                                   edgecolor='#dee2e6',
                                   linewidth=1.5,
                                   alpha=0.8)
        ax.add_patch(stats_rect)

        # Statistics box title
        ax.text((stats_x_start + stats_x_end) / 2, stats_y_start - 0.2,
                f'📊 {account.name}',
                ha='center', va='center',
                fontsize=14, fontweight='bold',
                color='#2c3e50')

        ax.text((stats_x_start + stats_x_end) / 2, stats_y_start - 0.4,
                'Monthly Statistics',
                ha='center', va='center',
                fontsize=12, fontweight='bold',
                color='#34495e')

        # Statistics content
        stats_lines = [
            ('Total P&L:', f'${month_pnl:+,.2f}', '#27ae60' if month_pnl >= 0 else '#c0392b'),
            ('Account Balance:', f'${account.current_balance:+,.2f}', '#2980b9'),
            ('Trading Days:', f'{trading_days} days', '#2c3e50'),
            ('Total Trades:', f'{month_trades}', '#2c3e50'),
            ('Winning Days:', f'{winning_days} days', '#27ae60'),
            ('Losing Days:', f'{losing_days} days', '#c0392b'),
            ('Win Rate:', f'{win_rate:.1f}%', '#2c3e50'),
            ('Avg P&L/Trade:', f'${avg_trade_pnl:+,.2f}', '#27ae60' if avg_trade_pnl >= 0 else '#c0392b'),
        ]

        y_pos = stats_y_start - 0.6
        for label, value, color in stats_lines:
            ax.text(stats_x_start + 0.15, y_pos, label,
                    ha='left', va='center',
                    fontsize=9, fontweight='bold',
                    color='#34495e')
            ax.text(stats_x_end - 0.15, y_pos, value,
                    ha='right', va='center',
                    fontsize=9, fontweight='bold',
                    color=color)
            y_pos -= 0.3

        # Legend
        legend_x = stats_x_start
        legend_y = y_pos - 0.2

        legend_elements = [
            mpatches.Patch(facecolor='#d4edda', alpha=0.6, label='Profit'),
            mpatches.Patch(facecolor='#f8d7da', alpha=0.6, label='Loss'),
            mpatches.Patch(facecolor='#ffffff', alpha=0.6, label='Breakeven')
        ]

        ax.legend(handles=legend_elements,
                  loc='upper left',
                  bbox_to_anchor=(stats_x_start, legend_y),
                  fontsize=8,
                  framealpha=0.9)

        plt.tight_layout()

        # Save or display
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Saved to: {save_path}")
        else:
            plt.show()

        plt.close()

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
