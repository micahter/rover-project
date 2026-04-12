"""this code works with raspberry pi when is connected through the USB cable"""

import paramiko

client = paramiko.SSHClient()
#client.load_system_host_keys() # Load known host keys from ~/.ssh/known_hosts
# Or set a policy for handling unknown host keys
# client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# ssh = paramiko.SSHClient()
# ssh.connect(server, username=username, password=password)
# ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)

try:
    client.connect('136.183.81.59', port=22, username='pi', password='pi') # need to adjust IP address
    print("ok")
    # Or using an SSH key:
    # client.connect('your_remote_host', username='your_username', key_filename='/path/to/your/private_key')
    ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command("python3 testclean.py") #python3 testclean.py
    output = ssh_stdout.read().decode('utf-8')
    error = ssh_stderr.read().decode('utf-8')
    if error:
        print("--- Command Error ---")
        print(error)        
    if output:
        print("--- Command Output ---")
        print(output)
except paramiko.AuthenticationException:
    print("Authentication failed, please verify your credentials.")
    exit()
except paramiko.SSHException as e:
    print(f"Could not establish SSH connection: {e}")
    exit()
