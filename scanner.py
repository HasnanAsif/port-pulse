# Import packages
import paramiko #SSH
import telnetlib # Telnet
import sys
from datetime import datetime
import time
import schedule
import os.path


# Create and configure SSH Client
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Empty Telnet Object ready for connecting
telnet = None


# Function to read switch IPs from a file
def get_switch_ips(file_path="switches.txt"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read().splitlines()
    print(f"Error: {file_path} not found.")
    return []


# Keeps track of inactive ports and removes reactivated ports from the overview
def update_overviews(ip, trues, falses):
    overview_path = f"ports/{ip}/overview.txt"
    os.makedirs(f"ports/{ip}", exist_ok=True) # Ensure the directory exists

    # If the overview file doesn't exist, create it with the inactive ports
    if not os.path.exists(overview_path):
        with open(overview_path, "w") as f:
            f.write("\n".join(falses) + "\n")
    
    # Read the existing overview file and remove reactivated ports
    else:
        with open(overview_path, "r") as f:
            content = f.read()
        for port in trues:
            content = content.replace(port + "\n", "")
        with open(overview_path, "w") as f:
            f.write(content)


# Creates files for each port and updates the overview file
def process_port_data(ip, rows):
    trues, falses = [], []  # Lists for active and inactive ports
    try:
        os.makedirs(f"ports/{ip}", exist_ok=True)  # Ensure the directory exists
        print(f"Directory created or exists: ports/{ip}")
    except Exception as e:
        print(f"Failed to create directory for {ip}: {e}")
        return

    for line in rows:
        # Extract port information and connection status
        port = line.split(" ")[0].replace("/", "_")
        status = "connected" in line
        results = f"{datetime.now()}\t{status}\n"

        port_file = f"ports/{ip}/{port}.txt"
        mode = "a+" if os.path.exists(port_file) else "w+"
        try:
            # Write the connection status to the port-specific file
            with open(port_file, mode) as f:
                f.write(results)
                print(f"Updated port file: {port_file}")
        except Exception as e:
            print(f"Failed to write to file {port_file}: {e}")

        # Categorize the port as active or inactive
        if status:
            trues.append(port)
        else:
            falses.append(port)

    # Update the overview file with inactive ports
    update_overviews(ip, trues, falses)


# Retrieves and processes the port data from a switch using SSH or Telnet
def gather_info(ip, username, password, ssh_mode=True):
    rows = []
    try: 
        # Connect via SSH
        if ssh_mode:  
            ssh_client.connect(ip, username=username, password=password)
            print(f"Connected to {ip} via SSH.")
            stdin, stdout, stderr = ssh_client.exec_command("show int status")
            rows = [line.strip() for line in stdout.readlines() if line.strip()]
            ssh_client.close()

        # Connect via Telnet
        else:  
            telnet = telnetlib.Telnet(ip)
            telnet.read_until(b"Username: ")
            telnet.write(username.encode() + b"\n")
            telnet.read_until(b"Password: ")
            telnet.write(password.encode() + b"\n")
            telnet.write(b"show int status\n")
            telnet.write(b"exit\n")
            results = telnet.read_all().decode()
            rows = results.splitlines()[5:-2] if "^" not in results else []

    except Exception as e:
        print(f"Error gathering info from {ip}: {e}")
        return

    if rows:
        print(f"Processing data for {ip}...")
        process_port_data(ip, rows)


# Uses the provided username and password for authentication
def check_ports():
    username = "[your_username]" # Replace with your SSH/Telnet username
    password = "[your_password]" # Replace with your SSH/Telnet password

    for ip in get_switch_ips():
        print(f"Checking ports for {ip} at {datetime.now()}...")
        try:
            gather_info(ip, username, password)
        except Exception as e:
            print(f"Failed to gather info for {ip}: {e}")


# Main function to schedule and run the port-checking job
def main():
    print("Scheduling job...")
    schedule.every(30).minutes.do(check_ports) # Schedule the job to run every 30 minutes
    print("Job scheduled. Running initial check...")
    check_ports() # Perform an initial check immediately
    while True:
        schedule.run_pending() 
        time.sleep(60)

# Launch the port scanning service
def start_service():
    print("Initializing port scan service...")
    main()

start_service() 
