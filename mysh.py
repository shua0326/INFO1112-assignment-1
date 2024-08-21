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


def process_command(cmd):
    pattern = r'([\'"])\$\{.*?\}\1'
    def replace_quotes(match):
        inner_content = match.group()[1:-1]  # Remove the original quotes
        return "'\"" + inner_content + "\"'"
    escaped_cmd = re.sub(pattern, replace_quotes, cmd)
    return escaped_cmd


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

        escaped_cmds = []

        for i in cmds_split_by_pipes:
            if re.search(r'\\\$\{.*?\}', i) and "'" not in i and '"' not in i:
                escaped_cmd = i.replace('\\', "'\\").replace('}', "}'")
                escaped_cmds.append(escaped_cmd)
            elif re.search(r'[\'"]\${.*?}[\'"]', i):
                escaped_cmd = process_command(i)
                escaped_cmds.append(escaped_cmd)
            else:
                escaped_cmds.append(i)

        parsed_commands = split_and_format_arguments(escaped_cmds)

        if any(len(sublist) == 0 for sublist in parsed_commands):
            sys.stderr.write("mysh: syntax error: expected command after pipe\n")
            continue

        if run_commands(parsed_commands):
            continue


if __name__ == "__main__":
    main()
