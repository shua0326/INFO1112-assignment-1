import json
import os
import re
import signal
import sys
import shlex
from glob import escape

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
            if type(variable_name) != str or type(value) != str:
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
    try:
        os.environ['PROMPT']
    except KeyError:
        os.environ['PROMPT'] = '>> '
    try:
        os.environ['PWD']
    except KeyError:
        os.environ['PWD'] = os.getcwd()
    try:
        os.environ['MYSH_VERSION']
    except KeyError:
        os.environ['MYSH_VERSION'] = '1.0'

def split_preserve_quotes(s):
    # Regular expression to match words or quoted substrings
    pattern = re.compile(r'\"[^\"]*\"|\'[^\']*\'|\S+')
    return pattern.findall(s)

def process_commands(cmds_split_by_pipes):
    quotes_escaped_cmds = []
    for j in cmds_split_by_pipes:
        temp_split = []
        j = j.strip()
        split_list = split_preserve_quotes(j)
        for i in split_list:
            if i.startswith('"') and i.endswith('"'):
                i = '\\"' + i[1:-1] + '\\"'
            elif i.startswith("'") and i.endswith("'"):
                i = "\\'" + i[1:-1] + "\\'"
            temp_split.append(i)
        quotes_escaped_cmds.append(' '.join(temp_split))
    return quotes_escaped_cmds


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


        quotes_escaped_cmds = process_commands(cmds_split_by_pipes)

        print(quotes_escaped_cmds)


        escaped_cmds = []

        for i in quotes_escaped_cmds:
            if re.search(r'\\\$\{.*?\}', i) and "'" not in i and '"' not in i:
                escaped_cmd = i.replace('\\', "'\\").replace('}', "}'")
                escaped_cmds.append(escaped_cmd)
            else:
                escaped_cmds.append(i)

        print(escaped_cmds)

        parsed_commands = split_and_format_arguments(escaped_cmds)

        print(parsed_commands)


        if any(len(sublist) == 0 for sublist in parsed_commands):
            sys.stderr.write("mysh: syntax error: expected command after pipe\n")
            continue

        if run_commands(parsed_commands):
            continue


if __name__ == "__main__":
    main()
