#!/usr/bin/env python

"""
Simple script to manage Dialpad users 
via API. 

Usage: 
    python dialpad.py -f input.json -o output.csv

Options:
    -h --help
    -f --file	Input file (required)
    -o --out	Output file (required)

Environment specific script constants are stored in this 
config file: dialpad_settings.py
    
Input:

Input file is expected to be in JSON format (e.g. input.json).
with these 7 required data fields:
{
    "useractions": [
        {
            "action": "create",
            "username": "testuserj",
            "newusername": "testuserj",
            "loginDisabled": "False",
            "givenName": "John",
            "sn": "Testuser",
            "primO": "Biology"
        }
    ] 
}
where action can be create/update/delete and newusername is same old 
one or a new value if renaming the user.

Note that renaming users is not supported by the API currently. Update action 
is limitted to suspending and reactivating users only. An email notification 
to the admin will be sent if user renaming is required.
    
Output:

Output file (e.g. output.csv) will have these fields:

action, username, result (ERROR/SUCCESS: reason)

Logging:

Script creates a detailed dialpad.log

All errors are also printed to stdout.

Author: A. Ablovatski
Email: ablovatskia@denison.edu
Date: 11/21/2016
"""

from __future__ import print_function
import time
import sys
import traceback
import json
import csv
import argparse
import logging
import httplib
import urllib
import textwrap
import smtplib

def main(argv):
    """This is the main body of the script"""
    
    # Setup the log file
    logging.basicConfig(
        filename='dialpad.log',level=logging.DEBUG, 
        format='%(asctime)s, %(levelname)s: %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S')

    # Get Dialpad creds and other constants from this settings file
    config_file = 'dialpad_settings.py'
    
    if not readConfig(config_file):
        logging.error("unable to parse the settings file")
        sys.exit()
    
    # Parse script arguments
    parser = argparse.ArgumentParser()                                               

    parser.add_argument("--file", "-f", type=str, required=True, 
                        help="Input JSON file with user actions and params")
    parser.add_argument("--out", "-o", type=str, required=True, 
                        help="Output file with results of Dialpad user actions")

    try:
        args = parser.parse_args()
        
    except SystemExit:
        logging.error("required arguments missing - " \
                        "provide input and output file names")
        sys.exit()

    # Read input from json file
    in_file = args.file
    # Write output to csv file
    out_file = args.out
    
    try:
        f_in = open(in_file, 'rb')
        logging.info("opened input file: {0}".format(in_file))
        f_out = open(out_file, 'wb')
        logging.info("opened output file: {0}".format(out_file))
        reader = json.load(f_in)
        writer = csv.writer(f_out)
        writer.writerow(['action','username','result'])

        for row in reader["useractions"]:
            result = ''
            # Select what needs to be done
            if row["action"] == 'create':
                result = create(str(row["username"]), str(row["givenName"]), 
                                str(row["sn"]), str(row["primO"]))
            elif row["action"] == 'update':
                result = update(str(row["username"]), str(row["newusername"]), 
                                str(row["loginDisabled"]))
            elif row["action"] == 'delete':
                 result = delete(str(row["username"]))
            else:
                print("ERROR: unrecognized action: {0}".format(row["action"]))
                logging.error("unrecognized action: {0}".format(row["action"]))
                result = "ERROR: Unrecognized action."
            
            # Write the result to the output csv file
            writer.writerow([row["action"], row["username"], result])
            
    except IOError:
        print("ERROR: Unable to open input/output file!")
        logging.critical("file not found: {0} or {1}".format(in_file, out_file))
        
    except Exception as e:
        traceb = sys.exc_info()[-1]
        stk = traceback.extract_tb(traceb, 1)
        fname = stk[0][3]
        print("ERROR: unknown error while processing line '{0}': " \
                "{1}".format(fname,e))
        logging.critical("unknown error while processing line '{0}': " \
                "{1}".format(fname,e))
        
    finally:
        f_in.close()
        logging.info("closed input file: {0}".format(in_file))
        f_out.close()
        logging.info("closed output file: {0}".format(out_file))
        
    return


