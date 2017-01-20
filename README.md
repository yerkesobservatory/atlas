## Stone Edge Observatory

*NB: If you are simply trying to use the Stone Edge telescope, you have come to the wrong place. Head over to [Stone Edge Observatory](http://www.stoneedgeobservatory.com) and sign in using your credentials*

*If you are here to develop or extend the Stone Edge Observatory code base, then continue!*

#### Setting up the environment
To setup a copy of the production environment on your local machine, you will need a few dependencies. 

If you are running on OS X with Homebrew, 

    # install python 3
    brew install python3

    # install git (if you don't already have it)
    brew install git

    # install the mosquitto message broker
    brew install mosquitto

If you don't have Homebrew, go and install [it](http://brew.sh/) and then repeat the above. If you are running on something else, all of the above should be already installed, or available in your distro's package manager. 

Once you have the software tools, start by cloning the repo:

	# via https
	git clone https://github.com/yerkesobservatory/seo.git 

	# OR via ssh
    git clone git@github.com:yerkesobservatory.com/seo
    
    
Change to the directory you just cloned, and create a new python virtual environment called `env`

    # change to seo directory
    cd seo
    
    # create a new Python virtual environment
    pyvenv env
    
    # load virtual environment
    source env/bin/activate
    
Once this is successful, we can populate the virtual environment with the required packages:

    # load packages
    pip3 install -r requirements.txt
    
Your terminal is now running a complete copy of the production environment; when you are done working on the project for the day, run `deactivate` to exit from the virtual environment. When you wish to start working again, all you need to run is `source env/bin/activate`. 
    
*You're all set! - start developing!*


#### Project Layout

There are several independent modules necessary for the operation of this system; they are each contained within their own folder in the repository. 

* `web/` : This contains the complete web interface for controlling and working with the Stone Edge Observatory telescope; this is the only public facing component. This is a Python Flask application; see the [README](https://github.com/yerkesobservatory/seo/web/) for more information
* `queue/` : This contains the backend control server for managing and scheduling the queue. These is only accessed *via* the web app. See the [README](https://github.com/yerkesobservatory/seo/queue/)
* `pipeline` : This is the image reduction pipeline that is run on SEO images that are captured by the telescope. See the [README](https://github.com/yerkesobservatory/seo/pipeline/)
* `queue/` : This contains the backend control servers and interfaces for controlling and communicating with the telescope. These are only used by the web app and the queue to control and query the telescope. See the [README](https://github.com/yerkesobservatory/seo/telescope/)



    
