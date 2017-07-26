from . import server
from . import ssh_telescope
from . import remote_telescope

def Telescope(username: str, host: str, method: str = 'remote'):
    """ A wrapper around SSHTelescope and RemoteTelescope classes. 
    """
    if method == 'remote':
        return remote_telescope.RemoteTelescope(username, host)
    elif method == 'ssh':
        return ssh_telescope.SSHTelescope()
    else:
        print("Unknown telescope type")
        
SSHTelescope = ssh_telescope.SSHTelescope
RemoteTelescope = remote_telescope.RemoteTelescope
TelescopeServer = server.TelescopeServer
