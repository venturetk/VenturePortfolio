import json
from datetime import datetime
#version = 0.0.2

class Asset:
    def __init__(self, name, market_value):
        self.name = name
        self.market_value = market_value

    def __str__(self):
        return f"Asset(name={self.name}, market_value={self.market_value})"

class Position:
    def __init__(self, asset: Asset, quantity, date_acquired, cost_basis):
        self.asset = asset
        self.quantity = quantity
        self.date_acquired = date_acquired
        self.cost_basis = cost_basis
        self.spot_price = asset.market_value

    @property
    def total_market_value(self):
        return self.quantity * self.spot_price

    def cost_basis_per_unit(self):
        if self.quantity > 0:
            return self.cost_basis / self.quantity
        else:
            return 0  # Return 0 or appropriate value when quantity is zero to avoid division by zero error

    def __str__(self):
        return (f"Position(asset={self.asset.name}, quantity={self.quantity}, date_acquired={self.date_acquired}, " +
                f"cost_basis={self.cost_basis}, cost_basis_per_unit={self.cost_basis_per_unit()}, " +
                f"total_market_value={self.total_market_value})")


class Wallet:
    def __init__(self, name):
        self.name = name
        self.positions = []

    def add_position(self, position):
        self.positions.append(position)

    def remove_position(self, position):
        self.positions.remove(position)

