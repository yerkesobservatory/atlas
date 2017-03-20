import sys
import os
import argparse
import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

#################### CREATE COMMAND LINE ARGUMENT PARSER #######################
parser = argparse.ArgumentParser(description='Given a file of emails and expiry dates, generate a list of registration tokens')
parser.add_argument('usernames', help="A file list of usernames or username/expiry pairs", type=str)
parser.add_argument('--expiry', '-d', help='The default expiry date for users', type=str)

######################### PARSE COMMAND LINE ARGUMENTS #########################
args = parser.parse_args()
default_date = (args.expiry or '01/01/2024')

# create serializer
s = Serializer(config.Config.SECRET_KEY)

######################### READ IN FILE AND CREATE TOKENS ######################
users = open(args.usernames, 'r')
for line in users:
    elems = line.split(' ')
    # if we just have a username
    if len(elems) == 1:
        msg = {'email':elems[0], 'expiry':default_date}
        print(elems[0]+' '+s.dumps(msg).decode())
    if len(elems) == 2:
        msg = {'email':elems[0], 'expiry':elems[1]}
        print(elems[0]+' '+s.dumps(msg).decode())

# CLOSE OUT THE USER FILE
users.close()
