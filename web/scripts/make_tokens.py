import sys
import os
import argparse
import datetime
from itsdangerous import Signer
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

#################### CREATE COMMAND LINE ARGUMENT PARSER #######################
parser = argparse.ArgumentParser(description='Given a file of emails and expiry dates, generate a list of registration tokens')
parser.add_argument('usernames', help="A file list of usernames or username/expiry pairs", type=str)

######################### PARSE COMMAND LINE ARGUMENTS #########################
args = parser.parse_args()

# create serializer
s = Signer(config.Config.SECRET_KEY)

######################### READ IN FILE AND CREATE TOKENS ######################
users = open(args.usernames, 'r')
for line in users:
    if line == '' or line == '\n':
        continue
    tok = s.sign(line.strip().encode()).decode().split('.')
    print(tok[0]+'.'+tok[1]+' '+tok[2])

# CLOSE OUT THE USER FILE
users.close()