def create(username, givenName, sn, ou):
    """This funtion adds users to Dialpad"""
    
    # Check if any of the parameters are missing
    params = locals()
    
    for _item in params:
        if str(params[_item]) == "":
            print("ERROR: unable to create user {0} because {1} is missing " \
                    "a value".format(username, _item))
            logging.error("unable to create user {0} because {1} is missing " \
                            "a value".format(username, _item))
            result = "ERROR: Missing an expected input value for " + _item \
                        + " in input file."
            return result
    
    # Grab the API CLIENT_KEY
    api_key = CLIENT_KEY
    
    # Create user principal name
    upn = username + "@" + DOMAIN

    # Check if the user already exists
    if findUser(upn):
        print("ERROR: cannot add Dialpad account - user already exists: {0}" \
                .format(username))
        logging.error("cannot add Dialpad account - user already exists: {0}" \
                .format(username))
        result = "ERROR: username already exists in Dialpad!"
        return result
    
    # If can't find an office for this user, 
    # just don't assign this user to any office.
    office = ""
    office_key = findOfficeKey(ou)
    if office_key:
        office = "&office_key=" + office_key
    
    try:
        # Set the header
        headers = {
        }
        
        # Connect to Dialpad API
        conn = httplib.HTTPSConnection('dialpad.com')
        conn.request("GET", "/api/v1/admin/user?api_key=" + api_key 
                        + "&email=" + upn + "&action=add&first_name=" 
                        + givenName + "&last_name=" + sn + office, "", headers)
        response = conn.getresponse()

        # Check if the request succeeded
        if response.status != 200:
            logging.error("user {0} was not created in Dialpad".format(upn))
            print("ERROR: Could not create user in Dialpad: {0}".format(upn))
            result = "ERROR: could not create Dialpad user."
        else:
            # Log user creation
            logging.info("user added to Dialpad: {0}".format(upn))
            print("SUCCESS: User {0} added to Dialpad".format(upn))
            result = "SUCCESS: user was created in Dialpad."
        
        conn.close()
        
    except Exception as e:
        print("ERROR: Could not add user to Dialpad: {0}".format(e))
        logging.error("Dialpad add failed for user: {0}: {1}" \
                        .format(username,e))
        result = "ERROR: could not create Dialpad user."
        return result
    
    return result


def update(username, newusername, loginDisabled):
    """This function updates a user (only to 
    suspend or reactivate currently)"""

    # Check if any of the arguments are missing
    params = locals()
    
    for _item in params:
        if str(params[_item]) == "":
            print("ERROR: unable to update user {0} because {1} is missing " \
                    "a value".format(username, _item))
            logging.error("unable to update user {0} because {1} is missing " \
                            "a value".format(username, _item))
            result = "ERROR: Missing an expected input value for " \
                        + _item + " in input file."
            return result

    # Grab the CLIENT_KEY
    api_key = CLIENT_KEY
    
    # Create user principal name
    upn = username + "@" + DOMAIN
    
    if not findUser(upn):
        print("ERROR: user does not exist in Dialpad: {0}".format(username))
        logging.error("user does not exist in Dialpad: {0}".format(username))
        result = "ERROR: user could not be found in Dialpad!"
        return result
    
    # If newusername is diferent
    # notify admin about renaming request
    if username != newusername:
        # Send an email to the operator re:
        # renaming user manually (not supported in API)
        frm = FROM
        to = TO
        subject = "Rename Dialpad user: " + username + " to " + newusername
        text = "Please rename Dialpad user account manually."
                
        sendMail(frm, to, subject, text)
        print("ERROR: renaming users in Dialpad is not supported: {0}" \
                .format(username))
        logging.info("emailed {0} about Dialpad account re-naming" \
                .format(to))
        result = "ERROR: renaming users in Dialpad is not supported " \
                    "- emailed Dialpad admin!"
        return result
    
    # suspend or reactivate the user
    if loginDisabled == "True":
        action = "suspend"
    else:
        action = "reactivate"

    # Suspend or reactivate
    try:
        # Set the header
        headers = {
        }
        
        # Connect to Dialpad API
        conn = httplib.HTTPSConnection('dialpad.com')
        conn.request("GET", "/api/v1/admin/user?api_key=" + api_key 
                        + "&email=" + upn + "&action=" + action, "", headers)
        response = conn.getresponse()

        # Check if the request succeeded
        if response.status != 200:
            logging.error("user {0} was not updated in Dialpad".format(upn))
            print("ERROR: Could not update user in Dialpad: {0}".format(upn))
            result = "ERROR: could not update Dialpad user."
        else:
            # Log user update
            logging.info("user updated in Dialpad: {0}".format(username))
            print("SUCCESS: User {0} updated Dialpad".format(username))
            result = "SUCCESS: user was updated in Dialpad."
        
        conn.close()
        
    except Exception as e:
        print("ERROR: Could not update user in Dialpad: {0}".format(e))
        logging.error("Dialpad update failed for: {0}: {1}".format(username,e))
        result = "ERROR: Could not update Dialpad user."
        return result
    
    return result


