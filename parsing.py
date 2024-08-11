"""
Module to handle parsing for the shell.
"""
import os
import re
import shlex
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

def format(commands):
    parsed = []


    for i in commands:
        s = shlex.shlex(i, posix=True)
        s.whitespace_split = True
        s.escapedquotes = "'\""
        s.quotes = "'\""
        s.escape = ''
        s.wordchars += '\\'
        try :
            parsed.append(list(s))
        except ValueError:
            sys.stderr.write("mysh: syntax error: unterminated quote\n")
            sys.stderr.flush()

    return parsed

def check_variable(command):
    checked_variables = []
    checked_variables.append(command[0])
    arguments = command[1:]
    for i in arguments:
        if re.search(r'\\\${.*?}', i):
            fixed_command = re.sub(r'[\\]', '', i)
        elif re.search(r'\${.*?}', i):
            variable = re.search(r'\${(.*?)}', i).group(1)
            if not re.match(r'^[A-Za-z0-9_]+$', variable):
                sys.stderr.write(f"mysh: syntax error: invalid characters for variable {variable}\n")
                return
            try:
                fixed_command = re.sub(r'\${' + variable + '}', os.environ[variable], i)
            except KeyError:
                fixed_command = re.sub(r'\${' + variable + '}', '', i)

        else:
            if re.search(r'^~', i):
                i = re.sub(r'~', os.environ['HOME'], i)
            fixed_command = i

        checked_variables.append(fixed_command)

    return checked_variables

def create_pipes(commands):
    num_commands = len(commands)
    pipe_fds = []

    for i in range(num_commands - 1):
        read_fd, write_fd = os.pipe()
        pipe_fds.append((read_fd, write_fd))

    return pipe_fds

def run_exec(command):

    if re.search(r'[/]', command[0]):
        filename = re.sub(r'^./', '', command[0])

        path = os.environ['PWD']

        if not os.path.exists(path + '/' + filename):

            sys.stderr.write('mysh: no such file or directory: ' + command[0] + '\n')
            return

        if os.path.isdir(path + '/' + filename):
            sys.stderr.write('mysh: ' + filename + ' is a directory\n')
            return

        if not os.access(path + '/' + filename, os.X_OK):
            sys.stderr.write('mysh: permission denied: ' + filename + '\n')
            return
    else:
        filename = re.sub(r'^./', '', command[0])
        paths = os.environ['PATH'].split(os.pathsep)
        existing_path = []
        for path in paths:
            if not os.path.exists(path + '/' + filename):
                continue
            else:
                existing_path.append(path)

        if not existing_path:
            sys.stderr.write('mysh: command not found: ' + filename + '\n')
            return

        path = existing_path[0]

        if os.path.isdir(path + '/' + filename):
            sys.stderr.write('mysh: ' + filename + ' is a directory\n')
            return

    child_pid = os.fork()
    if child_pid == 0:
        # Child process
        if len(command) == 1:
            os.execv(path + '/' + filename, [filename])
        else:
            os.execv(path + '/' + filename, command)

    else:
        # Parent process
        os.setpgid(child_pid, child_pid)
        child_pgid = os.getpgid(child_pid)
        parent_pgid = os.getpgrp()

        with open('/dev/tty') as tty:
            fd = tty.fileno()
            os.tcsetpgrp(fd, child_pgid)
            os.waitpid(child_pid, 0)
            os.tcsetpgrp(fd, parent_pgid)

    return

def pipe_command(command, newin, newout):
    pid = os.fork()
    if pid == 0:
        # Child process
        os.dup2(newin, 0)  # Replace stdin
        os.dup2(newout, 1)  # Replace stdout
        os.execvp(command[0], command)
    else:
        # parent
        os.setpgid(pid, pid)
        child_pgid = os.getpgid(pid)
        parent_pgid = os.getpgrp()

        with open('/dev/tty') as tty:
            fd = tty.fileno()
            os.tcsetpgrp(fd, child_pgid)
            os.waitpid(pid, 0)
            os.tcsetpgrp(fd, parent_pgid)
        return pid

def run_piped_command(command):
    num_commands = len(command)
    pipe_fds = []

    built_in_commands = ['var', 'pwd', 'cd', 'which', 'exit']

    for i in range(num_commands):
        read_fd, write_fd = os.pipe()
        pipe_fds.append((read_fd, write_fd))

    child_processes = []

    for i, cmd in enumerate(command):
        cmd = check_variable(cmd)

        if cmd[0] in built_in_commands:
            match_built_in(cmd)
            continue

        if i == 0:
            child_processes.append(pipe_command(cmd, pipe_fds[i][0], pipe_fds[i][1]))
        elif i == num_commands - 1:
            # Final command, execute directly
            child_processes.append(pipe_command(cmd, pipe_fds[i-1][0], 1))
            # Replace stdin with the read end of the previous pipe

        else:
            child_processes.append(pipe_command(cmd, pipe_fds[i-1][0], pipe_fds[i][1]))

        os.close(pipe_fds[i][1])


