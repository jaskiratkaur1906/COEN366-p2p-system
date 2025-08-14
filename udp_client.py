import socket
import random
import time
import threading
import sys

class UDPClient:
    def __init__(self, server_host='localhost', server_port=5000, server_tcp_port=5001):
        # Remove the nested __init__ function
        self.server_address = (server_host, server_port)
        self.server_tcp_address = (server_host, server_tcp_port)
        self.client_name = None
        self.client_udp_port = random.randint(6000, 7000)
        self.client_tcp_port = random.randint(7001, 8000)
        self.role = None
        self.request_counter = 1
        self.is_registered = False
        self.tcp_server_socket = None
        self.tcp_listener_thread = None
        self.running = True

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', self.client_udp_port))
        self.udp_socket.settimeout(5.0)

        self.udp_listener_thread = threading.Thread(target=self.udp_listener)
        self.udp_listener_thread.daemon = True
        self.udp_listener_thread.start()
        self.payment_in_progress = False
        # Start TCP listener immediately
        self.start_tcp_listener()
        print(f"Client initialized with UDP port: {self.client_udp_port}, TCP port: {self.client_tcp_port}")

    def udp_listener(self):
        """Listen for incoming UDP messages"""
        self.udp_socket.settimeout(3.0)  # Set timeout for checking if client is still running

        while self.running:
            try:
                data, server = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                print(f"\nReceived from server: {message}")

                # Handle different types of messages
                '''if message.startswith("AUCTION_ANNOUNCE"):
                    self.handle_auction_announcement(message)
                elif message.startswith("BID_UPDATE"):
                    self.handle_bid_update(message)
                elif message.startswith("PRICE_ADJUSTMENT"):
                    self.handle_price_adjustment(message)'''

            except socket.timeout:
                # This is just to allow checking if we're still running
                continue
            except Exception as e:
                if self.running:
                    print(f"Error in UDP listener: {e}")

        print("UDP listener stopped")

    def start_tcp_listener(self):
        """Start TCP listener socket for auction closures"""
        # Prevent double initialization
        if self.tcp_listener_thread is not None and self.tcp_listener_thread.is_alive():
            print("TCP listener already running.")
            return

        try:
            # Close previous socket if it exists
            if self.tcp_server_socket:
                try:
                    self.tcp_server_socket.close()
                except:
                    pass

            self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Use 0.0.0.0 to listen on all interfaces
            self.tcp_server_socket.bind(('0.0.0.0', self.client_tcp_port))
            self.tcp_server_socket.listen(5)

            # Get the actual port (important if we used port 0)
            actual_port = self.tcp_server_socket.getsockname()[1]
            self.client_tcp_port = actual_port  # Update with the actual bound port

            print(f"TCP listener started on port {self.client_tcp_port}")
        except OSError as e:
            print(f"Port {self.client_tcp_port} is in use. Trying a different port.")
            self.client_tcp_port = random.randint(7001, 8000)
            print(f"New TCP port: {self.client_tcp_port}")
            # Try again with new port
            self.start_tcp_listener()
            return

        # Start listener thread
        self.tcp_listener_thread = threading.Thread(target=self.tcp_listener)
        self.tcp_listener_thread.daemon = True
        self.tcp_listener_thread.start()
        print(f"TCP listener thread started and listening on port {self.client_tcp_port}")

    def tcp_listener(self):
        """Listen for incoming TCP connections from the server"""
        self.tcp_server_socket.settimeout(None)  # Set timeout for checking if client is still running

        while self.running:
            try:
                client_socket, address = self.tcp_server_socket.accept()
                print(f"Received TCP connection from {address}")

                # Handle the TCP connection in a separate thread
                tcp_handler = threading.Thread(target=self.handle_tcp_connection, args=(client_socket,))
                tcp_handler.daemon = True
                tcp_handler.start()

            except socket.timeout:
                # This is just to allow checking if we're still running
                continue
            except Exception as e:
                if self.running:
                    print(f"Error accepting TCP connection: {e}")

        print("TCP listener stopped")

    def handle_tcp_connection(self, conn):
        """Handle incoming TCP connection"""
        try:
            # Set a reasonable timeout
            #conn.settimeout()  # 60 seconds for user input

            # Instead of reading once, loop to read multiple messages
            while True:
                data = conn.recv(1024).decode('utf-8')
                print(f"\nReceived TCP message: {data}")

                if not data:
                    print("Connection closed by server")
                    break

                parts = data.strip().split()
                if not parts:
                    print("No valid message parts")
                    continue

                message_type = parts[0]

                if message_type == "WINNER":
                    _, req_num, item_name, final_price, seller_name = parts
                    print(f"\nYou won the auction for '{item_name}' at ${final_price}.")
                    print(f"Seller: {seller_name}")
                    print("Waiting for purchase information request...")
                    # Don't break, wait for next message

                elif message_type == "SOLD":
                    _, req_num, item_name, final_price, buyer_name = parts
                    print(f"\nYour item '{item_name}' was sold to {buyer_name} for ${final_price}.")
                    print("Waiting for purchase information request...")
                    # Don't break, wait for next message

                elif message_type == "INFORM_Req":
                    _, req_num, item_name, final_price = parts
                    self.payment_in_progress = True
                    # Make this extremely visible
                    print("\n" + "=" * 50)
                    print(f"PURCHASE INFORMATION REQUIRED")
                    print(f"Please provide your details to finalize the purchase for '{item_name}' (${final_price})")
                    print("=" * 50)
                    print("IMPORTANT: The next 4 inputs are for payment details, not menu choices!")
                    print("=" * 50, flush=True)

                    # Add a delay to ensure the prompts are visible
                    time.sleep(1)

                    try:
                        name = input("Enter your full name: ")
                        cc_num = input("Enter your credit card number: ")
                        cc_exp = input("Enter credit card expiry (MM/YY): ")
                        address = input("Enter your shipping address: ")

                        inform_response = f"INFORM_Res {req_num} {name} {cc_num} {cc_exp} {address}"
                        conn.sendall(inform_response.encode('utf-8'))
                        print("Sent payment and address info to server.")
                        print("Waiting for confirmation...")
                    except Exception as e:
                        print(f"Error during input process: {e}")
                    self.payment_in_progress = False
                elif message_type == "Shipping_Info":
                    req_num = parts[1]
                    buyer_name = parts[2]
                    buyer_address = " ".join(parts[3:])
                    print(f"\nShip item to {buyer_name} at address: {buyer_address}")
                    # This is the end of the conversation for the seller
                    break

                elif message_type == "CANCEL":
                    reason = " ".join(parts[2:])
                    print(f"\nTransaction cancelled: {reason}")
                    break

                else:
                    print(f"Unknown TCP message type: {message_type}")

        except socket.timeout:
            print("Connection timed out while waiting for data")
        except ConnectionAbortedError:
            print("Connection was aborted by the server")
        except ConnectionResetError:
            print("Connection was reset by the server")
        except Exception as e:
            print(f"Error handling TCP connection: {e}")
        finally:
            try:
                conn.close()
                print("TCP connection closed")
            except:
                pass

    def prompt_user_details(self):
        """Prompt user for name and role"""
        print("\n--- User Registration ---")
        self.client_name = input("Enter your username: ")

        while True:
            role_input = input("Select your role (buyer/seller): ").lower()
            if role_input in ["buyer", "seller"]:
                self.role = role_input
                break
            else:
                print("Invalid role. Please enter 'buyer' or 'seller'.")

    def register(self):
        """Send registration request"""
        if not self.client_name or not self.role:
            self.prompt_user_details()

        # Ensure TCP listener is running with correct port before registration
        self.start_tcp_listener()

        req_num = self.request_counter
        self.request_counter += 1

        # Get the actual machine hostname and IP for better connectivity
        local_ip = socket.gethostbyname(socket.gethostname())

        message = f"REGISTER {req_num} {self.client_name} {self.role} {local_ip} {self.client_udp_port} {self.client_tcp_port}"

        print(f"Sending: {message}")
        self.udp_socket.sendto(message.encode('utf-8'), self.server_address)

        try:
            data, server = self.udp_socket.recvfrom(1024)
            response = data.decode('utf-8')
            print(f"Received: {response}")
            if response.startswith("REGISTERED"):
                self.is_registered = True
                # TCP listener should already be running from init
                print(f"Registration successful. TCP listener is active on port {self.client_tcp_port}")
            return response
        except socket.timeout:
            print("Timeout waiting for response")
            return None

    def login(self):
        """Login with existing account"""
        print("\n--- User Login ---")
        self.client_name = input("Enter your username: ")

        # Ensure TCP listener is running before login
        if not self.tcp_listener_thread or not self.tcp_listener_thread.is_alive():
            self.start_tcp_listener()

        req_num = self.request_counter
        self.request_counter += 1

        # Include TCP port in login message
        message = f"LOGIN {req_num} {self.client_name} {self.client_tcp_port}"

        print(f"Sending: {message}")
        self.udp_socket.sendto(message.encode('utf-8'), self.server_address)

        try:
            data, server = self.udp_socket.recvfrom(1024)
            response = data.decode('utf-8')
            print(f"Received: {response}")

            if response.startswith("LOGIN_SUCCESS"):
                self.is_registered = True
                self.role = response.split("role=")[1].strip()
                print(f"Login successful as {self.role}. TCP listener active on port {self.client_tcp_port}")
            else:
                print("Login failed. User not found or invalid credentials.")
                return False
            return True
        except socket.timeout:
            print("Timeout waiting for response")
            return False

    def deregister(self):
        """Send deregistration request"""
        req_num = self.request_counter
        self.request_counter += 1

        message = f"DE-REGISTER {req_num} {self.client_name}"

        print(f"Sending: {message}")
        self.udp_socket.sendto(message.encode('utf-8'), self.server_address)

        print("Deregistration message sent")
        self.client_name = None
        self.role = None
        self.is_registered = False

    def logout(self):
        """Handle logout"""
        self.client_name = None
        self.role = None
        self.is_registered = False
        print("Logged out")

    def close(self):
        """Close the socket"""
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()
        if self.tcp_server_socket:
            self.tcp_server_socket.close()
        print("Client stopped")

    def bid_item(self):
        """Handle item bidding"""
        if self.role != "buyer":
            print("Only buyers can bid on items.")
            return

        print("\n--- Bid on Item ---")
        item_name = input("Enter item name to bid on: ")
        bid_amount = input("Enter bid amount: ")

        req_num = self.request_counter
        self.request_counter += 1

        message = f"BID {req_num} {item_name} {bid_amount}"
        print(f"Sending Bid: {message}")
        self.udp_socket.sendto(message.encode('utf-8'), self.server_address)

        try:
            data, server = self.udp_socket.recvfrom(1024)
            response = data.decode('utf-8')
            print(f"Received: {response}")

            if response.startswith("BID_ACCEPTED"):
                print(f"Bid of ${bid_amount} accepted for {item_name}")
            elif response.startswith("BID_REJECTED"):
                reason = response.split(" ", 2)[2]
                print(f"Bid rejected: {reason}")
            return response

        except socket.timeout:
            print("Timeout waiting for response")
            return None

    def auction_item(self):
        """Handle auction item"""
        if self.role != "seller":
            print("Only sellers can auction items.")
            return

        print("\n--- Create Auction ---")
        item_name = input("Enter item name: ")
        item_description = input("Enter item description: ")
        start_price = input("Enter reserve price: ")
        duration = input("Enter auction duration in minutes: ")

        try:
            float(start_price)
            int(duration)
        except ValueError:
            print("Invalid price or duration format. Price and duration needs to be a number")
            return

        req_num = self.request_counter
        self.request_counter += 1

        item_name_safe = item_name.replace(' ', "_")
        item_description_safe = item_description.replace(" ", "_")

        message = f"LIST_ITEM {req_num} {item_name_safe} {item_description_safe} {start_price} {duration} {self.client_name}"

        print(f"Sending: {message}")
        self.udp_socket.sendto(message.encode('utf-8'), self.server_address)

        self.udp_socket.settimeout(5.0)

        try:
            data, server = self.udp_socket.recvfrom(1024)
            response = data.decode('utf-8')
            print(f"Received: {response}")

            if response.startswith("ITEM_LISTED"):
                print("Item listed for auction")
            elif response.startswith("LIST-DENIED"):
                print(f"Item listing denied: {' '.join(response.split()[2:])}")

            return response

        except socket.timeout:
            print("Timeout waiting for response")
            return None
        finally:
            self.udp_socket.settimeout(5.0)

    def subscribe(self):
        """Handle subscribe item"""
        if self.role != "buyer":
            print("Only buyer can subscribe to auction items.")
            return

        print("\n--- Subscription ---")
        item_name = input("Enter item name: ")

        req_num = self.request_counter
        self.request_counter += 1

        item_name_safe = item_name.replace(' ', "_")

        message = f"SUBSCRIBE {req_num} {item_name_safe} {self.client_name}"

        print(f"Sending: {message}")
        self.udp_socket.sendto(message.encode('utf-8'), self.server_address)

        self.udp_socket.settimeout(5.0)

        try:
            data, server = self.udp_socket.recvfrom(1024)
            response = data.decode('utf-8')
            print(f"Received: {response}")

            if response.startswith("SUSBSCRIBED"):
                print("Subscribed to auction announcements")
                # Wait for auction announcement
                try:
                    data, server = self.udp_socket.recvfrom(1024)
                    response = data.decode('utf-8')
                    print(f"Received: {response}")
                    if response.startswith("AUCTION_ANNOUNCED"):
                        parts = response.split()
                        req_num = parts[1]
                        item_name = parts[2]
                        description = parts[3].replace("_", " ")
                        current_price = parts[4]
                        time_left = parts[5]
                        print(f"\nAuction Announcement Details:")
                        print(f"Item Name: {item_name}")
                        print(f"Description: {description}")
                        print(f"Current Price: ${current_price}")
                        print(f"Time Left: {time_left} minutes")
                except socket.timeout:
                    print("No auction announcement received")

            elif response.startswith("AUCTION_ANNOUNCED"):
                print("Auction announcement received")
                parts = response.split()
                req_num = parts[1]
                item_name = parts[2]
                description = parts[3].replace("_", " ")
                current_price = parts[4]
                time_left = parts[5]
                print(f"\nAuction Announcement Details:")
                print(f"Item Name: {item_name}")
                print(f"Description: {description}")
                print(f"Current Price: ${current_price}")
                print(f"Time Left: {time_left} minutes")
                # Wait for subscription confirmation
                try:
                    data, server = self.udp_socket.recvfrom(1024)
                    response = data.decode('utf-8')
                    print(f"Received: {response}")
                    if response.startswith("SUBSCRIBED"):
                        print("Subscribed to auction announcements")
                except socket.timeout:
                    print("No auction announcement received")
            elif response.startswith("SUBSCRIPTION-DENIED"):
                print(f"Subscription denied: {' '.join(response.split()[2:])}")
            return response

        except socket.timeout:
            print("Timeout waiting for response")
            return None

        finally:
            self.udp_socket.settimeout(5.0)

    def unsubscribe(self):
        """Send de-subscribe request"""
        item_name = input("Enter item name: ")

        req_num = self.request_counter
        self.request_counter += 1

        item_name_safe = item_name.replace(' ', "_")

        message = f"DE-SUBSCRIBE {req_num} {item_name_safe} {self.client_name}"

        print(f"Sending: {message}")
        self.udp_socket.sendto(message.encode('utf-8'), self.server_address)


