"""
Author: Cristian Di Pietrantonio.

"""
from bs4 import BeautifulSoup
from constraint import *
import json
import requests
import datetime



def parse_doodle(pollID):
    JSON = requests.get("https://doodle.com/api/v2.0/polls/" + pollID).content.decode('utf-8')
    JSON = json.loads(JSON)

    options = [datetime.datetime.fromtimestamp(x['start']/1000) for x in JSON['options']]
    calendar = dict([(i, list()) for i in range(len(options))])
    participants = dict()
    for participant in JSON['participants']:
        pID = participant['id']
        pName = participant['name']
        participants[pID] = pName

        for i, pref in enumerate(participant['preferences']):
            if pref == 1:
                calendar[i].append(pID)
        
    for k in calendar:
        if len(calendar[k]) == 0:
            calendar[k].append(-1) # empty shift
    
    participants[-1] = "<vuoto>"

    return participants, options, calendar



def format_date(date):
    """
    Return a unique string representation for the date, to be used as variable name.
    """
    return "{}/{}/{} {}:{}".format(date.day, date.month, date.year, date.hour, date.minute)



def format_solution(solution, participants, options):
    text = "Turni:\n_______\n\n"
    for i, option in enumerate(options):
        text += "{}   -->  {}\n".format(format_date(option), participants[solution[i]])
    return text



if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: shifts.py <doodle-poll-id>")
        exit(1)
    
    pollID = sys.argv[1]
    participants, options, calendar = parse_doodle(pollID)
    # create CSP problem
    turni = Problem()

    for k in calendar:
        turni.addVariable(k, calendar[k])
    
    empty_shift = lambda x: x[0] == -1

    # Constraint 1 - maximum one shift per person per day
    slotsInSameDay = list() if empty_shift(calendar[0]) else [0]
    for i in range(1, len(options)):
        if empty_shift(calendar[i]):
            continue
        elif options[i].day == options[i-1].day:
            slotsInSameDay.append(i)
        elif len(slotsInSameDay) > 1:
            # add all different constraints
            turni.addConstraint(AllDifferentConstraint(), slotsInSameDay)
            slotsInSameDay = [i]

    if len(slotsInSameDay) > 1:
        # add all different constraints
        turni.addConstraint(AllDifferentConstraint(), slotsInSameDay)
        slotsInSameDay = [i]

    solution = turni.getSolution()
    textSol = format_solution(solution, participants, options)
    print(textSol)


