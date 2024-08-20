"""
Module to handle parsing for the shell.
"""
import os
import re
import shlex
import signal
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

def split_and_format_arguments(commands):
    parsed = []
    for i in commands:
        print(i)
        s = shlex.shlex(i, posix=True)
        s.whitespace_split = True
        s.escapedquotes = "'\""
        s.quotes = "'\""
        s.escape = '\\'
        s.commenters = ''
        try :
            parsed.append(list(s))
        except ValueError:
            sys.stderr.write("mysh: syntax error: unterminated quote\n")
            sys.stderr.flush()
    return parsed

def text_to_variable(text):
    if re.search(r'\\\${.*?}', text):
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        fixed_text = re.sub(r'[\\]', '', text)
    elif re.search(r'\${.*?}', text):
        variable = re.search(r'\${(.*?)}', text).group(1)
        if not re.match(r'^[A-Za-z0-9_]+$', variable):
            sys.stderr.write(f"mysh: syntax error: invalid characters for variable {variable}\n")
            return
        try:
            if text.startswith('"') and text.endswith('"') or text.startswith("'") and text.endswith("'"):
                environ_variable = os.environ[variable]
            else:
                environ_variable = os.environ[variable].strip()
            fixed_text = re.sub(r'\${' + variable + '}', environ_variable, text)
        except KeyError:
            fixed_text = re.sub(r'\${' + variable + '}', '', text)
        if re.search(r'\${.*?}', text):
            fixed_text = text_to_variable(fixed_text)
    else:
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        if re.search(r'^~', text):
            text = re.sub(r'~', os.environ['HOME'], text)
        fixed_text = text

    return fixed_text


def check_for_variables(command):
    checked_variables = []
    checked_variables.append(command[0])
    arguments = command[1:]
    for i in arguments:
        fixed_command = text_to_variable(i)
        checked_variables.append(fixed_command)
    return checked_variables

def check_file_exists(filename):

    if re.search(r'^./', filename):
        cwd_path = os.environ['PWD']
        path = os.path.join(cwd_path, filename)
        if not os.path.exists(path):
            sys.stderr.write('mysh: no such file or directory: ' + filename + '\n')
            return path, False
    elif re.search(r'[/]', filename):
        path = filename
        if not os.path.exists(path):
            sys.stderr.write('mysh: no such file or directory: ' + filename + '\n')
            return path, False
    else:
        existing_path = []
        paths = os.environ['PATH'].split(os.pathsep)
        path = ""
        found_dir = False
        for i in paths:
            i = text_to_variable(i)
            for root, dirs, files in os.walk(i):
                if filename in files:
                    existing_path.append(os.path.join(root, filename))
                if filename in root:
                    found_dir = True

        if existing_path:
            path = existing_path[0]

        if found_dir and not path:
            sys.stderr.write('mysh: ' + filename + ' is a directory\n')
            return path, False

        if not path:
            sys.stderr.write('mysh: command not found: ' + filename + '\n')
            return path, False

    if not os.access(path, os.X_OK):
        sys.stderr.write('mysh: permission denied: ' + filename + '\n')
        return path, False

    return path, True

def run_exec(command):

    filename = command[0]

    path, found_file = check_file_exists(filename)

    if not found_file:
        return

    r, w = os.pipe()

    pid = os.fork()
    if pid == 0:
        # Child process
        os.close(w)
        signal = os.read(r, 1)
        os.close(r)

        #waits for parent to finish setting new process group before executing
        while not signal:
            signal = os.read(r, 1)

        if len(command) == 1:
            os.execv(path, [filename])
        else:
            os.execv(path, command)
    else:
        # Parent process
        os.close(r)
        os.setpgid(pid, pid)
        child_pgid = os.getpgid(pid)
        parent_pgid = os.getpgrp()

        with open('/dev/tty') as tty:
            fd = tty.fileno()
            os.tcsetpgrp(fd, child_pgid)
            os.write(w, b'1')  # Write to the pipe to signal the child
            os.close(w)
            os.waitpid(child_pgid, 0)
            os.tcsetpgrp(fd, parent_pgid)

    return

def pipe_command(command, newin, newout):
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        # Child process
        os.close(w)
        signal = os.read(r, 1)
        os.close(r)

        #waits for parent to finish setting new process group before executing
        while not signal:
            signal = os.read(r, 1)

        os.dup2(newin, 0)  # Replace stdin
        os.dup2(newout, 1)  # Replace stdout
        os.execvp(command[0], command)
    else:
        # parent
        os.close(r)
        os.setpgid(pid, pid)
        child_pgid = os.getpgid(pid)
        parent_pgid = os.getpgrp()

        with open('/dev/tty') as tty:
            fd = tty.fileno()
            os.tcsetpgrp(fd, child_pgid)
            os.write(w, b'1')  # Write to the pipe to signal the child to continue
            os.close(w)
            os.waitpid(child_pgid, 0)
            os.tcsetpgrp(fd, parent_pgid)
    return

