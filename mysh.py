import json
import os
import re
import signal
import sys

from parsing import split_by_pipe_op, split_and_format_arguments, run_commands


# DO NOT REMOVE THIS FUNCTION!
# This function is required in order to correctly switch the terminal foreground group to
# that of a child process.
def setup_signals() -> None:
    """
    Setup signals required by this program.
    """
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)


def initialise_shell() -> None:
    os.environ["PWD"] = os.getcwd()
    os.environ['PROMPT'] = '>> '
    os.environ['MYSH_VERSION'] = '1.0'

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
            if re.search(r'[0-9]', variable_name) or type(variable_name) == int:
                sys.stderr.write(f"mysh: .myshrc: {variable_name}: not a string\n")
                continue
            os.environ[variable_name] = value

    except json.decoder.JSONDecodeError:
        sys.stderr.write("mysh: invalid JSON format for .myshrc\n")

    except FileNotFoundError:
        pass

    try:
        os.environ['PATH']
    except KeyError:
        os.environ['PATH'] = os.defpath


def main() -> None:
    # DO NOT REMOVE THIS FUNCTION CALL!
    setup_signals()

    # Start your code here!

    initialise_shell()

    while True:

        try:
            user_input = input(os.environ['PROMPT'])
        except EOFError:
            sys.stdout.write("\n")
            break

        cmds_split_by_pipes = split_by_pipe_op(user_input)

        parsed_commands = split_and_format_arguments(cmds_split_by_pipes)

        if any(len(sublist) == 0 for sublist in parsed_commands):
            sys.stderr.write("mysh: syntax error: expected command after pipe\n")
            continue

        if run_commands(parsed_commands):
            continue


if __name__ == "__main__":
    main()