class Transaction:
    def __init__(self, date, time, transaction_type, fee_quantity, fee_asset: Asset, classification,
                 fee_spot_price=None, received_quantity=None, received_asset: Asset = None, received_spot_price=None,
                 sent_quantity=None, sent_asset: Asset = None, sent_spot_price=None,
                 origin_wallet: Wallet = None, destination_wallet: Wallet = None):
        self.date = date
        self.time = time
        self.transaction_type = transaction_type
        self.fee_quantity = fee_quantity
        self.fee_asset = fee_asset
        if fee_asset is not None:
            self.fee_spot_price = fee_spot_price if fee_spot_price is not None else self.fetch_market_price(fee_asset)
            self.fee_total_value = self.fee_quantity * self.fee_spot_price
        else:
            self.fee_spot_price = 0
            self.fee_total_value = 0
        self.classification = classification
        self.received_quantity = received_quantity
        self.received_asset = received_asset
        self.received_spot_price = received_spot_price if received_spot_price is not None else (self.fetch_market_price(received_asset) if received_asset else None)
        self.received_total_value = self.received_quantity * self.received_spot_price if self.received_quantity and self.received_spot_price else 0
        self.sent_quantity = sent_quantity
        self.sent_asset = sent_asset
        self.sent_spot_price = sent_spot_price if sent_spot_price is not None else (self.fetch_market_price(sent_asset) if sent_asset else None)
        self.sent_total_value = self.sent_quantity * self.sent_spot_price if self.sent_quantity and self.sent_spot_price else 0
        self.origin_wallet = origin_wallet
        self.destination_wallet = destination_wallet
        if self.fee_quantity > 0:
            fee_entry = FeeEntry(self.date, self.time, self.fee_asset, self.fee_quantity, self.fee_spot_price)
            portfolio.fee_ledger.add_fee_entry(fee_entry)
        self.gainloss = 0  # Initialize gain/loss to zero

    def fetch_market_price(self, asset: Asset):
        # Placeholder for market price fetching logic
        return asset.market_value  # Temporary return, replace with actual market price fetching logic

    def process_transaction(self, portfolio):
        if self.transaction_type == 'Deposit':
            self.process_deposit(portfolio)
        if self.transaction_type == 'Withdraw':
            self.process_withdraw(portfolio)
        if self.transaction_type == 'Order':
            self.process_order(portfolio)
		# Calculate realized gain/loss
        self.calculate_realized_gain_loss()
		# If there is a realized gain, create a GainLossEntry and add it to the gain-loss ledger
        if self.gainloss > 0:
            gain_loss_entry = GainLossEntry(self.date, self.time, self.gainloss)
            portfolio.gain_loss_ledger.add_entry(gain_loss_entry)
	
    def process_order(self, portfolio):
        wallet = next((w for w in portfolio.wallets if w.name == self.origin_wallet.name), None)
        if not wallet:
            print("Wallet not found.")
            return

        sent_position = next((pos for pos in wallet.positions if pos.asset.name == self.sent_asset.name), None)
        if sent_position and sent_position.quantity >= self.sent_quantity:
            cost_basis_reduction = self.sent_quantity * sent_position.cost_basis_per_unit()
            sent_position.quantity -= self.sent_quantity
            sent_position.cost_basis -= cost_basis_reduction

            # Calculate gain or loss
            market_value_of_sent_quantity = self.sent_quantity * self.sent_spot_price
            gain_loss = market_value_of_sent_quantity - cost_basis_reduction

            # Create GainLossEntry if there's a gain or loss
            if gain_loss != 0:
                gain_loss_entry = GainLossEntry(self.date, self.time, gain_loss)
                portfolio.gain_loss_ledger.add_entry(gain_loss_entry)

            if sent_position.quantity == 0:
                wallet.remove_position(sent_position)
        else:
            print("Not enough asset in the position to cover the order.")
            return

        # Handling the received asset
        received_position = next((pos for pos in wallet.positions if pos.asset.name == self.received_asset.name), None)
        if received_position:
            received_position.quantity += self.received_quantity
            received_position.cost_basis += self.received_quantity * self.received_spot_price
        else:
            # Create a new position for the received asset
            new_position = Position(
                asset=self.received_asset,
                quantity=self.received_quantity,
                date_acquired=f"{self.date} {self.time}",
                cost_basis=self.received_quantity * self.received_spot_price
            )
            wallet.add_position(new_position)

        print(f"Order transaction processed in wallet '{wallet.name}'.")

    def process_withdraw(self, portfolio):
        origin_wallet = next((wallet for wallet in portfolio.wallets if wallet.name == self.origin_wallet.name), None)
        if origin_wallet is None:
            print("Origin wallet not found.")
            return

        # Find the position with the sent_asset
        position = next((pos for pos in origin_wallet.positions if pos.asset.name == self.sent_asset.name), None)
        if position is None or position.quantity < self.sent_quantity:
            print("Not enough asset in the position to cover the withdrawal.")
            return

        # Adjust the position
        if position.quantity == self.sent_quantity:
            origin_wallet.remove_position(position)
        else:
            position.quantity -= self.sent_quantity
            position.cost_basis -= self.sent_quantity * position.spot_price  # Adjust cost basis proportionally

        print(f"Withdrawal processed for {self.sent_quantity} {self.sent_asset.name} from {origin_wallet.name}.")

    def process_deposit(self, portfolio):
        # Find the destination wallet in the portfolio
        destination_wallet = next((wallet for wallet in portfolio.wallets if wallet.name == self.destination_wallet.name), None)
        if destination_wallet is None:
            return  # Wallet not found, or other error handling

        # Add position to the wallet
        position = Position(
            asset=self.received_asset,
            quantity=self.received_quantity,
            date_acquired=f"{self.date} {self.time}",
            cost_basis=self.received_total_value
        )
        destination_wallet.add_position(position)

    def calculate_realized_gain_loss(self):
        # Placeholder for gain/loss calculation logic
        # This function should update self.gainloss with the calculated value
        pass
		
    def __str__(self):
        origin_wallet_name = self.origin_wallet.name if self.origin_wallet else "N/A"
        destination_wallet_name = self.destination_wallet.name if self.destination_wallet else "N/A"
        return (f"Transaction({self.date}, {self.time}, {self.transaction_type}, " +
                f"Fee: {self.fee_quantity} {self.fee_asset.name} @ {self.fee_spot_price} Total: {self.fee_total_value}, " +
                f"Received: {self.received_quantity} {self.received_asset.name if self.received_asset else 'N/A'} @ {self.received_spot_price} Total: {self.received_total_value}, " +
                f"Sent: {self.sent_quantity} {self.sent_asset.name if self.sent_asset else 'N/A'} @ {self.sent_spot_price} Total: {self.sent_total_value}, " +
                f"Origin Wallet: {origin_wallet_name}, Destination Wallet: {destination_wallet_name})")

