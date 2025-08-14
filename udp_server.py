import socket
import json
import os
import threading
import time
from datetime import datetime, timedelta

class AuctionServer:
    def __init__(self, host='0.0.0.0', udp_port=5000, tcp_port=5001):
        self.host = host
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.users = {}
        self.items = {}
        self.subscriptions = {}
        self.ip_to_name: dict[str, str] = {}
        self.lock = threading.Lock()

        if os.path.exists('server_data.json'):
            try:
                with open('server_data.json', 'r') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.subscriptions = data.get('subscriptions', {})
                    items_data = data.get('items', {})
                    self.items = {}
                    for k, v in items_data.items():
                        if 'start_time' in v and 'end_time' in v:
                            self.items[int(k)] = {
                                **v,
                                'start_time': datetime.fromisoformat(v['start_time']),
                                'end_time': datetime.fromisoformat(v['end_time'])
                            }
                        else:
                            self.items[int(k)] = v

                    print(f"Loaded {len(self.users)} users and {len(self.items)} items from saved data and {len(self.subscriptions)} subscriptions")
            except Exception as e:
                print(f"Error loading data: {e}")

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)

        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        print(f"Server started on {ip_address} - UDP:{self.udp_port}, TCP:{self.tcp_port}")

        self.threads = []
        self.active_auctions = {}
        self.request_counter = 1

    def save_data(self):
        """Save the current state of users, subscriptions, and items to disk"""
        try:
            data = {
                'users': self.users,
                'subscriptions': self.subscriptions,
                'items': {
                    item_id: {
                        **item,
                        'start_time': item['start_time'].isoformat() if isinstance(item.get('start_time'),
                                                                                   datetime) else item.get(
                            'start_time'),
                        'end_time': item['end_time'].isoformat() if isinstance(item.get('end_time'),
                                                                               datetime) else item.get('end_time'),
                        'bids': item.get('bids', []),  # Save bid list as is
                        'highest_bidder': item.get('highest_bidder')  # Save highest bidder name
                    }
                    for item_id, item in self.items.items()
                }
            }

            with open('server_data.json', 'w') as f:
                json.dump(data, f, indent=2)

            print("✅ Data saved to server_data.json")

        except Exception as e:
            print(f"❌ Error while saving data: {e}")

    def handle_registration(self, message, client_address):
        """Handle REGISTER message"""
        parts = message.split()

        if len(parts) != 7:
            return f"REGISTER-DENIED {parts[1]} Invalid format"

        _, req_num, name, role, ip, udp_port, tcp_port = parts

        if name in self.users:
            return f"REGISTER-DENIED {req_num} User name is already taken"

        self.users[name] = {
            'role': role,
            'ip': ip,
            'udp_port': udp_port,
            'tcp_port': tcp_port,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # Store the full client_address tuple as key.
        self.ip_to_name[client_address] = name
        self.save_data()
        return f"REGISTERED {req_num}"

    def handle_list_item(self, message, client_address):
        """Handle LIST_ITEM message"""
        parts = message.split()

        if len(parts) < 6:
            return f"LIST-DENIED {parts[1]} Invalid format"

        _, req_num, item_name, item_description, start_price, duration, seller_name = parts

        try:
            start_price = float(start_price)
            duration = int(duration)

            if start_price <= 0:
                return f"LIST_DENIED {req_num} start price must be positive"

            if duration <= 0:
                return f"LIST_DENIED {req_num} duration must be postive"

            if any(item['name'] == item_name for item in self.items.values()):
                return f"LIST_DENIED {req_num} item name already exists"

        except ValueError:
            return f"LIST_DENIED {req_num} invalid price or duration format"


        item_id = len(self.items) + 1

        self.items[item_id] = {
            'name': item_name,
            'description': item_description,
            'start_price': start_price,
            'current_price': start_price,
            'duration': duration,
            'seller_address': client_address,
            'seller_name': seller_name,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(minutes=duration),
            'active': True,
            'bids': [],
            'highest_bidder': None
        }
        self.save_data()

        auction_timer = threading.Thread(target=self.monitor_auction_end, args=(item_id,))
        auction_timer.daemon = True
        auction_timer.start()
        #self.threads.append(auction_timer)

        return f"ITEM_LISTED {req_num}"

    def monitor_auction_end(self, item_id):
        """Monitor when an auction ends and handle closure"""
        item = self.items[item_id]
        time_to_wait = (item['end_time'] - datetime.now()).total_seconds()

        if time_to_wait > 0:
            print(f"Auction for {item['name']} will end in {time_to_wait:.2f} seconds")
            time.sleep(time_to_wait)

        item = self.items[item_id]
        if not item['active']:
            return

        item['active'] = False
        print(f"🔔 Auction for {item['name']} has ended. Marking inactive.")
        self.save_data()

        print(f"Auction for {item['name']} has ended!")

        # If there are bids, notify the winner and seller
        # If there are bids, notify the winner and seller
        if item['bids'] and item['highest_bidder']:
            winner_name = item['highest_bidder']
            seller_name = item['seller_name']

            # Check if we have TCP connection info for both parties
            if winner_name not in self.users:
                print(f"⚠️ WARNING: Winner {winner_name} not found in self.users!")
            else:
                winner_info = self.users[winner_name]
                print(f"Winner TCP info: {winner_name} at {winner_info['ip']}:{winner_info['tcp_port']}")

            if seller_name not in self.users:
                print(f"⚠️ WARNING: Seller {seller_name} not found in self.users!")
            else:
                seller_info = self.users[seller_name]
                print(f"Seller TCP info: {seller_name} at {seller_info['ip']}:{seller_info['tcp_port']}")

            threading.Thread(target=self.handle_auction_close, args=(item_id,)).start()

        else:
            # No bids were placed
            print("NO BIDS !!!")
            self.send_no_offer_message(item_id)


    def handle_auction_close(self, item_id):
        """Handle the auction closure process using TCP"""
        item = self.items[item_id]
        seller_name = item['seller_name']
        winner_name = item['highest_bidder']
        final_price = item['current_price']

        print("\n===== DEBUG USER DATA =====")
        print(f"All registered users: {list(self.users.keys())}")
        print(f"Winner name: {winner_name}, Seller name: {seller_name}")
        if winner_name in self.users:
            print(f"Winner data: {self.users[winner_name]}")
        if seller_name in self.users:
            print(f"Seller data: {self.users[seller_name]}")
        print("==========================\n")

        # Connect to the winner (buyer) using TCP
        if winner_name in self.users:
            threading.Thread(target=self.send_winner_message,
                            args=(winner_name, item_id, final_price, seller_name)).start()

        # Connect to the seller using TCP
        if seller_name in self.users:
            threading.Thread(target=self.send_sold_message,
                            args=(seller_name, item_id, final_price, winner_name)).start()

    def send_winner_message(self, buyer_name, item_id, final_price, seller_name):
        """Send WINNER message to buyer via TCP"""
        if buyer_name not in self.users:
            print(f"Buyer {buyer_name} not found in registered users")
            return

        buyer_info = self.users[buyer_name]
        buyer_ip = buyer_info['ip']
        buyer_tcp_port = int(buyer_info['tcp_port'])
        item = self.items[item_id]

        print(f"Attempting to connect to buyer {buyer_name} at {buyer_ip}:{buyer_tcp_port}")

        # Create TCP connection to buyer
        tcp_client = None
        try:
            tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_client.settimeout(None)  # Set timeout for connection attempts

            # Try connecting to the buyer
            tcp_client.connect((buyer_ip, buyer_tcp_port))

            # Send WINNER message
            req_num = self.request_counter
            self.request_counter += 1

            winner_msg = f"WINNER {req_num} {item['name']} {final_price} {seller_name}"
            tcp_client.sendall(winner_msg.encode('utf-8'))
            print(f"Sent to buyer {buyer_name}: {winner_msg}")
            time.sleep(1)  # Wait a moment for client to process

            # KEEP THE SAME CONNECTION OPEN for purchase finalization
            self.handle_purchase_finalization(tcp_client, item_id, final_price, "buyer", buyer_name)

        except ConnectionRefusedError:
            print(f"Connection refused by buyer {buyer_name} at {buyer_ip}:{buyer_tcp_port}")
            print("The client TCP listener might not be running or the port is incorrect")
        except Exception as e:
            print(f"Error sending WINNER message to {buyer_name}: {e}")
            print(f"Buyer TCP details: IP={buyer_ip}, PORT={buyer_tcp_port}")
        finally:
            # DON'T close the connection here, it's closed in handle_purchase_finalization
            pass

    def send_sold_message(self, seller_name, item_id, final_price, buyer_name):
        """Send SOLD message to seller via TCP"""
        if seller_name not in self.users:
            print(f"Seller {seller_name} not found in registered users")
            return

        seller_info = self.users[seller_name]
        seller_ip = seller_info['ip']
        seller_tcp_port = int(seller_info['tcp_port'])
        item = self.items[item_id]

        print(f"Attempting to connect to buyer {buyer_name} at {seller_ip}:{seller_tcp_port}")

        # Create TCP connection to seller
        try:
            tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_client.settimeout(None)  # Set a timeout for the connection attempt
            tcp_client.connect((seller_ip, seller_tcp_port))

            # Send SOLD message
            req_num = self.request_counter
            self.request_counter += 1

            sold_msg = f"SOLD {req_num} {item['name']} {final_price} {buyer_name}"
            tcp_client.sendall(sold_msg.encode('utf-8'))
            print(f"Sent to seller {seller_name}: {sold_msg}")
            time.sleep(0.5)
            # Start purchase finalization process
            self.handle_purchase_finalization(tcp_client, item_id, final_price, "seller", seller_name)

        except Exception as e:
            print(f"Error sending SOLD message to {seller_name}: {e}")
            print(f"Buyer TCP details: IP={seller_ip}, PORT={seller_tcp_port}")
        finally:
            # DON'T close the connection here, it's closed in handle_purchase_finalization
            pass

    def send_no_offer_message(self, item_id):
        """Send NON_OFFER message to seller via TCP when no bids are placed"""
        item = self.items[item_id]
        seller_name = item['seller_name']

        if seller_name not in self.users:
            print(f"Seller {seller_name} not found in registered users")
            return

        seller_info = self.users[seller_name]
        seller_ip = seller_info['ip']
        seller_tcp_port = int(seller_info['tcp_port'])

        # Create TCP connection to seller
        try:
            tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_client.connect((seller_ip, seller_tcp_port))

            # Send NON_OFFER message
            req_num = self.request_counter
            self.request_counter += 1

            no_offer_msg = f"NON_OFFER {req_num} {item['name']}"
            tcp_client.sendall(no_offer_msg.encode('utf-8'))
            print(f"Sent to seller {seller_name}: {no_offer_msg}")

        except Exception as e:
            print(f"Error sending NON_OFFER message to {seller_name}: {e}")
        finally:
            tcp_client.close()

    def handle_purchase_finalization(self, tcp_socket, item_id, final_price, role, user_name):
        """Handle the purchase finalization process via TCP"""
        item = self.items[item_id]

        # Set a reasonable timeout for receiving responses
        #tcp_socket.settimeout(30)  # 30 seconds should be enough for user input

        try:
            # First send the INFORM_Req message
            req_num = self.request_counter
            self.request_counter += 1
            inform_msg = f"INFORM_Req {req_num} {item['name']} {final_price}"

            print(f"Sending INFORM_Req to {role} {user_name}")
            tcp_socket.sendall(inform_msg.encode('utf-8'))
            print(f"Sent to {role} {user_name}: {inform_msg}")

            # Add a small delay after sending to ensure the message is processed
            time.sleep(0.5)

            # Wait for INFORM_Res response
            print(f"Waiting for INFORM_Res from {role} {user_name}...")
            data = tcp_socket.recv(1024).decode('utf-8')

            if not data:
                print(f"Empty response from {role} {user_name}")
                return

            print(f"Received from {role} {user_name}: {data}")

            parts = data.split()
            if not data.startswith("INFORM_Res") or len(parts) < 6:
                # Invalid response, cancel transaction
                cancel_msg = f"CANCEL {req_num} Invalid response format"
                tcp_socket.sendall(cancel_msg.encode('utf-8'))
                print(f"Invalid response format from {role} {user_name}, sent CANCEL")
                time.sleep(0.5)  # Give time for CANCEL to be sent
                return

            # Process payment information
            _, resp_req_num, name, cc_num, cc_exp_date, *address_parts = parts
            address = " ".join(address_parts)

            # Store information for transaction processing
            with self.lock:  # Use a lock for thread safety
                if role == "buyer":
                    item['buyer_info'] = {
                        'name': name,
                        'cc_num': cc_num,
                        'cc_exp_date': cc_exp_date,
                        'address': address
                    }
                    print(f"Stored buyer payment info")
                else:  # seller
                    item['seller_info'] = {
                        'name': name,
                        'cc_num': cc_num,
                        'cc_exp_date': cc_exp_date,
                        'address': address
                    }
                    print(f"Stored seller payment info")
                self.save_data()  # Save after updating

            # Only send shipping info if we have both buyer and seller info
            if role == "seller" and 'buyer_info' in item:
                try:
                    # Give extra time before sending shipping info
                    time.sleep(0.5)

                    # Send shipping info to seller
                    shipping_msg = f"Shipping_Info {req_num} {item['buyer_info']['name']} {item['buyer_info']['address']}"
                    tcp_socket.sendall(shipping_msg.encode('utf-8'))
                    print(f"Sent shipping info to seller {user_name}")

                    # Wait longer before closing to make sure shipping info is received
                    time.sleep(1)
                except Exception as ship_err:
                    print(f"Error sending shipping info: {ship_err}")

        except socket.timeout:
            print(f"Timeout waiting for response from {role} {user_name}")
            try:
                cancel_msg = f"CANCEL {req_num} Connection timeout"
                tcp_socket.sendall(cancel_msg.encode('utf-8'))
                time.sleep(0.5)  # Give time for CANCEL to be sent
            except:
                pass
        except Exception as e:
            print(f"Error in purchase finalization with {role} {user_name}: {e}")
            print(f"Error type: {type(e)}")
            try:
                # Try to send a cancel message
                cancel_msg = f"CANCEL {req_num} Connection error"
                tcp_socket.sendall(cancel_msg.encode('utf-8'))
                time.sleep(0.5)  # Give time for CANCEL to be sent
            except:
                pass
        finally:
            # Always close the socket at the end, but wait to make sure messages are sent
            time.sleep(1)
            try:
                tcp_socket.close()
                print(f"Closed TCP connection to {role} {user_name}")
            except:
                pass


    def handle_auction_subscription(self, message, client_address):
        """Handle SUBSCRIBE message"""
        parts = message.split()

        if len(parts) < 3:
            return f"SUBSCRIPTION-DENIED {parts[1]} Invalid format"

        _, req_num, item_name, client_name = parts

        if not client_name:
            return f"SUBSCRIBE-DENIED {req_num} User not registered"
        if not any(item['name'] == item_name for item in self.items.values()):
            return f"SUBSCRIPTION-DENIED {req_num} item does not exist"
        subscription_id = len(self.subscriptions) + 1


        self.subscriptions[subscription_id] = {
            'client_name': client_name,
            'name': item_name
        }
        self.save_data()

        required_item = next((item for item in self.items.values() if item['name'] == item_name), None)
            
        # Calculate time left in seconds
        time_left = max(0, int((required_item['end_time'] - datetime.now()).total_seconds()))
        
        # Send initial auction status to subscriber
        announce_msg = f"AUCTION_ANNOUNCE {req_num} {item_name} {required_item['description']} {required_item['current_price']} {time_left}"
        self.udp_socket.sendto(announce_msg.encode('utf-8'), client_address)
        print(f"Sent {announce_msg}")

        return f"SUBSCRIBED {req_num}"

    def handle_deregistration(self, message):
        """Handle DE-SUBSCRIBE message"""
        parts = message.split()

        if len(parts) != 3:
            return None

        _, req_num, name = parts


        if name in self.users:
            del self.users[name]
            self.save_data()
            print(f"User {name} deregistered")

            return None


# THIS ISNT WORKING PLZ FIX ME
    def handle_unsubscribe(self, message, client_address):
        """Handle DE-REGISTER message"""
        parts = message.split()

        if len(parts) != 3:
            return None

        _, req_num, name, client_name = parts


        to_delete = None
        for key, subscription in self.subscriptions.items():
            if subscription.get('name') == name and subscription.get('client_name') == client_name:
                to_delete = key
                break

        if to_delete is not None:
            del self.subscriptions[to_delete]
            self.save_data()
            print(f"Subscription to {name} for {client_name} deleted")
        else:
            print(f"No subscription found for {name} and {client_name}")
        return None

    def handle_login(self, message, client_address):
        """Handle LOGIN message"""
        parts = message.split()

        # Check if we have the TCP port in the message
        if len(parts) == 4:  # LOGIN req_num name tcp_port
            _, req_num, name, tcp_port = parts
            has_tcp_port = True
        elif len(parts) == 3:  # Old format: LOGIN req_num name
            _, req_num, name = parts
            has_tcp_port = False
        else:
            return f"LOGIN-FAILED {parts[1]} Invalid format"

        if name in self.users:
            role = self.users[name]['role']
            # Save IP → name mapping on login
            self.ip_to_name[client_address] = name

            # Update the user's IP address to match their current connection
            self.users[name]['ip'] = client_address[0]

            # Update TCP port if provided
            if has_tcp_port:
                self.users[name]['tcp_port'] = tcp_port
                print(f"Updated TCP port for {name} to {tcp_port}")

            self.save_data()

            print(f"User {name} logged in successfully from {client_address[0]}")
            return f"LOGIN_SUCCESS {req_num} role={role}"
        else:
            print(f"Login failed for user {name} - not found")
            return f"LOGIN-FAILED {req_num} User not found"

    def run(self):
        """Run the server"""
        print("Server running")

        #tcp_thread = threading.Thread(target=self.tcp_listener)
        #tcp_thread.daemon = True
        #tcp_thread.start()
        #self.threads.append(tcp_thread)

        try:
            while True:
                data, client_address = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                print(f"Received from {client_address}: {message}")
                print(f"Handling request in thread: {threading.current_thread().name}")


                if message.startswith("REGISTER"):
                    response = self.handle_registration(message, client_address)
                elif message.startswith("DE-REGISTER"):
                    response = self.handle_deregistration(message)
                elif message.startswith("LOGIN"):
                    response = self.handle_login(message, client_address)
                elif message.startswith("LIST_ITEM"):
                    response = self.handle_list_item(message, client_address)
                elif message.startswith("SUBSCRIBE"):
                  response = self.handle_auction_subscription(message, client_address)
                elif message.startswith("DE-SUBSCRIBE"):
                  response = self.handle_unsubscribe(message, client_address)
                elif message.startswith("BID"):
                    response = self.handle_bid(message, client_address)

                else:
                    response = None
                    print(f"Unknown command: {message}")

                if response:
                    self.udp_socket.sendto(response.encode('utf-8'), client_address)
                    print(f"Send to {client_address}: {response}")

                # self.handle_seller_timeout()

        except KeyboardInterrupt:
            print("\n Server shutting down...")
            self.save_data()
            self.socket.close()

    def tcp_listener(self):
        """Listen for incoming TCP connections"""
        print(f"TCP listener started on port {self.tcp_port}")

        while True:
            try:
                client_socket, client_address = self.tcp_socket.accept()
                print(f"New TCP connection from {client_address}")

                # Handle the TCP connection in a separate thread
                client_thread = threading.Thread(target=self.handle_tcp_client, args=(client_socket, client_address))
                client_thread.daemon = True
                client_thread.start()
                self.threads.append(client_thread)

            except Exception as e:
                print(f"Error accepting TCP connection: {e}")

    def handle_tcp_client(self, client_socket, client_address):
        """Handle individual TCP client connections"""
        try:
            # Wait for any message from client
            data = client_socket.recv(1024).decode('utf-8')
            print(f"Received TCP from {client_address}: {data}")

            # Process message based on type
            if data.startswith("INFORM_Res"):
                # Handle purchase info response
                pass  # This is handled in handle_purchase_finalization
            else:
                print(f"Unknown TCP message: {data}")

        except Exception as e:
            print(f"Error handling TCP client {client_address}: {e}")
        finally:
            client_socket.close()

    def handle_bid(self, message, client_address):
        """Handle BID message"""
        parts = message.split()
        if len(parts) != 4:
            return f"BID_REJECTED Invalid format"

        _, req_num, item_name, bid_amount = parts
        bidder_name = self.ip_to_name.get(client_address)

        if not bidder_name:
            return f"BID_REJECTED {req_num} User_not_registered"

        # Find the item
        item_id = next((id for id, item in self.items.items() if item['name'] == item_name), None)
        if item_id is None:
            return f"BID_REJECTED {req_num} Item_not_found"

        item = self.items[item_id]

        # Check if auction is still active
        if not item.get('active', True):
            return f"BID_REJECTED {req_num} Auction_ended"

        # Validate bid
        try:
            bid_amount = float(bid_amount)
        except ValueError:
            return f"BID_REJECTED {req_num} Invalid_bid_amount"

        if bid_amount <= item['current_price']:
            return f"BID_REJECTED {req_num} Bid_too_low"

        # Update bid
        item['bids'].append((bidder_name, bid_amount))
        item['current_price'] = bid_amount
        item['highest_bidder'] = bidder_name

        print(f"Accepted bid of {bid_amount} from {bidder_name} on {item_name}")
        self.save_data()

        # Notify all subscribers
        for sub_id, sub in self.subscriptions.items():
            if sub['name'] == item_name and sub['client_name'] != bidder_name:
                subscriber = self.users.get(sub['client_name'])
                if subscriber:
                    try:
                        # Calculate time left in seconds
                        time_left = max(0, int((item['end_time'] - datetime.now()).total_seconds()))

                        # Include bidder name and time left in message
                        update_msg = f"BID_UPDATE {req_num} {item_name} {bid_amount} {bidder_name} {time_left}"

                        addr = (subscriber['ip'], int(subscriber['udp_port']))
                        self.udp_socket.sendto(update_msg.encode('utf-8'), addr)
                    except Exception as e:
                        print(f"Failed to send update to {subscriber['name']}: {e}")

        return f"BID_ACCEPTED {req_num}"


if __name__ == "__main__":
    server = AuctionServer()
    server.run()

