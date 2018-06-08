import time
import ast
import socket
import random
import re
import urllib, json
import pymysql
import string
import requests
import datetime
import configparser

from threading import Thread

# needs a timer (and be able toadd a command to the timer)
# sanitizing sql
# do the dnd api thing
# dice rolling? !roll 1d20
# make the code better pnySmile

# Load config.ini
config = configparser.ConfigParser()
config.read('config.ini')


def dbGetOne(query):
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"] )
    cursor = db.cursor()
    cursor.execute(query)
    data = cursor.fetchone()
    db.close()
    return data

def dbGetAll(query):
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"] )
    cursor = db.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    return data

def dbExecute(query):
    
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"] )
    cursor = db.cursor()
    cursor.execute(query)
    db.close()

def dbExecuteargs(query, arg):
   
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"] )
    cursor = db.cursor()
    cursor.execute(query, arg)
    db.close()

def getUser(line):
    separate = line.split(":", 2)
    user = separate[1].split("!", 1)[0]
    return str(user)

def getMessage(line):
    separate = line.split(":", 2)
    message = separate[2]
    return str(message).strip()

def openSocket():
    s = socket.socket()
    s.connect((config["Twitch"]["HOST"], int(config["Twitch"]["PORT"])))
    s.send(str("PASS " + config["Twitch"]["PASS"] + "\r\n").encode("utf-8"))
    s.send(str("NICK " + config["Twitch"]["IDENT"] + "\r\n").encode("utf-8"))
    s.send(str("JOIN #" + config["Twitch"]["CHANNEL"] + "\r\n").encode("utf-8"))
    
    return s
    
def sendMessage(s, message):
    messageTemp = "PRIVMSG #" + config["Twitch"]["CHANNEL"]+ " :" + message
    s.send(str(messageTemp + "\r\n").encode("utf-8"))
    print("Sent: " + messageTemp)

def joinRoom(s):
    readbuffer = ""
    Loading = True
    while Loading:
        readbuffer = readbuffer + s.recv(1024).decode("utf-8")
        temp = str.split(readbuffer, "\n")
        readbuffer = temp.pop()
        for line in temp:
            print(line)
            Loading = loadingComplete(line)
   
    print("Finished Connecting...")
    s.send("CAP REQ :twitch.tv/commands\r\n".encode("UTF-8"))
    sendMessage(s, "/mods")
def loadingComplete(line):
    if("End of /NAMES list" in line):
        return False
    else:
        return True

def is_live_stream(streamer_name):
    check_if_live = True
    while check_if_live:
        try:
            twitch_api_stream_url = "https://api.twitch.tv/kraken/streams/" + streamer_name + "?client_id=" + config["Twitch"]["CLIENT_ID"]
            streamer_html = urllib.request.urlopen(twitch_api_stream_url)
            streamer = json.loads(streamer_html.read().decode("utf-8"))

            return streamer["stream"] is not None
        except:
            print("Twitch API did not respond, trying again in 60 seconds..")
            time.sleep(60)

def load_commands():
    print("Loading commands...")
    triggerlist = []
    replies  = {}
    levels = {}
    allCommands = dbGetAll("SELECT * FROM commands")
    for command in allCommands:
        trigger = str(command[0])
        triggerlist.append(trigger)
        reply = str(command[1][2:-1])
        replyb = bytes(reply, "utf-8")
        replye = ast.literal_eval(str(replyb).replace('\\\\', '\\'))
        replyf = replye.decode("utf-8")
        
        replies[trigger] = replyf
        levels[trigger] = str(command[2])
    print(triggerlist)
    return (triggerlist, replies, levels)
def taskLoop(s, replies, timers):
    is_live = False
    while True:
        if is_live:
            if(len(timers) > 0):
                sendMessage(s, replies[random.choice(timers)])
            time.sleep(14 * 60)
            is_live = is_live_stream(config["Twitch"]["CHANNEL"])
            if not is_live:
                sendMessage(s, "Detected channel offline.")
        else:
            if "!retweet" in timers:
                timers.remove("!retweet")
                replies["!retweet"] = "Tweet for current stream not set."
                sendMessage(s, "Removed retweet timer.")
            is_live = is_live_stream(config["Twitch"]["CHANNEL"])
            if is_live:
                sendMessage(s, "Detected channel online. Starting timer..")
        time.sleep(60)



s = openSocket()
joinRoom(s)
readbuffer = ""
message = ""
requested=False
triggers = []
responses = {}
clearances = {}
mods = []
permits = []

timertriggers = config["Timers"]["TRIGGERS"].split(",")

(triggers, responses, clearances) = load_commands()
loopThread = Thread(target = taskLoop, args = (s, responses, timertriggers))
loopThread.setDaemon(True)
loopThread.start()