def delete(username):
    """This function deletes a user from Dialpad"""

    # Check if the argument is missing
    if str(username) == "":
        print("ERROR: unable to delete user because username argument " \
                "is missing a value")
        logging.error("unable to delete user because username argument " \
                        "is missing a value")
        result = "ERROR: Missing an expected input value for username " \
                    "in input file."
        return result

    # Grab the CLIENT_KEY
    api_key = CLIENT_KEY
    
    # Create user principal name
    upn = username + "@" + DOMAIN
    
    if not findUser(upn):
        print("ERROR: user does not exist in Dialpad: {0}".format(username))
        logging.error("user does not exist in Dialpad: {0}".format(username))
        result = "ERROR: user could not be found in Dialpad!"
        return result
        
    # Delete user if all is OK
    try:
         # Build header
        headers = {
        }
    
        # Connect to Dialpad API
        conn = httplib.HTTPSConnection('dialpad.com')
        conn.request("GET", "/api/v1/admin/user?api_key=" + api_key 
                        + "&email=" + upn + "&action=delete", "", headers)
        response = conn.getresponse()

        if response.status != 200:
            logging.error("user was not deleted in Dialpad: {0}" \
                    .format(username))
            print("ERROR: User {0} was not deleted in Dialpad" \
                    .format(username))
            result = "ERROR: could not delete user in Dialpad."
        else:
            logging.info("user deleted in Dialpad: {0}".format(username))
            print("SUCCESS: User {0} deleted in Dialpad".format(username))
            result = "SUCCESS: user deleted in Dialpad."
            
        conn.close()

    except Exception as e:
        print("ERROR: unknown error while deleting user: {0}".format(e))
        logging.error("unknown error while deleting user {0}: {1}" \
                        .format(username,e))
        result = "ERROR: Could not delete Dialpad user."
    
    return result


def readConfig(config_file):
    """Function to import the config file"""
    
    if config_file[-3:] == ".py":
        config_file = config_file[:-3]
    dialpadsettings = __import__(config_file, globals(), locals(), [])
    
    # Read settings and set globals
    try: 

        global CLIENT_KEY
        global DOMAIN
        global DEPTDICTIONARY
        global FROM
        global TO
        global MAILSERVER

        CLIENT_KEY = dialpadsettings.CLIENT_KEY
        DOMAIN = dialpadsettings.DOMAIN
        FROM = dialpadsettings.FROM
        TO = dialpadsettings.TO
        MAILSERVER = dialpadsettings.MAILSERVER
        DEPTDICTIONARY = dialpadsettings.DEPTDICTIONARY

    except Exception as e:
        logging.error("unable to parse settings file")
        print("ERROR: unable to parse the settings file: {0}".format(e))
        return False
        
    return True


def findUser(upn):
    """Do a quick check if the user already exists"""
        
    # Build header
    headers = {
    }
    
    # Grab the API CLIENT_KEY
    api_key = CLIENT_KEY
    
    # Connect to Dialpad API
    try:
        conn = httplib.HTTPSConnection('dialpad.com')
        conn.request("GET", "/api/v1/admin/user?api_key=" + api_key 
                        + "&email=" + upn, "", headers)
        response = conn.getresponse()

        if response.status == 200:
            data = response.read()
            if upn not in data:
                conn.close()
                return False
        else:
            print("ERROR: Dialpad service did not respond correctly")
            logging.error("Dialpad service returned: {0}" \
                            .format(response.status))
            
        conn.close()

    except Exception as e:
        print("ERROR: problem with user search in Dialpad: {0}".format(e))
        logging.error("problem searching for {0} in Dialpad: {1}".format(upn,e))
        
    return True


def findOfficeKey(ou):
    """ This function looks up 
    office key based on HR-provided ou"""
    
    # Get primOU->office key translation dictionary
    deptDict = DEPTDICTIONARY

    # Lookup the dept group by ou
    officeKey = deptDict.get(ou, None)
        
    return officeKey


def sendMail(frm, to, subject, text):
    """Function to send a notification email"""
    
    # Build the message body
    message = textwrap.dedent("""\
        From: {0}
        To: {1}
        Subject: {2}
        {3}
        """.format(frm, to, subject, text))
    
    try:
        # Send the mail
        mailserver = MAILSERVER
        server = smtplib.SMTP(mailserver)
        server.sendmail(frm, to, message)
        server.quit()
        
    except Exception as e:
        print("ERROR: unable to send email: {0}".format(e))
        logging.error("unknown error while sending email: {0}".format(e))
    
    return


if __name__ == "__main__":
    main(sys.argv)
