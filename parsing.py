"""
Module to handle parsing for the shell.
"""
import os
import re
import sys

# You are free to add functions or modify this module as you please.

_PIPE_REGEX_PATTERN = re.compile(
    # Match escaped double quotes
    r"\\\""
    # OR match escaped single quotes
    r"|\\'"
    # OR match strings in double quotes (escaped double quotes inside other quotes are OK)
    r"|\"(?:\\\"|[^\"])*\""
    # OR match strings in single quotes (escaped single quotes inside other quotes are OK)
    r"|'(?:\\'|[^'])*'"
    # OTHERWISE: match the pipe operator, and make a capture group for this
    r"|(\|)"
)
"""
Regex pattern which will perform multiple matches for escaped quotes or quoted strings,
but only contain a capture group for an unquoted pipe operator ('|').

Original regex credit to zx81 on Stack Overflow (https://stackoverflow.com/a/23667311).
"""


def split_by_pipe_op(cmd_str: str) -> list[str]:
    """
    Split a string by an unquoted pipe operator ('|').

    The logic for this function was derived from 
    https://www.rexegg.com/regex-best-trick.php#notarzan.

    >>> split_by_pipe_op("a | b")
    ['a ', ' b']
    >>> split_by_pipe_op("a | b|c")
    ['a ', ' b', 'c']
    >>> split_by_pipe_op("'a | b'")
    ["'a | b'"]
    >>> split_by_pipe_op("a '|' b")
    ["a '|' b"]
    >>> split_by_pipe_op(r"a | b 'c|d'| ef\\"|\\" g")
    ['a ', " b 'c|d'", ' ef\\\\"', '\\\\" g']
    >>> split_by_pipe_op("a|b '| c' | ")
    ['a', "b '| c' ", ' ']

    Args:
        cmd_str: The command string we wish to split on the unquoted pipe operator ('|').

    Returns:
        A list of strings that was split on the unquoted pipe operator.
    """
    # If you'd like, you're free to modify this function as you need.

    # Indexes which we will split the string by
    split_str_indexes = []

    for match in _PIPE_REGEX_PATTERN.finditer(cmd_str):
        if match.group(1) is not None:
            # A group exists - which is only for the last alternative
            # All other alternatives have non-capture groups, meaning they will have
            # `group(1)` return `None`
            split_str_indexes.append(match.start())

    if not split_str_indexes:
        # Nothing to split
        return [cmd_str]

    # Now, we actually split the string by the pipe operator (identified at indexes in
    # `split_str_indexes`)
    split_str = []
    prev_index = 0
    for next_index in split_str_indexes:
        # Slice string
        cmd_str_slice = cmd_str[prev_index:next_index]
        split_str.append(cmd_str_slice)

        # Update index
        prev_index = next_index + 1

    cmd_str_slice = cmd_str[prev_index:]
    split_str.append(cmd_str_slice)

    # Return string list
    return split_str

def run_exec(command):
    if re.search(r'[/]', command[0]):
        filename = re.sub(r'^./', '', command[0])
        path = os.environ['PWD']
        if os.path.isdir(path + '/' + filename):
            sys.stderr.write('mysh: ' + filename + ' is a directory\n')
        elif not os.path.exists(path + '/' + filename):
            sys.stderr.write('mysh: no such file or directory: ' + filename + '\n')
        elif not os.access(path + '/' + filename, os.X_OK):
            sys.stderr.write('mysh: permission denied: ' + filename + '\n')
        else:
            os.execv(path + '/' + filename)

    return

def run_built_in(command_line):
    for i in command_line:
        match_built_in(i)
    return True

def match_built_in(command):


    match command[0]:
        case "var":
            var(command)
            return

        case "pwd":
            pwd(command)
            return

        case "cd":
            cd(command)
            return

        case "which":
            which(command)
            return

        case "exit":
            pass

        case _:
            run_exec(command)
            pass

def var(var_command):


    # Check for the -s flag
    if var_command[1][0] == '-':
        if var_command[1] != '-s':
            error = re.sub(r's', '', var_command[1])
            if error:
                sys.stderr.write("var: invalid option " + error + "\n")

            return
        var_command.remove('-s')
        var_command.remove('var')
        if len(var_command) != 2:
            sys.stderr.write("var: expected 2 arguments, got " + str(len(var_command)) + "\n")
            return
        var_name = var_command[0]
        var_value = ' '.join(var_command[1:]) #needs to run the command given and obtain the output
    else:
        var_command.remove('var')
        if len(var_command) != 2:
            sys.stderr.write("var: expected 2 arguments, got " + str(len(var_command)) + "\n")

            return
        var_name, var_value = var_command

    # Validate variable name
    if not re.match(r'^[A-Za-z0-9_]+$', var_name):
        sys.stderr.write(f"var: invalid characters for variable {var_name}\n")

        return

    # Set the environment variable
    os.environ[var_name] = var_value

def pwd(command):
    if len(command) != 1:
        if command[1] == '-P':
            print(os.path.realpath(os.environ['PWD']))
            return
        else:
            if command[1][0] == '-':
                sys.stderr.write("pwd: invalid option: " + command[1] + "\n")
            else:
                sys.stderr.write("pwd: not expecting any arguments\n")
            return
    else:
        print(os.environ['PWD'])

def cd(command):
    print(os.environ['PATH'])
    if len(command) > 2:
        sys.stderr.write("cd: too many arguments\n")
        return
    if len(command) == 1:
        os.environ['PWD'] = os.environ['home_dir']
        return
    path = command[1]
    if os.path.isabs(path):
        abspath = path
    else:
        abspath = os.path.join(os.environ['PWD'], path)
    if not os.path.exists(abspath):
        sys.stderr.write('cd: no such file or directory: ' + abspath + '\n')
        return
    elif not os.path.isdir(abspath):
        sys.stderr.write('cd: not a directory: ' + abspath + '\n')
        return
    elif not os.access(abspath, os.X_OK):
        sys.stderr.write('cd: permission denied: ' + abspath + '\n')
        return
    else:
        os.environ['PWD'] = abspath
        return

def which(command):

    built_in_commands = ['var', 'pwd', 'cd', 'which', 'exit']

    if len(command) < 2:
        sys.stderr.write('usage: which command ...\n')
        return

    if command[1] in built_in_commands:
        sys.stdout.write(command[1] + ': shell built-in command\n')
    elif re.search(r'bin', os.environ['PATH']):
        command_path = os.environ['PATH']
        path_command = re.sub(r'[^:.*appleinternal$]', '', command_path)
        sys.stdout.write(path_command + '\n')
    else:
        sys.stdout.write(command[1] + ' not found\n')
