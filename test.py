import re, sys
line = 'helloworld'
if re.search(r'[^u]', line):
    print('match found')
    sys.exit(1)
else:
    print('fuck you')
    sys.exit(1)