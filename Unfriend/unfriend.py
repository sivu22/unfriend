#!/usr/bin/python

#   Copyright 2014 Cristian Sava
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import sys
import os.path
import json
import urllib
import urlparse
import BaseHTTPServer
import webbrowser
import argparse
# The facebook-sdk module
import facebook

from datetime import datetime
from time import time
from enum import Enum


# Facebook app details
APP_ID = "012345678901234"
APP_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ENDPOINT = "graph.facebook.com"
# This is actually 127.0.0.1, add the facebookappname entry into hosts file
# Facebookappname must be the exact name of the Facebook app
REDIRECT_URI = "http://facebookappname:8080/"
# Extension of local file that holds the received user access token
ACCESS_TOKEN_FILE_EXT = ".fbat"
# Extension of local file that holds the friends data
# This data is a JSON filled with all the friends (unfriended as well as new users can be found out thru the FBFriend class)
FRIENDS_DB_FILE_EXT = ".dat"

# Will hold the access token
AccessToken = None
# The facebook account name (in form of email address)
AccountName = None
# When True, show all the friend data and not just the name
InDetail = False
# Output data to this file, when specified
OutputFile = None


# Every user will have this action associated with the date param to give an overview of the activity
class FBAction(Enum):
    NONE = 0
    ADD = 1
    REMOVE = 2


# 1. Users with action == NONE are old users
# 2. Users with action == ADD were added on date
# 3. Users with action == REMOVE are no longer your friends since date
class FBFriend:
    def __init__(self, name, ID, date, action):
        self.name = name
        self.id = ID
        self.date = date
        self.action = action

    def toDict(self):
        dict = {"name": self.name, "id": self.id, "date": self.date, "action": self.action}

        return dict


def urlGetWithParams(path, args = None):
    args = args or {}
    if AccessToken:
        args["access_token"] = AccessToken

    if "access_token" in args or "client_secret" in args:
        endpoint = "https://" + ENDPOINT
    else:
        endpoint = "http://" + ENDPOINT

    return endpoint + path + "?" + urllib.urlencode(args)


def urlGet(path, args = None):
    return urllib.urlopen(urlGetWithParams(path, args = args)).read()


# Handler for getting the user access token
class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        global AccessToken
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        code = None
        code = urlparse.parse_qs(urlparse.urlparse(self.path).query).get("code")[0]

        if code is None:
            self.wfile.write("Sorry, authentication failed.")
            sys.exit(1)

        response = urlGet("/oauth/access_token",
                            {"client_id": APP_ID, "redirect_uri": REDIRECT_URI, "client_secret": APP_SECRET, "code": code})

        AccessToken = urlparse.parse_qs(response).get("access_token")[0]
        open("{0}{1}".format(AccountName, ACCESS_TOKEN_FILE_EXT), "w").write(AccessToken)
        self.wfile.write("You have successfully logged in to facebook. You can close this window now.")


def getTokenFromLogin():
    print "Logging you in to facebook..."
    login_url = urlGetWithParams("/oauth/authorize",
                                    {"client_id": APP_ID, "redirect_uri": REDIRECT_URI, "scope": "read_stream"})
    webbrowser.open(login_url)

    httpd = BaseHTTPServer.HTTPServer(("facebookappname", 8080), RequestHandler)

    while AccessToken is None:
        httpd.handle_request()


def getTokenFromFile():
    return open("{0}{1}".format(AccountName, ACCESS_TOKEN_FILE_EXT)).read()


def loadCurrentDB():
    friendsFilename = "{0}{1}".format(AccountName, FRIENDS_DB_FILE_EXT)

    Friends = None
    if not os.path.exists(friendsFilename):
        return Friends

    try:
        jsonFriends = open(friendsFilename).read()
        Friends = json.loads(jsonFriends)
    except:
        print "Error: exception while loading the local DB!"

    return Friends


# Returnes a list of dictionary containing the current FB friends
def fetchFBFriends():
    global AccessToken

    currentFriends = None
    try:
        graph = facebook.GraphAPI(AccessToken)
        currentFriends = graph.get_connections("me", "friends")["data"]
        if currentFriends == None:
            print "Error: Could not fetch current friend list!\n"
    except:
        print "Invalid OAuth token!"

    return currentFriends


# Writes the list of friends to the user's output file
# The friends should be a list in the FBFriend format
def dumpFriendsToFile(FBFriends):
    global AccountName

    if FBFriends == None or len(FBFriends) == 0:
        return

    jsonString = json.dumps(FBFriends)
    friendsFilename = "{0}{1}".format(AccountName, FRIENDS_DB_FILE_EXT)
    with open(friendsFilename, "wt") as f:
        f.write(jsonString)
            

# Gets a list of friends (fetched from Facebook) and returns the a list of FBFriend objects
def convertToFBFriend(friends):
    FBFriends = []

    for friend in friends:
        FBFriendNew = FBFriend(friend["name"].encode("utf-8"), friend["id"], 0, FBAction.NONE)
        FBFriends.append(FBFriendNew.toDict())

    return FBFriends