def create_pipes(commands):
    num_commands = len(commands)
    pipe_fds = []

    for i in range(num_commands):
        read_fd, write_fd = os.pipe()
        pipe_fds.append((read_fd, write_fd))

    return pipe_fds

def run_piped_commands(raw_command):

    commands = []

    for i in raw_command:
        checked = check_for_variables(i)
        if None in checked:
            return
        commands.append(checked)

    num_commands = len(commands)

    pipe_fds = create_pipes(commands)

    for i, cmd in enumerate(commands):
        cmd = check_for_variables(cmd)

        if check_if_built_in_command(cmd[0]):
            match_single_command(cmd)
            continue

        path, cmd_exists = check_file_exists(cmd[0])
        if not cmd_exists:
            return

        if i == 0:
            pipe_command(cmd, pipe_fds[i][0], pipe_fds[i][1])
        elif i == num_commands - 1:
            # Final command, execute directly
            pipe_command(cmd, pipe_fds[i-1][0], 1)
        else:
            pipe_command(cmd, pipe_fds[i-1][0], pipe_fds[i][1])

        os.close(pipe_fds[i][1])

    return

def run_commands_and_capture_output(command):

    pipe_fds = create_pipes(command)

    for i, cmd in enumerate(command):

        cmd = check_for_variables(cmd)

        if None in cmd:
            return

        if check_if_built_in_command(cmd[0]):
            match_single_command(cmd)
            continue

        path, cmd_exists = check_file_exists(cmd[0])
        if not cmd_exists:
            return

        if i == 0:
            pipe_command(cmd, pipe_fds[i][0], pipe_fds[i][1])
        else:
            pipe_command(cmd, pipe_fds[i-1][0], pipe_fds[i][1])

        os.close(pipe_fds[i][1])

    #output of the last command is captured and placed into the environment variable 'OUTPUT'
    with os.fdopen(pipe_fds[i][0]) as r:
        output = r.read()
        os.environ['OUTPUT'] = output
    return

def run_commands(command_line):

    if len(command_line) == 1:
        match_single_command(command_line[0])
        return True

    run_piped_commands(command_line)
    return True

def check_if_built_in_command(command):
    if command in ['var', 'pwd', 'cd', 'which', 'exit']:
        return True
    return False

def match_single_command(command):

    #runs the appropriate command for any unpiped commands

    command = check_for_variables(command)

    if None in command:
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
    # Validate variable name


    # Check for the -s flag
    if var_command[1][0] == '-':
        if var_command[1] != '-s':
            invalid_option = var_command[1].replace("-", "")
            error = "-" + re.match(r'[^s]', invalid_option).group(0)
            if error:
                sys.stderr.write("var: invalid option: " + error + "\n")
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
        parsed_commands = split_and_format_arguments(split_commands)
        #runs piped commands and places output into environment variable 'OUTPUT'
        run_commands_and_capture_output(parsed_commands)

    else:
        var_command.remove('var')
        if len(var_command) != 2:
            sys.stderr.write("var: expected 2 arguments, got " + str(len(var_command)) + "\n")
            return
        var_name, var_value = var_command
        os.environ['OUTPUT'] = var_value

    if not re.match(r'^[A-Za-z0-9_]+$', var_name):
        sys.stderr.write(f"var: invalid characters for variable {var_name}\n")
        return
    # Set the environment variable
    os.environ[var_name] = os.environ['OUTPUT']
    return

def pwd(command):
    if len(command) != 1:
        if command[1].lower() == '-p':
            sys.stdout.write(os.path.realpath(os.environ['PWD']) + '\n')
            return
        if command[1][0] == '-':
            sys.stderr.write("pwd: invalid option: " + command[1].replace("p", "") + "\n")
        else:
            sys.stderr.write("pwd: not expecting any arguments\n")
        return
    sys.stdout.write(os.environ['PWD'] + '\n')
    return

def cd(command):

    if len(command) > 2:
        sys.stderr.write("cd: too many arguments\n")
        return
    if len(command) == 1:
        os.environ['PWD'] = os.environ['HOME']
        os.chdir(os.environ['HOME'])
        return
    path = command[1]
    if path == '..':
        os.environ['PWD'] = os.path.dirname(os.environ['PWD'])
        os.chdir(os.path.dirname(os.environ['PWD']))
        return
    if path == '~':
        os.environ['PWD'] = os.environ['HOME']
        os.chdir(os.environ['HOME'])
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
    os.chdir(abspath)

    return

def which(command):

    if len(command) < 2:
        sys.stderr.write('usage: which command ...\n')
        return

    arguments = command[1:]

    for i in arguments:

        if check_if_built_in_command(i):
            sys.stdout.write(i + ': shell built-in command\n')
            continue

        sys.stderr = open(os.devnull, 'w')

        path, found_in_path = check_file_exists(i)

        sys.stderr = sys.__stderr__

        if found_in_path:
            sys.stdout.write(path + '\n')
            continue

        sys.stdout.write(i + ' not found\n')
    return

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
