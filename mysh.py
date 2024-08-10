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
            prompt = input(">>")
        except EOFError:
            break

        split = parsing.split_by_pipe_op(prompt)

        parsed = []


        for i in split:
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

        if any(len(sublist) == 0 for sublist in parsed):
            sys.stderr.write("mysh: syntax error: expected command after pipe\n")
            continue

        if parsing.run_built_in(parsed):
            continue



if __name__ == "__main__":
    main()