def updateFriends(localFBFriends):
    currentFriends = fetchFBFriends()
    if not currentFriends:
        return

    # On first time just dump all the friends to the local dat file
    if localFBFriends == None or len(localFBFriends) == 0:
        # Before writing the data down, first convert it to our format
        FBFriends = convertToFBFriend(currentFriends)
        dumpFriendsToFile(FBFriends)
        return

    # First process the local friends in respect to the remote ones (for FBAction.NONE and FBAction.REMOVE)
    updatedLocalFBFriends = []
    for fbFriend in localFBFriends:
        currentFBFriend = None
        
        for friend in currentFriends:
            if friend["id"] == fbFriend["id"]:
                currentFBFriend = FBFriend(friend["name"].encode("utf-8"), friend["id"], fbFriend["date"], fbFriend["action"])
                friend["id"] = 0
                break

        # Friend was not removed from your list of friends so just add him as he is to the new list of FBFriends
        if currentFBFriend is not None:
            updatedLocalFBFriends.append(currentFBFriend.toDict())
        # Otherwise mark the friend as removed
        else:
            if fbFriend["action"] != FBAction.REMOVE:
                removedFBFriend = FBFriend(fbFriend["name"].encode("utf-8"), fbFriend["id"], int(time()), FBAction.REMOVE)
            else:
                removedFBFriend = FBFriend(fbFriend["name"].encode("utf-8"), fbFriend["id"], fbFriend["date"], FBAction.REMOVE)

            updatedLocalFBFriends.append(removedFBFriend.toDict())

    # Now process the remote ones who were left (for FBAction.ADD)
    for friend in currentFriends:
        # A new remote friend was found
        if friend["id"] != 0:
            newFBFriend = FBFriend(friend["name"].encode("utf-8"), friend["id"], int(time()), FBAction.ADD)
            updatedLocalFBFriends.append(newFBFriend.toDict())

    # Overwrite the local DB with the actual one
    dumpFriendsToFile(updatedLocalFBFriends)


def listFriends(FBFriends, fbAction, local = False):
    global OutputFile, InDetail

    if FBFriends == None:
        print "Can not process displaying request."
        return

    displayFriends = []
    descriptionString = "Your current friends (local database) are:"
    # For local, FBFriends is a list of FBFriend
    if local:
        # Get only the newly added friends
        if fbAction == FBAction.ADD:
            for friend in FBFriends:
                if friend["action"] == FBAction.ADD:
                    displayFriends.append(friend)

            if len(displayFriends) > 0:
                descriptionString = "The list of new friends:"
            else:
                descriptionString = "No new friends found."
        # Get only the unfriended ones
        elif fbAction == FBAction.REMOVE:
            for friend in FBFriends:
                if friend["action"] == FBAction.REMOVE:
                    displayFriends.append(friend)

            if len(displayFriends) > 0:
                descriptionString = "The list of friends that were unfriended or unfriended you:"
            else:
                descriptionString = "No unfriended persons found."
        # Get all the current friends
        else:
            for friend in FBFriends:
                if friend["action"] == FBAction.NONE or friend["action"] == FBAction.ADD:
                    displayFriends.append(friend)
    else:
        displayFriends = FBFriends
        if len(displayFriends) > 0:
            descriptionString = "Your current Facebook friends are:"
        else:
            descriptionString = "No current Facebook friends found."

    if OutputFile is not None:
        with open(OutputFile, "at") as f:
            f.write(descriptionString + "\n")
            for friend in displayFriends:
                if not InDetail:
                    f.write(friend["name"].encode("utf-8") + "\n")
                else:
                    f.write((friend["name"] + " with ID " + friend["id"]).encode("utf-8"))
                    
                    if not local:
                        continue

                    if friend["action"] == FBAction.REMOVE:
                        dt = datetime.fromtimestamp(friend["date"])
                        dtString = dt.strftime("%d.%m.%Y at %H:%M")
                        f.write(" was found removed on " + dtString + "\n")
                    elif friend["action"] == FBAction.ADD:
                        if fbAction == FBAction.ADD:
                            dt = datetime.fromtimestamp(friend["date"])
                            dtString = dt.strftime("%d.%m.%Y at %H:%M")
                            f.write(" was found added on " + dtString + "\n")
                    elif friend["action"] == FBAction.NONE:
                        f.write("\n")
    else:
        print descriptionString
        for friend in displayFriends:
            if not InDetail:
                print friend["name"].encode("utf-8")
            else:
                print((friend["name"] + " with ID " + friend["id"]).encode("utf-8")),
                
                if not local:
                    continue

                if friend["action"] == FBAction.REMOVE:
                    dt = datetime.fromtimestamp(friend["date"])
                    dtString = dt.strftime("%d.%m.%Y at %H:%M")
                    print "was found removed on " + dtString
                elif friend["action"] == FBAction.ADD:
                    if fbAction == FBAction.ADD:
                        dt = datetime.fromtimestamp(friend["date"])
                        dtString = dt.strftime("%d.%m.%Y at %H:%M")
                        print "was found added on " + dtString


