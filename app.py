import requests
import xmltodict
from collections import defaultdict
import re
from datetime import datetime
from flask_apscheduler import APScheduler
from flask import Flask

class Config(object):
    SCHEDULER_API_ENABLED = True

app = Flask(__name__)
app.config.from_object(Config())
scheduler = APScheduler()

# This is the MTA api endpoint for subway service status
# Their website says it's refreshed every minute but doesn't always seem to be the case
URL = "http://web.mta.info/status/ServiceStatusSubway.xml"

# Current status of every line
is_delayed = dict()

# Total time in seconds a line has been delayed
total_time_delayed = defaultdict(lambda: 0)

# The time at which a line was marked as delayed
time_delayed_at = dict()

# The time at which data is initialized
start_time = None

# Set of valid subway lines
valid_lines = {'1', '2', '3', '4', '5', '6', '7', 'A', 'C', 'E', 'B', 'D', 'F', 'M', 'G', 'J', 'Z', 'L', 'N', 'Q', 'R', 'W', 'S', 'SR', 'SF', 'SIR'}

def initialize_app():
    """Initializes the app with the current state of all lines"""

    for line in valid_lines:
        is_delayed[line] = False

    # Get and parse the data into a dictionary
    response = requests.get(URL)
    tree = response.content
    data = xmltodict.parse(tree)

    # Set the time data is initialized
    global start_time
    start_time = datetime.now()

    # Loop through all situation elements
    for situation in data['Siri']['ServiceDelivery']['SituationExchangeDelivery']['Situations']['PtSituationElement']:
        # We only care about delays. Everything else will be considered "not delayed"
        if situation['ReasonName'] == 'Delays':
            # Parse out the line number/letter
            match = re.search(r'\[(\w+)\]', situation['LongDescription'])

            # Edge cases in the response
            if match:
                if match.group(1) == 'H':
                    line = 'SR'
                elif match.group(1) == 'FS':
                    line = 'SF'
                else:
                    line = match.group(1)

                
                # Set the line as delayed and store its delay time
                is_delayed[line] = True
                time_delayed_at[line] = start_time
                print(f"[{start_time}] Line {line} is experiencing delays")

@scheduler.task('interval', id='check_for_updates', seconds=60)
def check_for_updates():
    """Checks for updates to line status every minute"""

    check_time = datetime.now()
    print(f"[{check_time}] Checking for updates...")

    # Get and parse the data into a dictionary
    response = requests.get(URL)
    tree = response.content
    data = xmltodict.parse(tree)

    # This set will store which lines are delayed right now
    curr_delayed = set()

    # Loop through all situation elements
    for situation in data['Siri']['ServiceDelivery']['SituationExchangeDelivery']['Situations']['PtSituationElement']:
        # We only care about delays. Everything else will be considered "not delayed"
        if situation['ReasonName'] == 'Delays':
            # Parse out the line number/letter
            match = re.search(r'\[(\w+)\]', situation['LongDescription'])

            # Edge cases in the response
            if match:
                if match.group(1) == 'H':
                    line = 'SR'
                elif match.group(1) == 'FS':
                    line = 'SF'
                else:
                    line = match.group(1)


                curr_delayed.add(line)

    # Iterate through all lines 
    for line, delayed in is_delayed.items():
        # If the line just switched to delayed, switch status and store the new delay time
        if not delayed and line in curr_delayed:
            is_delayed[line] = True
            time_delayed_at[line] = datetime.now()
            print(f"[{check_time}] Line {line} is experiencing delays")

        # If the line just switched to not delayed, switch status and update total time delayed
        elif delayed and line not in curr_delayed:
            is_delayed[line] = False
            time_delayed = datetime.now() - time_delayed_at[line]
            total_time_delayed[line] += time_delayed.total_seconds()
            print(f"[{check_time}] Line {line} is now recovered")


@app.route("/")
def home():
    """Simple home page to return basic instructions"""

    return """Welcome to Dhruv's MTA service checker! <br>
    Navigate to /status/&ltline&gt to see the current status of a line. <br>
    Navigate to /uptime/&ltline&gt to see the percentage of time the line isn't delayed. <br>
    The console will print whenever the status of a line changes (updates every minute)."""

@app.route("/status/<line>")
def status(line):
    """Check the current status of a line"""

    # Allows for case insensitive queries
    line = line.upper()

    # Validate parameter
    if line not in valid_lines:
        return "Invalid line provided"

    if is_delayed[line]:
        return f"Line {line} is delayed"
    else:
        return f"Line {line} is not delayed"

@app.route("/uptime/<line>")
def uptime(line):
    """Check the percentage of time a line is not delayed"""

    # Allows for case insensitive queries
    line = line.upper()

    # Validate parameter
    if line not in valid_lines:
        return "Invalid line provided"

    curr_time = datetime.now()

    # In case a line is currently delayed we need to add the delta from the time it was delayed
    if is_delayed[line]:
        delta = curr_time - time_delayed_at[line]
        delta_sec = delta.total_seconds()
    else:
        delta_sec = 0

    # Calculate the uptime percentage
    total_time = curr_time - start_time
    percentage = 100 * (1 - (total_time_delayed[line] + delta_sec) / total_time.total_seconds())

    return f"Line {line} is not delayed {percentage}% of the time"

if __name__ == '__main__':
    # Initialize and run app
    initialize_app()
    scheduler.init_app(app)
    scheduler.start()
    app.run()
