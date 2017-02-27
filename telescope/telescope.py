# This file provides an abstraction around the control commands for the telescope; no shell commands
# should be run except through the Telescope interface provided below

import typing
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
            # create an SSH client
            self.ssh = paramiko.SSHClient()

            # load host keys for verified connection
            self.ssh.load_system_host_keys()

            # connect!
            try:
                self.ssh.connect('mail.stoneedgevineyard.com', username='rprechelt')
            except AuthenticationException: # unable to authenticate
                self.log('Unable to authenticate connection to aster', color='red')
                # TODO: Email admin
            except: # something else went wrong
                self.log('sirius has encountered an unknown error in connecting to aster',
                         color='red')

    def __del__(self):
        """ This function is called just prior to the object being garbage
        collected - this only happens when something has gone wrong, so we
        shutdown the telescope, and then disconnect from aster.
        """
        # closedown the telescope
        if self.dryrun is False:
            self.ssh.exec_command("closedown")
            # disconnect
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
                                        "&& track on")
            if result == True: # everything was good
                return True
            else: # one of the commands failed
                # should we handle this error more seriously
                return False
        else:
            return False


    def close_down(self) -> bool:
        """ Closes the current session, closes the dome, and logs out. Returns
        True if successful in closing down, False otherwise.
        """
        return self.run_command("closedown && logout")

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
        alt = re.search(r"(?<=alt=).*?(?= )", status).group(0)
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
        it is less than 40% cloudy. Returns true if the weather is OK to open up,
        false otherwise.
        """

        if self.dryrun is False:
            # check sun has set
            if self.get_sun_alt() >= -15.0:
                self.close_dome()
                return False

            # check that it isn't raining
            if get_rain != 0:
                self.close_dome()
                return False

            # check cloud cover is below 40%
            if get_cloud >= 0.40:
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
            # Check if we're using coordinates or target names
            cmd = "catalog "+target+" | dopoint"
            result = self.run_command(cmd)
            return result

        return False

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


    def current_filter(self) -> str:
        """ Returns the name of the currently enabled filter, or
        clear otherwise.
        """
        return self.run_command("pfilter")


    def change_filter(self, name: str) -> str:
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


    def run_command(self, command: str) -> str:
        """ Executes a shell command either locally, or remotely via ssh.
        Returns the byte string representing the captured STDOUT
        """
        ## THIS NEEDS TO APPEND A WHITESPACE TO EVERY STRING
        ## THIS NEEDS TO RETURN THE OUTPUT STRING AS SECOND RETURN ARGUMENT
        self.log("Executing: {}".format(command), color="magenta")
        if not self.dryrun:
            try:
                stdin, stdout, stderr = self.ssh.exec_command(command)
                return True, sys.stdout.readlines()[0]+' '
            except:
                self.log("Failed while executing {}".format(command), color="red")
                self.log("{}".format(sys.stderr.readlines()), color="red")
                self.log("Please manually close the dome by running"
                         " `closedown` and `logout`.", color="red")
                exit(1)

    def copy_files(self, remote: str, local: str) -> bool:
        """ Copy the file located at path "remote" on the telescope
        server to path "local" on the queue server.
        """

        # start sftp
        sftp = self.ssh.open_sftp()

        # transfer file from remote to local
        try:
            sftp.get(remote, local)
        except:
            self.log("Unable to transfer file from telescope controller.", color="red")
            print(sys.exc_info())
            return False

        # close sftp
        sftp.close()

        return True


