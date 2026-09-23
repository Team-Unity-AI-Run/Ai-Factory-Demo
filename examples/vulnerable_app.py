"""
Deliberately vulnerable demo file — DO NOT use in production.
Used to demonstrate scripts/scan_code.py and the AI fix workflow.
"""

password = "admin123"
api_key = "sk-demo-1234567890abcdef"

def debug_login(username):
    print("Attempting login for:", username)
    return True

def run_diagnostics(user_command):
    import os
    os.system(user_command)

def unsafe_eval(expression):
    return eval(expression)
