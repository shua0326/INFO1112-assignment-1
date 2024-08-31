# INFO1112 mysh

The mysh shell is a simple shell program that can be used to run commands on a Unix-like system. 
It is written in python, leveraging the os and sys modules to interact with the system to emulate the functions of a Unix terminal. 

Upon starting the shell, the user is presented with a prompt, '>> ':
user_input = input(os.environ['PROMPT'])

The shell then formats the user input into a list of commands and arguments:

cmds_split_by_pipes = split_by_pipe_op(user_input)
parsed_commands = split_and_format_arguments(escaped_cmds)

It then passes these commands to be processed in the parsing file:

if run_commands(parsed_commands):
    continue

(in parsing.py)

def run_commands(command_line):

    if len(command_line) == 1:
        match_single_command(command_line[0])
        return True

    run_piped_commands(command_line)
    return True

The shell classfies the commands as either a single command or a piped command, and runs them accordingly.

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

match_single_command(command) checks whether the command is a built-in command or a system command, 
calling upon the related function in parsing.py if it is a built-in command or leveraging the run_exec function, which uses the os module to invoke system commands, to run system commands.




