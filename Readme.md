# COEN 366 – P2P Auction System

##  Project Overview
This project was developed to deepen our understanding of communication protocols and network programming. It implements a **Peer-to-Peer Auction System** in Python, where buyers and sellers interact through a centralized server using both **UDP** and **TCP** communication protocols. The system uses Python’s native `socket` library for client-server communication.

##  Features
- **User Registration & Login** – Persistent accounts with session continuity.
- **Item Listing** – Sellers can list items with descriptions, starting price, and duration.
- **Bidding System** – Buyers place bids and receive real-time bid updates.
- **Auction Subscriptions** – Buyers can subscribe/unsubscribe to specific items.
- **Negotiation Mechanism** – Sellers can adjust prices if no bids are received.
- **Auction Closure & Finalization** – Uses TCP for reliable winner notifications, payment, and shipping details.
- **Threaded Server & Client** – Concurrent handling of multiple users.
- **Logging** – Event logging for server and client actions.

##  Technology Stack
- **Language:** Python
- **Networking:** UDP & TCP with `socket` library
- **Concurrency:** Python `threading` library
- **Data Storage:** JSON files

##  System Design
- **Server** – Manages registration, listings, subscriptions, bidding, auction closure, and data persistence.
- **Client** – Provides a CLI for interacting with the system and handles both UDP & TCP communication.

##  Testing & Debugging
- Each feature tested with valid and invalid inputs.
- Edge cases tested to ensure error handling.
- Bugs (e.g., incorrect TCP port connections) identified and fixed through iterative testing.

##  Team Members
- **Scott McDonald** – Registration, server setup, client menus, subscription handling.
- **Mohammed Zahed** – Auction announcements, threading, auction/bidding logic.
- **Jaskirat Kaur** – Auction closure, TCP connection, Auction Finalization, auction updates, subscription.

##  License
This project is licensed under the [MIT License](LICENSE).

---
