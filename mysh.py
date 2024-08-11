import json
import os
import re
import signal
import sys

import parsing



# DO NOT REMOVE THIS FUNCTION!
# This function is required in order to correctly switch the terminal foreground group to
# that of a child process.
def setup_signals() -> None:
    """
    Setup signals required by this program.
    """
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)


def main() -> None:
    # DO NOT REMOVE THIS FUNCTION CALL!
    setup_signals()


    # Start your code here!

    os.environ["PWD"] = os.getcwd()

    try:
        path = os.environ['MYSHDOTDIR']
    except KeyError:
        path = os.environ['HOME']


    path += '/.myshrc'
    try:
        with open(path, 'r') as init_file:
            lines = json.load(init_file)

        for variable_name, value in lines.items():
            if not re.match(r'^[A-Za-z0-9_]+$', variable_name):
                sys.stderr.write(f"mysh: .myshrc: {variable_name}: invalid characters for variable name\n")
                continue
            if not re.match(r'[A-Za-z]', variable_name):
                sys.stderr.write(f"mysh: .myshrc: {variable_name}: not a string\n")
                continue
            os.environ[variable_name] = value

    except json.decoder.JSONDecodeError:
        sys.stderr.write("mysh: invalid JSON format for .myshrc\n")

    except FileNotFoundError:
        pass


    while True:


        try:
            prompt = input(">> ")
        except EOFError:
            sys.stdout.write("\n")
            break



        split = parsing.split_by_pipe_op(prompt)

        parsed = parsing.format(split)


        if any(len(sublist) == 0 for sublist in parsed):
            sys.stderr.write("mysh: syntax error: expected command after pipe\n")
            continue



        if parsing.run_commands(parsed):
            continue

if __name__ == "__main__":
    main()