class Ledger:
    def __init__(self, portfolio):
        self.transactions = []
        self.portfolio = portfolio

    def add_transaction(self, transaction):
        self.transactions.append(transaction)
        self.transactions.sort(key=lambda x: x.date)
        self.portfolio.update_wallet_positions()

    def remove_transaction(self, transaction):
        self.transactions.remove(transaction)
        self.portfolio.update_wallet_positions()

class Portfolio:
    def __init__(self, name):
        self.name = name
        self.assets = [Asset("USD", 1.0)]
        self.ledger = Ledger(self)
        self.wallets = []
        self.fee_ledger = FeeLedger()  # Fee ledger for tracking fees
        self.gain_loss_ledger = GainLossLedger()  # Gain/Loss ledger for tracking gains and losses

    def add_asset(self, asset):
        self.assets.append(asset)

    def remove_asset(self, asset):
        self.assets.remove(asset)

    def add_wallet(self, wallet):
        self.wallets.append(wallet)

    def update_wallet_positions(self):
        # Clear current positions in each wallet
        for wallet in self.wallets:
            wallet.positions.clear()

        # Re-process each transaction in chronological order
        for transaction in self.ledger.transactions:
            transaction.process_transaction(self)

class FeeEntry:
    def __init__(self, date, time, fee_asset, fee_quantity, fee_spot_price):
        self.date = date
        self.time = time
        self.fee_asset = fee_asset
        self.fee_quantity = fee_quantity
        self.fee_spot_price = fee_spot_price
        self.fee_total_value = self.fee_quantity * self.fee_spot_price

    def __str__(self):
        return (f"FeeEntry(Date: {self.date}, Time: {self.time}, Asset: {self.fee_asset.name}, " +
                f"Quantity: {self.fee_quantity}, Spot Price: {self.fee_spot_price}, " +
                f"Total Value: {self.fee_total_value})")

class FeeLedger:
    def __init__(self):
        self.fees = []

    def add_fee_entry(self, fee_entry):
        self.fees.append(fee_entry)
        self.fees.sort(key=lambda x: (x.date, x.time))

    def remove_fee_entry(self, fee_entry):
        if fee_entry in self.fees:
            self.fees.remove(fee_entry)
            self.fees.sort(key=lambda x: (x.date, x.time))

    def view_all_fees(self):
        for fee in self.fees:
            print(fee)
			
class GainLossEntry:
    def __init__(self, date, time, gain_amount):
        self.date = date
        self.time = time
        self.gain_amount = gain_amount

    def __str__(self):
        return (f"GainLossEntry(Date: {self.date}, Time: {self.time}, Gain/Loss Amount: {self.gain_amount})")
		
class GainLossLedger:
    def __init__(self):
        self.entries = []

    def add_entry(self, entry):
        self.entries.append(entry)
        self.entries.sort(key=lambda x: (x.date, x.time))

    def remove_entry(self, entry):
        if entry in self.entries:
            self.entries.remove(entry)
            self.entries.sort(key=lambda x: (x.date, x.time))

    def view_all_entries(self):
        for entry in self.entries:
            print(entry)

def save_portfolio_to_file(portfolio, filename):
    # Convert the portfolio object to a JSON string and save it to a file
    pass

def load_portfolio_from_file(filename):
    # Load a JSON string from a file and convert it to a Portfolio object
    pass