while True:
    while True:
        try:

            

            try:
                chat_data =  s.recv(1024)
                
            except:
                print("Error: disconnected.. Reconnecting")
                s = openSocket()
                joinRoom(s)
                continue

            readbuffer = readbuffer + chat_data.decode("utf-8")
            temp = readbuffer.split('\r\n')
            readbuffer = temp.pop()
            
            if readbuffer == "":
                pass
            
            for line in temp: 
                if "PING" in line:
                    s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    print("Ping? Pong!")
                    continue
                if "PRIVMSG" in line:
                    user = getUser(line)
                    
                    if user in mods:
                        print("User is moderator.")
                    message = getMessage(line)
                elif "NOTICE" in line:
                    if "moderators" in line:
                        tempmsg = line.split(":", 3)
                        tempmods = tempmsg[3].split(",")
                        #print(tempmods)
                        mods = []
                        mods.append("tablestory")
                        for moderator in tempmods:
                            mods.append(moderator.lstrip())
                        
                        if requested:
                            sendMessage(s, "Found {} moderators.".format(len(mods)))
                            requested = False
                    continue
                else:
                    continue

                print("{} typed: {} \n".format(user, message))


                if re.search(r"[a-zA-Z]{2,}\.[a-zA-Z]{2,}", message ) and (user not in mods):
                    if user.lower() in permits:
                        permits.remove(user)
                        
                    else:    
                        sendMessage(s, "/timeout "+user+" 1")
                        sendMessage(s, "@{} links are not allowed! Ask a mod for a !permit.".format(user))

#####################################################################################################################
                                                    ## COMMANDS ## 
#####################################################################################################################                

                # this REALLY needs to be changed
                if message[0] == "!":
                    
                    
                    trigger = message.strip().split(" ")[0]    
                    if trigger.lower() in triggers:
                        clearance = clearances[trigger]
                        reply = responses[trigger]
                        if re.search(r""+trigger+" [@]?[a-zA-Z0-9]+", message ):
                            if clearance == 'mod' and user not in mods:
                                pass
                            else:
                                target = message.strip().split(' ',1)[1] 
                                print("this should @ target and print message.")
                                sendMessage(s, target +": " + reply)
                        elif message == trigger:
                            if clearance == 'mod' and user not in mods:
                                pass
                            else:
                                sendMessage(s, reply)


                #add command
                if (re.search(r"!addcom -ul=all ![a-zA-Z0-9]+", message ) or re.search(r"!addcom -ul=mod ![a-zA-Z0-9]+", message ))and (user in mods):
                    print("** Adding command **")
                    #if theres only '!addcom' and '!someword', but no reply
                    if len(message.split(' ')) <= 3:
                        pass

                    elif len(message.split(' ')) > 3:
                        message = message.split(' ', 3)

                        clearance = str(message[1].split('=')[1])
                        command = str(message[2]).lower()
                        if command.lower() in triggers:
                            sendMessage(s, "Command {} already exists".format(command))
                            continue
                        reply = str(message[3])
                        print(reply.encode("utf-8"))

                        if command[0] == '!':
                            query = "INSERT INTO commands (command, reply, clearance) VALUES ( %s, %s, %s)"
                           
                            

                            dbExecuteargs(query, (command, str(reply.encode("utf-8")), clearance))
                            sendMessage(s, "Command: '"+command+"' added.")
                            triggers.append(command)
                            responses[command] = reply
                            clearances[command] = clearance
                            #(triggers, responses, clearances) = load_commands()
                            continue
                    
                if re.search(r"!delcom ![a-zA-Z0-9]+", message ) and (user in mods):
                    print("** Removing command **")
                    message = message.split(' ', 2)

                    dbExecute("DELETE FROM commands WHERE command='"+str(message[1]).strip()+"' ")
                    (triggers, responses, clearances) = load_commands()
                    if (message[1].lower() in timertriggers):
                        timertriggers.remove(message[1].lower())
                        config.set("Timers", "TRIGGERS", ",".join(timertriggers))
                        with open("config.ini", 'w') as configfile:
                            config.write(configfile)
                
                        sendMessage(s, "Command {} removed from timer.".format(message[1].lower()))
                    sendMessage(s, "Command: '"+str(message[1])+"' deleted.")
                    continue
#####################################################################################################################
                                                    ## UTILS ## 
