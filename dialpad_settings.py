"""
This config file contains constants describing 
the specific environment where this script is used.
"""

# API CLIENT_KEY associated with a global admin account
CLIENT_KEY = ''
# Dialpad domain, e.g domain.edu
DOMAIN = ''
# Email address to send auto-notifications from, e.g. user@server.domain.edu
FROM = ''
# Email address to send the notifications to, e.g. user@domain.edu
TO = ''
# Email server address, e.g. mail.domain.edu
MAILSERVER = ''
# Office keys dictionary, you can get the list with an API call 
# like this: https://dialpad.com/api/v1/admin/office?api_key=<api_key>
DEPTDICTIONARY = {}
DEPTDICTIONARY['Admissions'] = 'gdfsgds546456bdcbbc'
DEPTDICTIONARY['Biology'] = ''
DEPTDICTIONARY['History'] = ''
