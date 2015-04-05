# unfriend
Python command-line tool for tracking changes in your Facebook friends list.<br>
Useful to see who (and when) unfriended you, or check out the friends you added or removed from your list. This is accomplished by having 2 lists of people, an added-list and removed-list.

# Prerequisites
All of the following requirements must be fulfilled before running the tool. Make sure to modify the Python source file accordingly. <br>

1. Email and password of Facebook account!
2. A Facebook app is needed (ID and secret) in order to access the graph API.
3. Facebook SDK Python module.
4. hosts must be modified on the running machine, adding the facebook app name as 127.0.0.1 - in order to have a local HTTP server, which will be used for redirection and thus to obtain the OAuth token.

# Usage
Type <code>unfriend.py -h</code> for a list of all the available arguments. The email used to register for the Facebook account (aka username) must always be used.<br><br>
First run <code>unfriend.py username</code>. This will open a new browser tab where the user can login to Facebook and allow the Facebook application to access it's graph data. Next the OAuth token is obtained and saved locally inside the username.fbat file (the friends data will be saved in username.dat file).<br>
From now on, every time the tool is beeing run, this token will be read from the file and then used, if there is no other token given as command parameter. Running <code>unfriend.py username</code> will sync the local data with the remote one.<br><br>
Calling for example <code>unfriend.py username -lr -d</code> will display in detail (with ID and timestamp) all the ex-friends that were tracked by the tool. <code>unfriend.py username -c</code> will count the current Facebook friends, if a valid token is found inside the username.fbat file. <code>unfriend.py username -t TOKEN -l</code> will use the provided TOKEN to display all your current Facebook friends by name.


# Limitations
- Tracking starts from the moment the tool is run for the first time. There is no possibility to register previous events and data about ex-friends.
- If a specific person has opted out of Facebook graph API calls (i.e. third party applications), then that person will not be discovered by the tool.
- If a user deactivates his profile and then reactivates it, or because of unknown circumstances he doesn't appear in the friends list at one time, that person will move to the removed-list and stay there. This can be fixed easily though.
- The timestamp of each add-event and remove-event is dependent on the time when the tool is executed. For better and more precise results, running the tool could be automated every day or every 12 hours for example.
- The lists are shown ordered by the Facebook user ID. Sorting by name/date is not implemented.
- The Facebook OAuth token is valid for 60 days, after it expires a new one must be obtained (this can be achieved with the tool by moving or deleting the current username.fbat file).
- Speaking of OAuth token, keep in mind this is sensitive data and should be kept somewhere safe and private. Right now it is written in plain text inside the .fbat file.
