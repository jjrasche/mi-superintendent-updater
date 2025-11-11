from contextlib import contextmanager
from sshtunnel import SSHTunnelForwarder
from config import SSH_HOST, SSH_REMOTE_PORT, SSH_LOCAL_PORT, SSH_USERNAME, SSH_KEY_PATH

@contextmanager
def ssh_tunnel():
    """
    Context manager for SSH tunnel to remote LLM server.

    Creates tunnel from localhost:SSH_LOCAL_PORT -> SSH_HOST:SSH_REMOTE_PORT

    Usage:
        with ssh_tunnel() as local_url:
            # Make API calls to local_url
            response = requests.post(local_url, ...)

    Configuration via .env:
        SSH_TUNNEL_ENABLED=true
        SSH_HOST=jrasche-ai
        SSH_REMOTE_PORT=8000
        SSH_LOCAL_PORT=8000
        SSH_USERNAME=your_username  # Optional if using SSH config
        SSH_KEY_PATH=/path/to/key   # Optional if using SSH config
    """

    # Build SSH tunnel kwargs
    tunnel_kwargs = {
        'ssh_address_or_host': (SSH_HOST, 22),
        'remote_bind_address': ('localhost', SSH_REMOTE_PORT),
        'local_bind_address': ('localhost', SSH_LOCAL_PORT),
    }

    # Add optional auth params if provided
    if SSH_USERNAME:
        tunnel_kwargs['ssh_username'] = SSH_USERNAME
    if SSH_KEY_PATH:
        tunnel_kwargs['ssh_pkey'] = SSH_KEY_PATH

    # Create and start tunnel
    tunnel = SSHTunnelForwarder(**tunnel_kwargs)

    try:
        tunnel.start()
        local_url = f'http://localhost:{tunnel.local_bind_port}/api/generate'
        print(f"[SSH TUNNEL] Connected: localhost:{tunnel.local_bind_port} -> {SSH_HOST}:{SSH_REMOTE_PORT}")
        yield local_url
    finally:
        tunnel.stop()
        print(f"[SSH TUNNEL] Closed")