def transactions_menu(portfolio):
    while True:
        print("\nTransactions Menu:")
        print("1. Add a transaction")
        print("2. Remove a transaction")
        print("3. View transactions")
        print("4. Edit a transaction")
        print("5. Return to main menu")

        choice = input("Enter your choice: ")

        if choice == "1":
            add_transaction_to_ledger(portfolio)
        elif choice == "2":
            remove_transaction_from_ledger(portfolio)
        elif choice == "3":
            view_transactions_in_ledger(portfolio)
        elif choice == "4":
            edit_transaction_in_ledger(portfolio)
        elif choice == "5":
            break
        else:
            print("Invalid choice, please try again.")

def add_transaction_to_ledger(portfolio):
    print("\nTransaction Types:")
    print("1. Deposit")
    print("2. Withdraw")
    print("3. Order")
    print("4. Internal")

    transaction_type = input("Enter the type of transaction: ")

    if transaction_type == "1":
        add_deposit_transaction(portfolio)
    elif transaction_type == "2":
        add_withdraw_transaction(portfolio)
    elif transaction_type == "3":
        add_order_transaction(portfolio)
    elif transaction_type == "4":
        add_internal_transaction(portfolio)
    else:
        print("Invalid transaction type, please try again.")

def add_deposit_transaction(portfolio):
    print("\nAdding a Deposit Transaction")

    # Handling date and time with defaults
    date = input("Enter the date (YYYY-MM-DD), leave blank for today: ").strip()
    time = input("Enter the time (HH:MM), leave blank for now: ").strip()

    date = date if date else datetime.now().strftime("%Y-%m-%d")
    time = time if time else datetime.now().strftime("%H:%M")

    fee_quantity = float(input("Enter the fee quantity, 0 for no fee: "))

    fee_asset = None
    if fee_quantity > 0:
        fee_asset = choose_asset_from_portfolio(portfolio)
        if not fee_asset:
            return

    classification = input("Enter the classification: ")
    received_quantity = float(input("Enter the received quantity: "))

    received_asset = choose_asset_from_portfolio(portfolio)
    if not received_asset:
        return

    # Automatically set spot price for USD, else ask user
    if received_asset.name == "USD":
        received_spot_price = 1.0
    else:
        received_spot_price = float(input("Enter the received asset spot price: "))
    destination_wallet = choose_wallet_from_portfolio(portfolio)
    if not destination_wallet:
        return

    deposit_transaction = Transaction(
        date=date, time=time, transaction_type='Deposit',
        fee_quantity=fee_quantity, fee_asset=fee_asset, classification=classification,
        received_quantity=received_quantity, received_asset=received_asset,
        received_spot_price=received_spot_price, destination_wallet=destination_wallet
    )

    portfolio.ledger.add_transaction(deposit_transaction)
    print("Deposit transaction added successfully.")

def add_withdraw_transaction(portfolio):
    print("\nAdding a Withdraw Transaction")

    # Handling date and time with defaults
    date = input("Enter the date (YYYY-MM-DD), leave blank for today: ").strip()
    time = input("Enter the time (HH:MM), leave blank for now: ").strip()

    date = date if date else datetime.now().strftime("%Y-%m-%d")
    time = time if time else datetime.now().strftime("%H:%M")

    fee_quantity = float(input("Enter the fee quantity, 0 for no fee: "))

    fee_asset = None
    if fee_quantity > 0:
        fee_asset = choose_asset_from_portfolio(portfolio)
        if not fee_asset:
            return

    classification = input("Enter the classification: ")
    sent_quantity = float(input("Enter the sent quantity: "))

    sent_asset = choose_asset_from_portfolio(portfolio)
    if not sent_asset:
        return

    # Automatically set spot price for USD, else ask user
    if sent_asset.name == "USD":
        sent_spot_price = 1.0
    else:
        sent_spot_price = float(input("Enter the sent asset spot price: "))
    origin_wallet = choose_wallet_from_portfolio(portfolio)
    if not origin_wallet:
        return

    withdraw_transaction = Transaction(
        date=date, time=time, transaction_type='Withdraw',
        fee_quantity=fee_quantity, fee_asset=fee_asset, classification=classification,
        sent_quantity=sent_quantity, sent_asset=sent_asset, sent_spot_price=sent_spot_price,
        origin_wallet=origin_wallet
    )

    portfolio.ledger.add_transaction(withdraw_transaction)
    print("Withdraw transaction added successfully.")
	