def countFriends(FBFriends, local = False):
    global OutputFile

    if FBFriends == None:
        print "Can not process count request."
        return

    numberOfFriends = len(FBFriends)
    if not local:
        displayString = "You currently have {0} facebook friends.\n".format(numberOfFriends)
    else:
        displayString = "You currently have {0} facebook friends (entries) in the local database.\n".format(numberOfFriends)
    
    if OutputFile is not None:
        with open(OutputFile, "at") as f:
            f.write(displayString)
    else:
        print displayString


def queryYesNo(question, default = "yes"):
    validChoices = {"yes" : "yes", "YES" : "yes", "Yes" : "yes", "y" : "yes",
                    "no" : "no", "NO" : "no", "No" : "no", "n" : "no"}

    prompt = " [y/n]"
    if default == "yes":
        prompt = " [Y/n]"
    elif default == "no":
        prompt = " [y/N]"

    while True:
        print question + prompt,

        choice = raw_input().lower()
        if choice is not None and choice == "":
            return validChoices[default]
        elif choice in validChoices:
            return validChoices[choice]
        else:
            print "Wrong answer!"


def main(args):
    global AccessToken, AccountName, InDetail, OutputFile

    parser = argparse.ArgumentParser(description = "Facebook friend observer (C) Cristian Sava 2014", formatter_class = argparse.RawTextHelpFormatter)
    parser.add_argument("account", help = "The facebook account name")
    parser.add_argument("-t", "--token", help = "Specify the user access token directly", required = False)
    parser.add_argument("-l", "--list", help = "Display your current FB friends", action = "store_true", required = False)
    parser.add_argument("-ll", "--listlocal", help = "Display your friends from the local DB", action = "store_true", required = False)
    parser.add_argument("-la", "--listadded", help = "Display all your new friends", action = "store_true", required = False)
    parser.add_argument("-lr", "--listremoved", help = "Display all your ex-friends", action = "store_true", required = False)
    parser.add_argument("-c", "--count", help = "Display how many friends you have (count local ones when there is no token)", action = "store_true", required = False)
    parser.add_argument("-cl", "--countlocal", help = "Display how many friends you have in the local DB", action = "store_true", required = False)
    parser.add_argument("-d", "--detail", help = "Display request in detail", action = "store_true", required = False)
    parser.add_argument("-o", "--output", help = "Specify a file (instead of normal stdout) for the returned data", required = False)

    args = parser.parse_args()

    AccountName = args.account
    if len(AccountName) < 3 or not "@" in AccountName:
        print "Bad account name!\n"
        sys.exit(2)

    if args.detail:
        InDetail = True

    if args.output:
        OutputFile = args.output
        if os.path.exists(OutputFile):
            response = queryYesNo("File already exists. Do you want to overwrite?")
            if response == "no":
                print "Auf Wiedersehen!\n"
                sys.exit(0)
        # Just create the file
        with open(OutputFile, "wt") as f:
                f.write("")

    # Loads the local DB
    localFBFriends = loadCurrentDB()
    if not localFBFriends:
        print "Warning! No local data found. Some functions will be unavailable.\n"

    # Don't sync the DB when at least one operation was exectued
    optionUsed = False
    if args.countlocal:
        optionUsed = True
        countFriends(localFBFriends, True)

    if args.listlocal:
        optionUsed = True
        listFriends(localFBFriends, FBAction.NONE, True)

    if args.listadded:
        optionUsed = True
        listFriends(localFBFriends, FBAction.ADD, True)

    if args.listremoved:
        optionUsed = True
        listFriends(localFBFriends, FBAction.REMOVE, True)

    # Now handle the requests that needs FB data
    if args.token:
        AccessToken = args.token
    elif not os.path.exists("{0}{1}".format(AccountName, ACCESS_TOKEN_FILE_EXT)):
        getTokenFromLogin()
    else:
        AccessToken = getTokenFromFile()

    if AccessToken == None:
        # The token is not needed only when displaying the current friends or counting them (local)
        if not args.list and not args.count:
            print "Error: Could not obtain a valid user access token!\n"
            sys.exit(2)

    # Fetches the remote friends, only if necesary!
    if args.count or args.list or optionUsed == False:
        FBFriends = fetchFBFriends()
        if FBFriends is None and (args.count or args.list):
            print "Error: couldn't fetch list of Facebook friends!"
            sys.exit(2)

    if args.count:
        optionUsed = True
        countFriends(FBFriends)

    if args.list:
        optionUsed = True
        listFriends(FBFriends, FBAction.NONE)

    # The default operation is syncing the local DB with the Facebook data
    if not optionUsed:
        updateFriends(localFBFriends)


if __name__ == '__main__':
    main(sys.argv[1:])