#####################################################################################################################

                if re.search(r"^!timer ![a-zA-Z0-9]+", message ) and (user in mods):
                    target = message.split(" ")[1].lower()
                    if target not in triggers:
                        sendMessage(s,"Command {} does not exist".format(target))
                        continue
                    if target in timertriggers:
                        timertriggers.remove(target)
                        config.set("Timers", "TRIGGERS", ",".join(timertriggers))
                        sendMessage(s, "Command {} removed from timer.".format(target))
                    else:
                        timertriggers.append(target)
                        config.set("Timers", "TRIGGERS", ",".join(timertriggers))
                        sendMessage(s, "Command {} added to timer.".format(target))
                    with open("config.ini", 'w') as configfile:
                        config.write(configfile)
                    continue
                if re.search(r"^!refreshmods", message):
                    requested = True
                    sendMessage(s, "/mods")

                if re.search(r"^!uptime", message):
                    twitch_api_stream_url = "https://api.twitch.tv/kraken/streams/tablestory?client_id=" + config["Twitch"]["CLIENT_ID"]
                    streamer_html = urllib.request.urlopen(twitch_api_stream_url)
                    streamer = json.loads(streamer_html.read().decode("utf-8"))
                    if streamer["stream"] is None:
                        sendMessage(s, "Channel is not live.")
                        continue

                    curtime = datetime.datetime.utcnow()

                    streamstart = datetime.datetime.strptime(str(streamer["stream"]["created_at"]), '%Y-%m-%dT%H:%M:%SZ')
                    elapsed = int((curtime - streamstart) / datetime.timedelta(seconds=1))
                    hours = int(elapsed / 3600)
                    minutes = int((elapsed - (3600*hours))/60)
                    seconds = int((elapsed -((3600*hours) + (60*minutes))))
                    
                    sendMessage(s, "The stream has been live for {}:{}:{}".format(hours, str(minutes).zfill(2), str(seconds).zfill(2)))
                    


                if re.search(r"^!caster [a-zA-Z0-9_]+", message ) and (user in mods):
                    print("** Caster command **")

                    message = message.split(' ')
                    

                    twitch_api_stream_url = "https://api.twitch.tv/kraken/channels/"+message[1]+"?client_id=" + config["Twitch"]["CLIENT_ID"]
                    streamer_html = urllib.request.urlopen(twitch_api_stream_url)
                    

                    streamer = json.loads(streamer_html.read().decode("utf-8"))
                    
                    game = streamer["game"]

                    sendMessage(s, "We love @"+message[1]+", go give them a follow at www.twitch.tv/"+message[1]+" ! They were last seen playing "+str(game))
                    continue

                if re.search(r"^!permit [a-zA-Z0-9_]+", message ) and (user in mods): 
                    target = message.split(" ")[1]
                    if target not in permits:
                        permits.append(target.lower())
                        sendMessage(s, "@{}: {} has allowed you to post one link.".format(target, user))

                if re.search(r"^!tweet https://twitter.com/[a-zA-Z0-9]+/status/[0-9_]+", message ) and (user in mods):
                    url = message.split(" ")[1]
                      
                    if "!retweet" not in triggers:
                        triggers.append("!retweet")
                        createdtrigger = True
                    responses["!retweet"] = "Let your friends know we're live and retweet out our stream: {}".format(url)
                    clearances["!retweet"] = "all"
                    if "!retweet" not in timertriggers:
                        timertriggers.append("!retweet")
                    
                    sendMessage(s, "!retweet command and timer created/updated.")

#####################################################################################################################
                                                    ## QUOTES ## 
#####################################################################################################################

                if "!quote" in message or "!addquote" in message or "!delquote" in message:
                    dataquotes = dbGetAll("SELECT * FROM quotes")
                    print(dataquotes)
                    totalquotes = len(dataquotes)
                    print(totalquotes)

                    if re.search(r"!quote random$", message ):
                        print("** Quote random **")

                        number = random.randint(1,totalquotes)
                        quote = dbGetOne("SELECT * FROM quotes WHERE number = '"+str(number)+"'")

                        sendMessage(s, str(quote[1]))


                    if re.search(r"!quote [0-9]+$", message ):
                        print("** Quote <nr> **")

                        messages = message.split(' ')
                        number = messages[1]

                        quote = dbGetOne("SELECT * FROM quotes WHERE number = '"+str(number)+"'")
                        sendMessage(s, str(quote[1]))


                    if re.search(r"!delquote [0-9]+", message ) and (user in mods):
                        print("** Remove quote **")

                        quotenr = message.split(' ', 1)[1]
                        dbExecute('DELETE FROM quotes WHERE number='+str(quotenr)+'')
                        sendMessage(s, "Quote #" + quotenr + " deleted.")


                    if re.search(r"!addquote", message ) and (user in mods):
                        print("** Add quote **")

                        newquote = str(message.strip().split(' ', 1)[1])
                        date = str(datetime.datetime.now()).split(" ")[0]
                        totalquotes = str(int(totalquotes+1))

                        sendMessage(s, "Added quote #" + totalquotes)
                        dbExecuteargs('INSERT INTO quotes (number, quote) VALUES ( %s, %s)', (totalquotes, "{} {} #{}".format(newquote, date, totalquotes)))


        except:
            print(doesntexist)
            
            pass
        else:
            break




