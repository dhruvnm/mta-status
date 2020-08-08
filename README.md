# mta-status
A small API that monitors the status of MTA subway lines.

## Install
You will need [Python3](https://www.python.org/downloads/)<br>
Dependencies you may need to install:<br>
Flask: `pip install flask`<br>
Flask APScheduler: `pip install Flask-APScheduler`<br>

## Run
To run the app, simply run `python app.py` in the same folder as the file<br>
The service will run on `localhost:5000`. The status of each line will be updated every minute.

## Routes
### Home
The home page is at `localhost:5000`.<br>
This page just gives simple instructions about the available routes.

### Status
To see the current status of a line, navigate to `localhost:5000/status/<line>`<br>
Note requesting the status of a line that doesn't exist will simply tell you the line is not delayed.<br>
The parameter `<line>` is case insensitive.

### Uptime
To see what percentage of time a line is not delayed, navigate to `localhost:5000/uptime/<line>`<br>
Note requesting the uptime of a line that doesn't exist will simply tell you the line is not delayed 100% of the time.<br>
The parameter `<line>` is case insensitive.
