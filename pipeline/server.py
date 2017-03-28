import paramiko
from templates import mqtt

class PipelineServer(mqtt.MQTTServer):
    """ The PipelineServer listens for requests on the pipeline topic; messages contain a directory
    containing the location of a completed queue session; this session is then sent through the
    pipeline. 
    """

    def __init__(self, config: {str}):
        """ This function creates SSH connections to the telescope and storage server
        and then awaits a process message from the message broker. 
        """

        # MUST INIT SUPERCLASS FIRST
        super().__init__(config, "PIPELINE SERVER")

        # we first verify that we can connect to the two servers
        try:
            # connect to telescope server
            self.telescope = self.connect_to_telescope()

            # connect to storage server
            self.storage = self.connect_to_storage()

            # let's disconnect until we are ready to avoid timeouts
            self.telescope.close()
            self.storage.close()
        except Exception as e:
            self.log('Pipeline server unable to connect to servers', color='red')
            self.log('__init__: '+str(e))

        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def connect_to_telescope(self):
        """ Creates and returns an SSHClient connected to the telescope server.
        """
        return self.connect_ssh(self.config['server']['telescope']['host'],
                         self.config['server']['telescope']['username'])

    
    def connect_to_storage(self):
        """ Creates and returns an SSHClient connected to the storage server.
        """
        return self.connect_ssh(self.config['server']['storage']['host'],
                         self.config['server']['storage']['username'])

    
    def connect_ssh(self, remote, username):
        """ Creates an SSHClient, connects to 'remote', and returns the client. 
        """
        # create an SSH client
        ssh = paramiko.SSHClient()

        # load host keys for verified connection
        ssh.load_system_host_keys()
        
        # insert keys - this needs to be removed ASAP
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # connect!
        try:
            ssh.connect(remote, username=username, key_filename='/home/rprechelt/.ssh/id_rsa')
            self.log('Successfully connected to server: {}'.format(remote), color='green')
        except paramiko.AuthenticationException: # unable to authenticate
            self.log('Unable to authenticate ssh connection to {}'.format(remote), color='red')
            self.notify('Pipeline server unable to authenticate ssh connection to {}.'.format(remote))
            exit(1)
        except Exception as e: # something else went wrong
            self.log('sirius has encountered an unknown error in connecting to aster',
                     color='red')
            self.log('connect_ssh: {}'.format(str(e)))
            self.notify('Pipeline server unable to connect via ssh to {}. \n{}'.format(remote, e))
            exit(1)

        return ssh

                
    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """
        prefix = '/'+self.config['general']['shortname']+'/'
        return [prefix+'pipeline']

    
    def process_message(self, msg: {str}) -> bool:
        """ This function is given a JSON dictionary message from the broker
        and must decide how to process the message given the servers purpose. This
        is automatically called whenever a message is received
        """

        # if we get a process message
        if msg.get('type') == 'process':

            if msg.get('dir') is not None:

                # start processing of that dir
                self.start_pipeline(msg.get('dir'))
            
        return True


    def start_pipeline(self, fdir: str) -> bool:
        """ Start the processing pipeline on the raw image
        files in the directory given by 'fdir'
        """
        # until the pipeline is ready, we compress the directory
        # and copy to the storage server

        try:
            tarball = self.compress_dir(fdir)
            name = tarball.split('/')[-1]
            local_file = self.copy_remote_to_local(tarball, '/home/rprechelt/projects/seo/'+name)

            # extract the date
            date = (fdir.split('/')[-1]).split('_')
            year = date[0]; month = date[1]

            # copy the tarball to the storage server
            final_loc = '/data/public/queue/'+year+'/'+month+'/'
            self.copy_local_to_remote(local_file, final_loc)
        except Exception as e:
            self.log('start_pipeline: '+str(e))

        return True

    
    def compress_dir(self, loc: str) -> str:
        """ Compress the directory on the telescope
        server and returns the file. 
        """
        # connect to the telescope server
        self.telescope = self.connect_to_telescope()

        # calculate the tar command
        name = loc.split('/')[-1]
        cmd = 'tar czf compressed/'+name+'.tar.gz '+loc

        # compress the data
        self.telescope.exec_command(cmd)

        # return the final location
        return 'compressed/'+name+'.tar.gz'

    
    def copy_remote_to_local(self, remote: str, local: str) -> str:
        """ Copy the remote file from the telescope
        server to the local server. Returns the new location
        on the local server. 
        """

        # connect to telescope server
        self.telescope = self.connect_to_telescope()

        # create an SFTP client
        sftp = self.telescope.open_sftp()

        # try and transfer file from remote to local
        try:
            sftp.get(remote, local)
            self.log('Successfully transferred file from telescope server', color='green')
        except Exception as e:
            self.log('Unable to transfer file from telescope server', color='red')
            self.log('copy_remote_to_local: '+str(e))
            return False

        # close the sftp connection
        sftp.close()

        # close the telescope connection
        self.telescope.close()

        return local

    
    def copy_local_to_remote(self, local: str, remote: str) -> bool:
        """ Copy the file `loc` on the local server to
        'dest' on the storage server. 
        """

        # connect to storage server
        self.storage = self.connect_to_storage()

        # create a SFTP client
        sftp = self.storage.open_sftp()

        # try and transfer file from remote to local
        try:
            name = local.split('/')[-1]
            sftp.put(local, remote+'/'+name)
            self.log('Successfully transferred file to storage server', color='green')
        except Exception as e:
            self.log('Unable to transfer file to storage server', color='red')
            self.log('copy_local_to_remote: '+str(e))
            return False

        # close the sftp connection
        sftp.close()

        # close the telescope connection
        self.storage.close()

        return True

    
    def close(self):
        """ This function is called when the server receives a shutdown
        signal (Ctrl+C) or SIGINT signal from the OS. Use this to close
        down open files or connections. 
        """

        return

