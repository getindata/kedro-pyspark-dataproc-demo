import os
from kedro.framework import cli

os.chdir('/home/kedro')

print(os.environ)

cli.main()