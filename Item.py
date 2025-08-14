# Item.py
from datetime import datetime, timedelta
class Item:
    def __init__(self, name: str, req_num: str):
        """
        Initialize a new Item.

        :param name: The name of the item.
        :param req_num: The request number associated with the listing.
        """
        self.name = name
        self.req_num = req_num
        self.item_id = None
        self.description = ""
        self.starting_price = 0
        self.current_price = 0
        self.seller_name = None
        self.duration = 0  # Duration in minutes
        self.bids = []  # List to hold bids as tuples: (bid_amount, bidder_name)
        self.highest_bidder = None
        self.subscribed_clients = []  # List of client names that have subscribed to this item
        self.end_time = None  # will be set later
        self.active = True

    def add_client(self, client_name: str):
        """
        Add a client to the subscribed clients list if not already subscribed.
        """
        if client_name not in self.subscribed_clients:
            self.subscribed_clients.append(client_name)

    def add_item_unique(self, item_id: int, starting_price: int, description: str, seller_name: str, duration: int):
        """
        Set additional properties for the item.

        :param item_id: Unique identifier for the item.
        :param starting_price: Starting (reserve) price.
        :param description: Description of the item.
        :param seller_name: Name of the seller listing the item.
        :param duration: Auction duration in minutes.
        """
        self.item_id = item_id
        self.starting_price = starting_price
        self.current_price = starting_price  # Initially, the current price equals the starting price.
        self.description = description
        self.seller_name = seller_name
        self.duration = duration
        # Set the auction's end time based on the duration in minutes
        self.end_time = datetime.now() + timedelta(minutes=duration)


    def update_highest_bid(self, bid_amount: int, bidder_name: str):
        """
        Update the current price and highest bidder if bid_amount is greater than the current_price.

        :param bid_amount: The new bid amount.
        :param bidder_name: The name of the bidder.
        :return: A tuple (previous_price, updated) where updated is True if the bid was successful.
        """
        current = self.current_price
        if bid_amount > self.current_price:
            self.current_price = bid_amount
            self.highest_bidder = bidder_name
            self.bids.append((bid_amount, bidder_name))
            return (current, True)
        else:
            return (self.current_price, False)

    def get_final_bid(self):
        """
        Get the final bid data.

        :return: A tuple (current_price, highest_bidder)
        """
        return (self.current_price, self.highest_bidder)

    def get_seller_names(self):
        """
        Get the seller's name as a list. This may be useful if the auction system
        were to support multiple sellers per item.

        :return: List of seller names.
        """
        return [self.seller_name] if self.seller_name else []

    def get_lowest_negotiable_item(self):
        """
        For a simple auction with one seller, simply return the seller's name.

        :return: The seller's name.
        """
        return self.seller_name

    def remove_seller(self, seller_name: str):
        """
        Remove the seller from the item. In a single-seller auction,
        this might simply clear the seller_name.

        :param seller_name: The seller name to remove.
        """
        if self.seller_name == seller_name:
            self.seller_name = None

    def __str__(self):
        return (f"Item(name={self.name}, current_price={self.current_price}, "
                f"highest_bidder={self.highest_bidder}, seller={self.seller_name}, "
                f"active={self.active}, end_time={self.end_time})")

    def __repr__(self):
        return self.__str__()
