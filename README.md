scalrr
======

resolution reduction code.
This runs as a web app powered by Python using Flask. It currently
doesn't run on the web, I'm working on that.

***How to run scalrr***
scalrr consists of 2 python scripts:
scalrr_front.py
scalrr_back.py

They are meant to be run the front and back-ends, respectively.
Both need to be running at the same time for scalrr to function.
To run them, simply run "python scalrr_front.py" or
"python scalrr_back.py" on the command line. sclarr_back.py is meant
to be run on the machine hosting the database (modis in our case).
However, scalrr_back.py should be able to access remote databases
with minimal modification (just changing the database access
information in scalrr_back.py).

There are some necessary python libraries for scalrr_front.py
and scalrr_back.py:

scalrr_front.py: Flask,simplejson, (mod-wsgi python library
    required to run scalrr online).
scalrr_back.py:scidbapi (installed by general SciDB installation),
    simplejson

You can install these libraries globally on your machine, or you can
use virtualenv to install them in a virtual environment.

I recommend installing pip for easy installation of python libraries.
You can typically do "sudo pip install [python library]" and pip will
do the rest.

***How to interact with scalrr locally***
After getting scalrr_front.py and scalrr_back.py running, go to
"http://localhost:5000/index2.html" in your web browser
of choice (I did almost all the development using only firefox, so I
would recommend using that for best results).

NOTE: scalrr works fine when being accessed by separate browsers.
However, if you have 2 windows/tabs running scalrr within the same
browser, scalrr will break. Flask sessions are maintained per browser
(same cookie is used for the windows/tabs)

***How to make changes to scalrr and test***
Just stop whichever part of the system you are modifying (backend
or frontend, ctrl-c on the command line is fine). Make your changes,
and then re-start that part of the system. scalrr_front.py and
scalrr_back.py run independently of each other so stopping both of
them is not necessary. However, if they are communicating when you
kill one of them, you could potentially crash the other (I haven't
put in code to catch exceptions yet).