def run_command_and_capture_output(command):

    num_commands = len(command)
    pipe_fds = []
    built_in_commands = ['var', 'pwd', 'cd', 'which', 'exit']

    for i in range(num_commands):
        read_fd, write_fd = os.pipe()
        pipe_fds.append((read_fd, write_fd))

    child_processes = []

    for i, cmd in enumerate(command):

        cmd = check_variable(cmd)

        if cmd[0] in built_in_commands:
            match_built_in(cmd)
            continue

        if i == 0:
            child_processes.append(pipe_command(cmd, pipe_fds[i][0], pipe_fds[i][1]))
        else:
            child_processes.append(pipe_command(cmd, pipe_fds[i-1][0], pipe_fds[i][1]))

        os.close(pipe_fds[i][1])

    with os.fdopen(pipe_fds[i][0]) as r:
        output = r.read().strip()
        os.environ['OUTPUT'] = output
        return

def run_commands(command_line):


    if len(command_line) == 1:
        match_built_in(command_line[0])
        return True


    run_piped_command(command_line)


    return True

def match_built_in(command):

    command = check_variable(command)

    if command == None:
        return

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
            exit_cmd(command)
            return

        case _:
            run_exec(command)
            return

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
        command_str = var_command[1]


        # Split and parse the command string
        split_commands = split_by_pipe_op(command_str)
        parsed_commands = format(split_commands)


        run_command_and_capture_output(parsed_commands)

    else:
        var_command.remove('var')
        if len(var_command) != 2:
            sys.stderr.write("var: expected 2 arguments, got " + str(len(var_command)) + "\n")

            return
        var_name, var_value = var_command
        os.environ['OUTPUT'] = var_value

    # Validate variable name
    if not re.match(r'^[A-Za-z0-9_]+$', var_name):
        sys.stderr.write(f"var: invalid characters for variable {var_name}\n")
        return

    # Set the environment variable
    os.environ[var_name] = os.environ['OUTPUT']

def pwd(command):
    if len(command) != 1:
        if command[1] == '-P':
            sys.stdout.write(os.path.realpath(os.environ['PWD']) + '\n')
            return
        if command[1][0] == '-':
            sys.stderr.write("pwd: invalid option: " + command[1] + "\n")
        else:
            sys.stderr.write("pwd: not expecting any arguments\n")
        return
    sys.stdout.write(os.environ['PWD'] + '\n')

def cd(command):

    if len(command) > 2:
        sys.stderr.write("cd: too many arguments\n")
        return
    if len(command) == 1:
        os.environ['PWD'] = os.environ['HOME']
        return
    path = command[1]
    if path == '..':
        os.environ['PWD'] = os.path.dirname(os.environ['PWD'])
        return
    if path == '~':
        os.environ['PWD'] = os.environ['HOME']
        return
    if os.path.isabs(path):
        abspath = path
    else:
        abspath = os.path.join(os.environ['PWD'], path)
    if not os.path.exists(abspath):
        sys.stderr.write('cd: no such file or directory: ' + abspath + '\n')
        return
    if not os.path.isdir(abspath):
        sys.stderr.write('cd: not a directory: ' + command[1] + '\n')
        return
    if not os.access(abspath, os.X_OK):
        sys.stderr.write('cd: permission denied: ' + abspath + '\n')
        return
    os.environ['PWD'] = abspath
    return

def which(command):

    built_in_commands = ['var', 'pwd', 'cd', 'which', 'exit']

    if len(command) < 2:
        sys.stderr.write('usage: which command ...\n')
        return

    path_dirs = os.environ['PATH'].split(os.pathsep)

    arguments = command[1:]

    for i in arguments:

        if i in built_in_commands:
            sys.stdout.write(i + ': shell built-in command\n')
            continue
        if os.path.exists(os.environ['PWD'] + '/' + i):
            sys.stdout.write(os.environ['PWD'] + '/' + i + '\n')
            continue
        found_in_path = False
        for path in path_dirs:
            if os.path.exists(path + '/' + i):
                found_in_path = True
                sys.stdout.write(path + '/' + i + '\n')
                break

        if found_in_path:
            continue

        sys.stdout.write(i + ' not found\n')

def exit_cmd(command):
    if len(command) > 2:
        sys.stderr.write("exit: too many arguments\n")
        return
    if len(command) == 2:
        try:
            exit_code = int(command[1])
        except ValueError:
            sys.stderr.write("exit: non-integer exit code provided: " + command[1] + "\n")
            return
        sys.exit(exit_code)
    else:
        sys.exit(0)
