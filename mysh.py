import os
import signal
import sys
import shlex

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
