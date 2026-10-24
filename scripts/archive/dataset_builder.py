import sys
import datetime

ALL_CHECKS = []

def add_check(category, dt, task, problem, solution, status, outcome, next_action, intern="Arnav Pundir"):
    ALL_CHECKS.append((category, dt, task, problem, solution, status, outcome, next_action, intern))

print("Dataset builder initialized.")