def add_order_transaction(portfolio):
    print("\nAdding an Order Transaction")

    # Handling date and time with defaults
    date = input("Enter the date (YYYY-MM-DD), leave blank for today: ").strip()
    time = input("Enter the time (HH:MM), leave blank for now: ").strip()

    date = date if date else datetime.now().strftime("%Y-%m-%d")
    time = time if time else datetime.now().strftime("%H:%M")

    fee_quantity = float(input("Enter the fee quantity, 0 for no fee: "))

    fee_asset = None
    if fee_quantity > 0:
        fee_asset = choose_asset_from_portfolio(portfolio)
        if not fee_asset:
            return

    classification = input("Enter the classification: ")

    # Details for the sent (sold) part of the order
    sent_quantity = float(input("Enter the sent (sold) quantity: "))
    sent_asset = choose_asset_from_portfolio(portfolio)
    if not sent_asset:
        return

    # Automatically set spot price for USD, else ask user
    if sent_asset.name == "USD":
        sent_spot_price = 1.0
    else:
        sent_spot_price = float(input("Enter the sent asset spot price: "))

    # Details for the received (bought) part of the order
    received_quantity = float(input("Enter the received (bought) quantity: "))
    received_asset = choose_asset_from_portfolio(portfolio)
    if not received_asset:
        return

    # Automatically set spot price for USD, else ask user
    if received_asset.name == "USD":
        received_spot_price = 1.0
    else:
        received_spot_price = float(input("Enter the received asset spot price: "))

    # Choosing the wallet
    wallet = choose_wallet_from_portfolio(portfolio)
    if not wallet:
        return

    order_transaction = Transaction(
        date=date, time=time, transaction_type='Order',
        fee_quantity=fee_quantity, fee_asset=fee_asset, classification=classification,
        sent_quantity=sent_quantity, sent_asset=sent_asset, sent_spot_price=sent_spot_price,
        received_quantity=received_quantity, received_asset=received_asset, received_spot_price=received_spot_price,
        origin_wallet=wallet, destination_wallet=wallet
    )

    portfolio.ledger.add_transaction(order_transaction)
    print("Order transaction added successfully.")


def add_internal_transaction(portfolio):
    print("\nAdding an Internal Transaction")

    # Handling date and time with defaults
    date = input("Enter the date (YYYY-MM-DD), leave blank for today: ").strip()
    time = input("Enter the time (HH:MM), leave blank for now: ").strip()

    date = date if date else datetime.now().strftime("%Y-%m-%d")
    time = time if time else datetime.now().strftime("%H:%M")

    # Choosing the origin wallet
    print("Choose the origin wallet:")
    origin_wallet = choose_wallet_from_portfolio(portfolio)
    if not origin_wallet:
        return

    # Choosing the destination wallet
    print("Choose the destination wallet:")
    destination_wallet = choose_wallet_from_portfolio(portfolio)
    if not destination_wallet:
        return

    # Gathering details about the asset being transferred
    sent_quantity = float(input("Enter the quantity of the asset to transfer: "))
    sent_asset = choose_asset_from_portfolio(portfolio)
    if not sent_asset:
        return

    # Handling fee
    fee_quantity = float(input("Enter the fee quantity, 0 for no fee: "))
    fee_asset = None
    if fee_quantity > 0:
        fee_asset = choose_asset_from_portfolio(portfolio)
        if not fee_asset:
            return

    classification = input("Enter the classification: ")

    # Creating the transaction
    internal_transaction = Transaction(
        date=date, time=time, transaction_type='Internal',
        fee_quantity=fee_quantity, fee_asset=fee_asset, classification=classification,
        sent_quantity=sent_quantity, sent_asset=sent_asset,
        origin_wallet=origin_wallet, destination_wallet=destination_wallet
    )

    portfolio.ledger.add_transaction(internal_transaction)
    print("Internal transaction added successfully.")

