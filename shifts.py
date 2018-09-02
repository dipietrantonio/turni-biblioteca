"""
Author: Cristian Di Pietrantonio.

"""
import json
import requests
import datetime
import sys
from constraint import *



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



def ask_for_min_shifts(participants):
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
    def __init__(self, valueToFrequency):
        self._valueToFrequency = valueToFrequency
        self._subtr = dict()
        for k in valueToFrequency:
            self._subtr[k] = sum([valueToFrequency[g] for g in valueToFrequency if g != k])
        self._myFreq = dict([(i, 0) for i in self._valueToFrequency])

    def __call__(self, variables, domains, assignments, forwardcheck=False):
        for i in self._myFreq:
            self._myFreq[i] = 0
        missing = False
        M = len(variables)
        for variable in variables:
            if variable in assignments:
                self._myFreq[assignments[variable]] += 1
            else:
                missing = True
        if missing:
            for k in self._myFreq:
                if self._myFreq[k] > M - self._subtr[k]:
                    return False
            return True
        for k in self._myFreq:
            if self._myFreq[k] < self._valueToFrequency[k]:
                return False
        return True



def solve_with_constraints_lib(participants, options, calendar, partToMinShifts):

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
        slotsInSameDay = [i]

    # Constraint 2 - each person p is assigned with at least partToMinShifts[p] shifts        
    turni.addConstraint(MinimumValueFrequency(partToMinShifts))

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