def main():
    """Main function with user interface"""
    server_host = input("Enter server IP (leave blank for localhost): ") or "localhost"
    server_port = int(input("Enter server UDP port (leave blank for 5000): ") or "5000")
    server_tcp_port = int(input("Enter server TCP port (leave blank for 5001): ") or "5001")

    client = UDPClient(server_host, server_port, server_tcp_port)

    try:
        while True:
            # Prevent menu from showing during TCP payment input
            if client.payment_in_progress:
                continue

            if not client.is_registered:
                print("\n=== Auction System ===")
                print("1. Register")
                print("2. Login")
                print("3. Exit")

                choice = input("\nEnter your choice (1-3): ")

                if choice == "1":
                    client.register()
                elif choice == "2":
                    client.login()
                elif choice == "3":
                    print("Exiting system. Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")

            # If logged in, show main menu
            else:
                print(f"\n=== Auction System - Logged in as {client.client_name} ({client.role}) ===")
                print("1. Auction an item")
                print("2. Deregister account")
                print("3. Logout")
                print("4. Subscribe to auction announcements")
                print("5. Unsubscribe from auction announcement")
                print("6. Bid")
                print("7. Show my TCP port")

                choice = input("\nEnter your choice (1-7): ")

                if choice == "1":
                    client.auction_item()
                elif choice == "2":
                    confirm = input("Are you sure you want to deregister? (y/n): ")
                    if confirm.lower() == 'y':
                        client.deregister()
                elif choice == "3":
                    client.logout()
                elif choice == "4":
                    client.subscribe()
                elif choice == "5":
                    client.unsubscribe()
                elif choice == "6":
                    client.bid_item()
                elif choice == "7":
                    print(f"Your TCP port is: {client.client_tcp_port}")
                    print(
                        f"TCP listener active: {client.tcp_listener_thread is not None and client.tcp_listener_thread.is_alive()}")
                else:
                    print("Invalid choice. Please try again.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