def remove_transaction_from_ledger(portfolio):
    # Logic to remove a transaction
    pass

def view_transactions_in_ledger(portfolio):
    # Logic to view transactions
    pass

def edit_transaction_in_ledger(portfolio):
    # Logic to edit a transaction
    pass

def main_menu():
    portfolio = None

    while True:
        print("\nMain Menu:")
        print("1. Portfolio")
        print("2. Assets")
        print("3. Wallets")
        print("4. Transactions")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            portfolio = portfolio_menu(portfolio)
            if portfolio:
                print(f"Portfolio '{portfolio.name}' is loaded.")
        elif choice == "2":
            if portfolio:
                assets_menu(portfolio)
            else:
                print("Please load or create a portfolio first.")
        elif choice == "3":
            if portfolio:
                wallets_menu(portfolio)
            else:
                print("Please load or create a portfolio first.")
        elif choice == "4":
            if portfolio:
                transactions_menu(portfolio)
            else:
                print("Please load or create a portfolio first.")
        elif choice == "5":
            print("Exiting program.")
            break
        else:
            print("Invalid choice, please try again.")

def portfolio_menu(portfolio):
    while True:
        print("\nPortfolio Menu:")
        print("1. Create a new portfolio")
        print("2. Save portfolio to file")
        print("3. Load portfolio from file")
        print("4. Return to main menu")

        choice = input("Enter your choice: ")

        if choice == "1":
            portfolio = create_new_portfolio()
        elif choice == "2":
            # Save logic will go here
            pass
        elif choice == "3":
            # Load logic will go here
            pass
        elif choice == "4":
            break  # Exit the portfolio menu loop to return to the main menu
        else:
            print("Invalid choice, please try again.")

    return portfolio

def create_new_portfolio():
    name = input("Enter the name for the new portfolio: ")
    return Portfolio(name)

def assets_menu(portfolio):
    while True:
        print("\nAssets Menu:")
        print("1. Add an asset")
        print("2. Remove an asset")
        print("3. View assets")
        print("4. Update market prices")
        print("5. Return to main menu")

        choice = input("Enter your choice: ")

        if choice == "1":
            add_asset_to_portfolio(portfolio)
        elif choice == "2":
            remove_asset_from_portfolio(portfolio)
        elif choice == "3":
            view_assets_in_portfolio(portfolio)
        elif choice == "4":
            update_market_prices(portfolio)
        elif choice == "5":
            break
        else:
            print("Invalid choice, please try again.")

def add_asset_to_portfolio(portfolio):
    name = input("Enter the asset name: ")
    try:
        market_value = float(input("Enter the market value: "))
        asset = Asset(name, market_value)
        portfolio.add_asset(asset)
        print(f"Asset '{name}' added.")
    except ValueError:
        print("Invalid market value. Please enter a number.")

def remove_asset_from_portfolio(portfolio):
    asset = choose_asset_from_portfolio(portfolio)
    if not asset or asset.name == "USD":
        print("Invalid selection or USD asset cannot be removed.")
        return

    portfolio.remove_asset(asset)
    print(f"Asset '{asset.name}' removed.")

def view_assets_in_portfolio(portfolio):
    if portfolio.assets:
        print("\nAssets in Portfolio:")
        for asset in portfolio.assets:
            print(f"Name: {asset.name}, Market Value: {asset.market_value}")
    else:
        print("No assets in the portfolio.")

