"""
Author: Cristian Di Pietrantonio.

"""
import json
import requests
import datetime
import sys
from constraint import *



def parse_doodle(pollID):
    """
    Retrieves poll data from doodle.com given the poll identifier.
    
    Parameters:
    -----------
        - `pollID`: the poll identifier (get it from the url)
    
    Returns:
    --------
    a tuple (participants, options, calendar) where
        - `participants` is a mapping userID -> userName
        - `options` is a list of datetime objects, representing the poll options
        - `calendar` is a mapping optionIndex -> list of userID
    """
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
    Returns a string representation of `date` datetime object, for printing purposes.
    """
    return "{}/{}/{} {}:{}".format(date.day, date.month, date.year, date.hour, date.minute)



def format_solution(solution, participants, options):
    """
    Return a string representation of the solution.
    """
    text = "Shifts:\n_______\n\n"
    for i, option in enumerate(options):
        text += "{}   -->  {}\n".format(format_date(option), participants[solution[i]])
    return text



def ask_for_min_shifts(participants):
    """
    Asks the user to specify the minimum number of shifts to assign to each user.
    """
    minShifts = dict()
    for p in participants:
        if p != -1:
            n = input("Minimum shifts to assign to {}? ".format(participants[p]))
            try:
                n = int(n)
            except ValueError:
                n = ""
            if n == "" or n < 0:
                print("Error: input \"{}\" not valid.".format(n)) 
                exit(1)
            minShifts[p] = n
    return minShifts



class MinimumValueFrequency(Constraint):
    """
    This constraint models the fact that each variable value must appear at least
    with a minimum specified frequency in the solution.
    """

    
    def __init__(self, value, frequency, others):
        self._value = value
        # frequency of each value, itially 0
        self._minFreq = frequency
        self._others = others
        # the following information is used later, as optimization step.
        
    
    def __call__(self, variables, domains, assignments, forwardcheck=False):

        missing = False
        # maximum frequency is M
        freq = 0
        M = len(variables)
        for variable in variables:
            if variable in assignments:
                if assignments[variable] == self._value:
                    freq += 1
            else:
                missing = True
        # if the assignment is incomplete, maybe we can see if it can be discarded too
        if missing:
            if freq > M - self._others:
                return False
            else:
                return True
        
        if freq < self._minFreq:
            return False
        else:
            return True



def solve_with_constraints_lib(participants, options, calendar, partToMinShifts):
    """
    Formulate and solve the problem using `constraint` library

    Parameters:
    -----------
        - `participants`: mapping participantID -> participantName
        - `options`: list of datetime objects
        - `calendar`: mapping optionID -> list of participantID
        - `partToMinShifts`: mapping paricipantID -> min number of shifts to be assigned
    """
    turni = Problem(MinConflictsSolver(1000000))
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

    # Constraint 2 - each person p is assigned with at least partToMinShifts[p] shifts
    for k in partToMinShifts:
        val = partToMinShifts[k]        
        turni.addConstraint(MinimumValueFrequency(k, val, sum([partToMinShifts[g] for g in partToMinShifts if g != k])))

    solution = turni.getSolution()
    if solution is None:
        print("No solution found. Try again.")
        exit()
    textSol = format_solution(solution, participants, options)
    print(textSol)



if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: shifts.py <doodle-poll-id>")
        exit(1)
    
    pollID = sys.argv[1]
    participants, options, calendar = parse_doodle(pollID)
    # create CSP problem
    partToMinShifts = ask_for_min_shifts(participants)
    partToMinShifts[-1] = 0
    solve_with_constraints_lib(participants, options, calendar, partToMinShifts)