from . import server
from . import ssh_telescope
from . import remote_telescope

Telescope = remote_telescope.RemoteTelescope
SSHTelescope = ssh_telescope.SSHTelescope
RemoteTelescope = remote_telescope.RemoteTelescope
TelescopeServer = server.TelescopeServer