def update_market_prices(portfolio):
    asset = choose_asset_from_portfolio(portfolio)
    if not asset or asset.name == "USD":
        print("Invalid selection or market value of USD cannot be changed.")
        return

    try:
        new_price = float(input(f"Enter the new market value for {asset.name}: "))
        asset.market_value = new_price
        print(f"Market value for {asset.name} updated to {new_price}.")
    except ValueError:
        print("Invalid market value. Please enter a number.")

#need to add an option to view a wallets positions in detail
def wallets_menu(portfolio):
    while True:
        print("\nWallets Menu:")
        print("1. Add a wallet")
        print("2. Remove a wallet")
        print("3. View wallets")
        print("4. View detailed positions of a wallet")
        print("5. Return to main menu")

        choice = input("Enter your choice: ")

        if choice == "1":
            add_wallet_to_portfolio(portfolio)
        elif choice == "2":
            remove_wallet_from_portfolio(portfolio)
        elif choice == "3":
            view_wallets_in_portfolio(portfolio)
        elif choice == "4":
            view_wallet_positions(portfolio)
        elif choice == "5":
            break
        else:
            print("Invalid choice, please try again.")

def view_wallet_positions(portfolio):
    selected_wallet = choose_wallet_from_portfolio(portfolio)
    if not selected_wallet:
        print("No wallet selected or available.")
        return

    # Display positions in the selected wallet
    if not selected_wallet.positions:
        print(f"No positions in wallet '{selected_wallet.name}'.")
        return

    print(f"\nPositions in wallet '{selected_wallet.name}':")
    for position in selected_wallet.positions:
        print(f"Asset: {position.asset.name}, Quantity: {position.quantity}, "
              f"Date Acquired: {position.date_acquired}, Cost Basis: {position.cost_basis}, "
              f"Total Market Value: {position.total_market_value}")

def add_wallet_to_portfolio(portfolio):
    name = input("Enter a name for the new wallet: ")

    # Check if a wallet with the same name already exists
    existing_wallet = next((wallet for wallet in portfolio.wallets if wallet.name == name), None)
    if existing_wallet:
        print(f"A wallet with the name '{name}' already exists.")
        return

    wallet = Wallet(name)
    portfolio.add_wallet(wallet)
    print(f"Wallet '{name}' added to the portfolio.")

def remove_wallet_from_portfolio(portfolio):
    selected_wallet = choose_wallet_from_portfolio(portfolio)
    if not selected_wallet:
        print("No wallet selected or available.")
        return

    # Proceed with wallet removal
    portfolio.wallets.remove(selected_wallet)
    print(f"Wallet '{selected_wallet.name}' has been removed from the portfolio.")

def view_wallets_in_portfolio(portfolio):
    if portfolio.wallets:
        print("\nWallets in Portfolio:")
        for wallet in portfolio.wallets:
            print(f"Name: {wallet.name}, Positions: {len(wallet.positions)}")
    else:
        print("No wallets in the portfolio.")

def choose_asset_from_portfolio(portfolio):
    if not portfolio.assets:
        print("No assets available.")
        return None

    print("\nAvailable Assets:")
    for i, asset in enumerate(portfolio.assets, 1):
        print(f"{i}. {asset.name}")

    choice = input("Select an asset (number): ")
    try:
        choice = int(choice) - 1
        if 0 <= choice < len(portfolio.assets):
            return portfolio.assets[choice]
        else:
            print("Invalid selection.")
            return None
    except ValueError:
        print("Please enter a number.")
        return None

def choose_wallet_from_portfolio(portfolio):
    if not portfolio.wallets:
        print("No wallets available.")
        return None

    print("\nAvailable Wallets:")
    for i, wallet in enumerate(portfolio.wallets, 1):
        print(f"{i}. {wallet.name}")

    choice = input("Select a wallet (number): ")
    try:
        choice = int(choice) - 1
        if 0 <= choice < len(portfolio.wallets):
            return portfolio.wallets[choice]
        else:
            print("Invalid selection.")
            return None
    except ValueError:
        print("Please enter a number.")
        return None

if __name__ == "__main__":
    main_menu()