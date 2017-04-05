# This file provides an abstraction around the control commands for the telescope; no shell commands
# should be run except through the Telescope interface provided below

import typing
import socket
import re
import paramiko
import time
import sys

class Telescope(object):
    """ This class is the sole point of contact between the system and the telescope
    control server. This class is responsible for converting high-level requests
    (open_dome()) into a shell command that it remotely executes on the control
    server using paramiko.
    """

    def __init__(self, dryrun=False):
        """ This function is responsible for establishing the
        connection with aster.
        """
        self.dryrun = dryrun
        if self.dryrun is not True:
            # create a SSH transport
            self.ssh = self.connect()

            # save ssh transport
            self.transport = self.ssh.get_transport()

            # create session
            self.session = self.transport.open_session()


    def connect(self):
        """ Create a SSH connection to the telescope, 
        """
        ssh = paramiko.SSHClient()
        
        # load host keys for verified connection
        ssh.load_system_host_keys()

        # insert keys - this needs to be removed ASAP
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # connect!
        try:
            ssh.connect('mail.stoneedgevineyard.com', username='rprechelt')
            self.log('Successfully connected to the telescope control server', color='green')
        except paramiko.AuthenticationException: # unable to authenticate
            self.log('Unable to authenticate connection to aster', color='red')
            exit(1)
            # TODO: Email admin
        except: # something else went wrong
            self.log('sirius has encountered an unknown error in connecting to aster',
                     color='red')
            exit(1)

        return ssh

    def disconnect(self) -> bool:
        """ Disconnect the SSH connection to the telescope. 
        """
        self.ssh.close()

        
    def open_dome(self) -> bool:
        """ Checks that the weather is acceptable, and then opens the dome,
        if it is not already open, and  also enables tracking.
        """
        # check if dome is already open
        if self.dome_open() == True:
            return True

        # check that weather is OK to open
        if self.weather_ok() == True:
            result = self.run_command("openup nocloud "
                                        "&& tx track on")
            if result == True: # everything was good
                return True
            else: # one of the commands failed
                # should we handle this error more seriously
                return False
        else:
            return False

    def keep_open(self, time: int) -> bool:
        """ Keeps the dome open for a specified number of seconds. Assumes
        dome is already open.
        """
        try:
            result = self.run_command("keepopen maxtime={} slit".format(int(time)),
                                      timeout = 5, ignore = True)
        finally:
            return True
        

    def close_down(self) -> bool:
        """ Closes the current session, closes the dome, and logs out. Returns
        True if successful in closing down, False otherwise.
        """
        return self.run_command("closedown")
    

    def close_dome(self) -> bool:
        """ Closes the dome, but leaves the session connected. Returns
        True if successful in closing down, False otherwise.
        """
        return self.run_command("closedown")


    def get_cloud(self) -> float:
        """ Returns the current cloud cover as a float.
        """
        status = self.run_command("tx taux")
        cloud = re.search(r"(?<=cloud=).*?(?= )", status).group(0)
        return float(cloud)


    def get_dew(self) -> float:
        """ Returns the current dew value as a float.
        """
        status = self.run_command("tx taux")
        dew = re.search(r"(?<=dew=).*?(?= )", status).group(0)
        return float(dew)


    def get_rain(self) -> bool:
        """ Returns the current rain value as a bool.
        """
        status = self.run_command("tx taux")
        rain = re.search(r"(?<=rain=).*?(?= )", status).group(0)
        return int(rain)


    def get_sun_alt(self) -> float:
        """ Returns the sun's current altitude as a float.
        """
        status = self.run_command("sun")
        alt = re.search(r"(?<=alt=).*$", status).group(0)
        return float(alt)


    def get_moon_alt(self) -> float:
        """ Returns the moon's current altitude as a float.
        """
        status = self.run_command("moon")
        alt = re.search(r"(?<=alt=).*?(?= )", status).group(0)
        return float(alt)


    def get_weather(self) -> dict:
        """ Returns a dictionary containing all the available weather info.
        """
        weather = {}
        weather['rain'] = self.get_rain()
        weather['cloud'] = self.get_cloud()
        weather['dew'] = self.get_dew()
        weather['sun'] = self.get_sun_alt()
        weather['moon'] = self.get_moon_alt()
        return weather


    def weather_ok(self) -> bool:
        """ Checks whether the sun has set, there is no rain (rain=0) and that
        it is less than 30% cloudy. Returns true if the weather is OK to open up,
        false otherwise.
        """

        if self.dryrun is False:

            # check sun has set
            if self.get_sun_alt() >= -15.0:
                if self.dome_open() is True:
                    self.close_dome()
                return False

            # check that it isn't raining
            if self.get_rain() != 0:
                if self.dome_open() is True:
                    self.close_dome()
                return False

            # check cloud cover is below 35%
            if self.get_cloud() >= 0.35:
                if self.dome_open() is True:
                    self.close_dome()
                return False

        # weather is good!
        return True


    def dome_open(self) -> str:
        """ Checks whether the slit is open or closed. Returns True if open,
        False if closed.
        """
        if self.dryrun is False:
            status = self.run_command("tx slit")
            slit = re.search(r"(?<=slit=).*?(?= )", status).group(0)

            # if open, return true
            if slit == "open":
                return True
            elif slit == "closed":
                return False
        else:
            return False

        return False


    def goto_target(self, target: str) -> bool:
        """ Points the telescope at the target in question. Returns True if
        successfully (object was visible), and returns False if unable to set
        telescope (failure, object not visible).
        """
        if self.target_visible(target) == True:
            # TODO: Check if we're using coordinates or target names
            cmd = "catalog "+target+" | dopoint"
            result = self.run_command(cmd)
            return result

        return False

    
    def goto(self, ra: str, dec: str) -> bool:
        """ Points the telescope at the given ra, dec in question. Returns True if
        successfully (object was visible), and returns False if unable to set
        telescope (failure, object not visible).
        """
        if self.point_visible(ra, dec) == True:
            # TODO: Check if we're using coordinates or target names
            cmd = "tx point ra="+ra+" dec="+dec+" equinox=2000"
            result = self.run_command(cmd)
            return result

        return False

    
    def make_dir(self, name: str) -> bool:
        """ Creates a directory in the current directory with a given name. Returns
        True if successful. 
        """
        if self.dryrun is False:
            try:
                self.run_command("mkdir -p "+name)
            except:
                pass
                
        return True
    

    def target_visible(self, target: str) -> bool:
        """ Checks whether a target is visible, and whether it is > 40 degrees
        in altitude. Returns True if visible and >40, False otherwise
        """
        if self.dryrun is False:
            cmd = "catalog "+target+" | altaz"
            altaz = self.run_command(cmd)
            alt = float(re.search(r"(?<=alt=).*?(?= )", altaz).group(0))
            if alt >= 40:
                return True
        else:
            return True

        return False

    
    def point_visible(self, ra: str, dec: str) -> bool:
        """ Checks whether a given (ra, dec) is visible, and whether it is > 40 degrees
        in altitude. Returns True if visible and >40, False otherwise
        """
        if self.dryrun is False:
            cmd = ' '.join(('echo', ra, dec, '2000', '| altaz'))
            altaz = self.run_command(cmd)
            alt = float(re.search(r"(?<=alt=).*?(?= )", altaz).group(0))
            if alt >= 40:
                return True
        else:
            return True

        return False


    def current_filter(self) -> str:
        """ Returns the name of the currently enabled filter, or
        clear otherwise.
        """
        return self.run_command("pfilter")


    def change_filter(self, name: str) -> bool:
        """ Changes filter to the new specified filter. Options are:
        u, g, r, i, z, clear, h-alpha. Returns True if successful,
        False otherwise
        """
        if name == "h-alpha":
            return self.run_command("pfilter h-alpha")
        elif name == "clear":
            return self.run_command("pfilter clear")
        else:
            return self.run_command("pfilter "+name+"-band")

        return True


    def take_exposure(self, filename: str, time: int, binning: int) -> bool:
        """ Takes an exposure of length time saves it in the FITS
        file with the specified filename. Returns True if imaging
        was successful, False otherwise.
        """
        cmd = "image time="+str(time)+" bin="+str(binning)
        cmd += " outfile="+filename+".fits"
        status = self.run_command(cmd)
        self.log("Saved exposure frame to "+filename, color="cyan")
        return status


    def take_bias(self, filename: str, binning: int) -> bool:
        """ Takes a bias frame and saves it in the FITS file with the specified
        filename. Returns True if imaging was successful, False otherwise.
        """
        cmd = "image time=0.5 bin="+str(binning)+" "
        cmd += "outfile="+filename+"_bias.fits"
        status = self.run_command(cmd)
        self.log("Saved bias frame to "+filename, color="cyan")
        return status


    def take_dark(self, filename: str, time: int, binning: int) -> bool:
        """ Takes an dark exposure of length self.exposure_time saves it in the
        FITS file with the specified filename. Returns True if imaging
        was successful, False otherwise.
        """
        cmd = "image time="+str(time)+" bin="+str(binning)+" dark "
        cmd += "outfile="+filename+"_dark.fits"
        status = self.run_command(cmd)
        self.log("Saved dark frame to "+filename, color="cyan")
        return status


    def enable_tracking(self) -> bool:
        return self.run_command("tx track on")

    def focus(self) -> bool:
        # focusing routine?
        pass

    def enable_flats(self) -> bool:
        # run tin?
        pass

    def offset(self, ra: float, dec: float) -> bool:
        """ Offset the telescope by `ra` degrees, and 
        `dec` degrees. 
        """
        if not self.dryrun:
            cmd = 'tx offset ra={} dec={}'.format(float(ra), float(dec))
            result = self.run_command(cmd)
            if result == True: # everything was good
                return True
            else:
                return False
            

    def log(self, msg: str, color: str = "white") -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {"red":"31", "green":"32", "blue":"34", "cyan":"36",
                  "white":"37", "yellow":"33", "magenta":"34"}
        logtime = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        log = "\033[1;"+colors[color]+"m"+logtime+" TELESCOPE: "+msg+"\033[0m"
        print(log)
        return True


    def run_command(self, command: str, timeout: int = 600, ignore: bool = False) -> str:
        """ Executes a shell command either locally, or remotely via ssh.
        Returns the byte string representing the captured STDOUT
        """
        self.log("Executing: {}".format(command), color="magenta")
        if not self.dryrun:

            # make sure the connection hasn't timed out due to sleep
            # if it has, reconnect
            try:
                self.ssh.exec_command('who')
            except socket.error as e:
                self.ssh = self.connect()

            # try and execute command 5 times if it fails
            numtries = 0; exit_code = 1
            while numtries < 5 and exit_code != 0:
                try:
                    session = self.transport.open_session()
                    stdin, stdout, stderr = self.ssh.exec_command(command, timeout)
                    numtries += 1
                    result = stdout.readlines()
                    # check exit code
                    exit_code = stdout.channel.recv_exit_status()
                    session.close()
                    if exit_code != 0:
                        self.log("Command returned {}. Retrying in 3 seconds...".format(exit_code))
                        time.sleep(3)
                        continue

                    # valid result received
                    if len(result) > 0:
                        result = result[0]
                        print(result)
                        return result
                except Exception as e:
                    if ignore is True:
                        return True
                    self.log('run_command: '+str(e), color='red')
                    self.log("Failed while executing {}".format(command), color="red")
                    self.log("Please manually close the dome by running"
                             " `closedown` and `logout`.", color="red")
                    exit(1)

            return None



