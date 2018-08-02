
# -*- coding: utf-8 -*-

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
import socketserver
from threading import Thread

# needs a timer (and be able toadd a command to the timer)
# sanitizing sql
# do the dnd api thing
# dice rolling? !roll 1d20
# make the code better pnySmile

# Load config.ini
config = configparser.ConfigParser()
config.read('config.ini')

class BotSocketHandler(socketserver.BaseRequestHandler):
    
    def handle(self):
        print("Incoming connection...")
        # self.request is the TCP socket connected to the client
        self.action_dispatch = {"reload_commands": self.do_reload, "add_command": self.do_addcom, "del_command": self.do_delcom, "edit_command": self.do_editcom}
        while True:
            self.data = self.request.recv(1024).strip()
            
            try:
                self.jsonin = json.loads(self.data.decode("UTF-8"))
            except:
                self.reply = {"result": "Error", "msg": "Invalid JSON"}
                self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                return
            else:  
                print("JSON: {}".format(self.jsonin))
                if "action" not in self.jsonin:
                    self.reply = {"result": "Error", "msg": "Missing argument action"}
                    self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                    return
                try:
                    self.action_dispatch[self.jsonin["action"]]()
                except:
                    self.reply = {"result": "Error", "msg": "Invalid action given."}
                    self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                    return
        
    def do_reload(self):
        try:
            print("Relading commands because of remote request.")
            commands.load_commands()
        except:
            self.reply = {"result": "Error", "msg": "Loading commands failed."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
        else:
            self.reply = {"result": "OK", "msg": "Successfully reloaded commands."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))

    def do_addcom(self):
        print("Remote connection requested to add a command.")
        try:
            if all (arg in self.jsonin for arg in("level", "trigger", "response")):
                if self.jsonin["trigger"] not in commands.triggers:
                    print("Inserting new command into bot.")
                    commands.replies[self.jsonin["trigger"]] = self.jsonin["response"]
                    commands.clearances[self.jsonin["trigger"]] = self.jsonin["level"]
                    commands.triggers.append(self.jsonin["trigger"])
                else:
                    self.reply = {"result": "Error", "msg": "Command already exists."}
                    self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                    return
            else:
                self.reply = {"result": "Error", "msg": "Error missing argument for add_command."}
                self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                return
        except:
            self.reply = {"result": "Error", "msg": "Error adding new command to bot."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
        else:
            self.reply = {"result": "OK", "msg": "Successfully added command."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))

    def do_delcom(self):
        print("Remote connection requested to remove a command.")
        try:
            if "trigger" in self.jsonin:
                if self.jsonin["trigger"] in commands.triggers:
                    try:
                        print("Removing {}....".format(self.jsonin["trigger"]))
                        commands.triggers.remove(self.jsonin["trigger"])
                        commands.clearances.pop(self.jsonin["trigger"])
                        commands.replies.pop(self.jsonin["trigger"])
                    except:
                        print("Exception")
                    if (self.jsonin["trigger"] in commands.timertriggers):
                        commands.timertriggers.remove(self.jsonin["trigger"])
                        config.set("Timers", "TRIGGERS", ",".join(commands.timertriggers))
                        with open("config.ini", 'w') as configfile:
                            config.write(configfile)
                else:
                    self.reply = {"result": "Error", "msg": "Command does not exist."}
                    self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                    return
            else:
                self.reply = {"result": "Error", "msg": "Error missing argument for del_command."}
                self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                return
        except:
            self.reply = {"result": "Error", "msg": "Error removing command from bot."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
        else:
            self.reply = {"result": "OK", "msg": "Successfully removed command."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
        
    def do_editcom(self):
        print("Remote connection requested to edit a command.")
        try:
            if all (arg in self.jsonin for arg in("level", "trigger", "response")):
                if self.jsonin["trigger"] in commands.triggers:
                    print("Editing command {}.".format(self.jsonin["trigger"]))
                    commands.replies[self.jsonin["trigger"]] = self.jsonin["response"]
                    commands.clearances[self.jsonin["trigger"]] = self.jsonin["level"]
                    
                else:
                    self.reply = {"result": "Error", "msg": "Command does not exist in bot."}
                    self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                    return
            else:
                self.reply = {"result": "Error", "msg": "Error missing argument for edit_command."}
                self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
                return
        except:
            self.reply = {"result": "Error", "msg": "Error editing command in bot."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))
        else:
            self.reply = {"result": "OK", "msg": "Successfully edited command."}
            self.request.sendall(json.dumps(self.reply).encode("UTF-8"))

    
def socketloop():
   

    
    server = socketserver.TCPServer((config["Remote"]["host"], int(config["Remote"]["port"])), BotSocketHandler)
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
    server.serve_forever()

class BotCommands:

    def __init__(self):
        self.triggers = []
        self.replies = {}
        self.clearances = {}
        self.timertriggers = config["Timers"]["TRIGGERS"].split(",")
        self.timertest = False

    def load_commands(self):
        print("Loading commands...")
        self.triggers.clear()
        self.replies.clear()
        self.clearances.clear()

        allCommands = dbGetAll("SELECT * FROM commands2")


        for command in allCommands:
           
            trigger = str(command[0])
            self.triggers.append(trigger)
            reply = command[1]

        
            self.replies[trigger] = reply
            self.clearances[trigger] = str(command[2])

def dbGetOne(query):
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"], charset='utf8mb4' )
    cursor = db.cursor()
    cursor.execute(query)
    data = cursor.fetchone()
    db.close()
    return data

def dbGetAll(query):
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"], charset='utf8mb4' )
    cursor = db.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    return data

def dbExecute(query):
    
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"], charset='utf8mb4' )
    cursor = db.cursor()
    cursor.execute(query)
    db.close()

def dbExecuteargs(query, arg):
   
    db = pymysql.connect(config["Database"]["HOSTNAME"],config["Database"]["USERNAME"],config["Database"]["PASSWORD"],config["Database"]["DBNAME"], charset='utf8mb4' )
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
    print("Sent: " + str(messageTemp) )

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



def load_dndapi():
    spell_data_clean = {}
    connection = urllib.request.urlopen("http://dnd5eapi.co/api/spells")
    spelldata =json.loads(connection.read().decode("utf-8"))
    for spell in spelldata["results"]:
        if "/" in spell["name"]:
            parts = spell["name"].split("/")
            for part in parts:
                spell_data_clean[part.lower().replace("'", "")] = spell["url"]
        else:
            spell_data_clean[spell["name"].lower().replace("'", "")] = spell["url"]
    print("Loaded {} spells from api.".format(len(spell_data_clean)))
    return spell_data_clean

def get_spell_text(url):
    connection = urllib.request.urlopen(url)
    response = json.loads(connection.read().decode("utf-8"))
    spell_text = []
    spell_text.append(response["name"])
    spell_text.append(", ".join(response["components"]))
    spell_text.append(response["school"]["name"])
    spell_text.append("Duration: {}".format(response["duration"]))
    spell_text.append("Concentration: {}".format(response["concentration"]))
    spell_text.append("Cast time: {}".format(response["casting_time"]))
    print("Description: {}".format(len(response["desc"])))
    if (len(response["desc"]) >= 2):
        spell_text.append(response["desc"][0].replace("â€™", "'") + " " + response["desc"][1].replace("â€™", "'"))
    else:
        spell_text.append(response["desc"][0].replace("â€™", "'"))
    if "higher_level" in response:
        spell_text.append(response["higher_level"][0])
    #spell_text.append("page")
    output = "-".join(spell_text)
    if len(output) > 500:
        sendMessage(s, output[0:499])
        if len(output) > 1000:
            sendMessage(s, output[500:999])
        else:
            sendMessage(s, output[500:])
    else:
        sendMessage(s, output)

    
def taskLoop():
    is_live = False
    while True:
        if is_live or commands.timertest:
            if(len(commands.timertriggers) > 0):
                sendMessage(s, commands.replies[random.choice(commands.timertriggers)])
            time.sleep(14 * 60)
            is_live = is_live_stream(config["Twitch"]["CHANNEL"])
            if not is_live:
                sendMessage(s, "Detected channel offline.")
        else:
            if "!retweet" in commands.timertriggers:
                commands.timertriggers.remove("!retweet")
                commands.replies["!retweet"] = "Tweet for current stream not set."
                sendMessage(s, "Removed retweet timer.")
            is_live = is_live_stream(config["Twitch"]["CHANNEL"])
            if is_live:
                sendMessage(s, "Detected channel online. Starting timer..")
        time.sleep(60)


commands = BotCommands()
s = openSocket()
joinRoom(s)
readbuffer = ""
message = ""
requested=False

mods = []
permits = []
rollcooldown = {}
commands.load_commands()

regulars = config["Twitch"]["regulars"].split(",")
if "" in regulars:
    regulars.remove("")
if "" in commands.timertriggers:
    commands.timertriggers.remove("")
socketThread = Thread(target = socketloop)
socketThread.setDaemon(True)
socketThread.start()
loopThread = Thread(target = taskLoop)
loopThread.setDaemon(True)
dnd_spells = load_dndapi()
#loopThread.start()

while True:
    while True:
        try:

            

            try:
                chat_data =  s.recv(1024)
                if chat_data  == b'':
                    raise socket.timeout
            except:
                print("Error: disconnected.. Reconnecting")
                s = openSocket()
                joinRoom(s)
                continue
            if not loopThread.is_alive():
                print("Loop thread not running, starting....")
                loopThread.start()
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
                        mods.append("karlklaxon")
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
                    elif user.lower() in regulars:
                        pass
                    else:    
                        sendMessage(s, "/timeout "+user+" 1")
                        sendMessage(s, "@{} links are not allowed! Ask a mod for a !permit.".format(user))

#####################################################################################################################
                                                    ## COMMANDS ## 
#####################################################################################################################                

                # this REALLY needs to be changed
                if message[0] == "!":
                    
                    
                    trigger = message.strip().split(" ")[0]    
                    if trigger.lower() in commands.triggers:
                        clearance = commands.clearances[trigger.lower()]
                        reply = commands.replies[trigger.lower()]
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

                #edit command
                if (re.search(r"^!editcom ![a-zA-Z0-9]+", message )) and (user in mods):
                    print("** Editing command **")

                    updatedCommand = re.split(r'^!editcom ![a-zA-Z0-9]{2,}\b ', message)[1]
                    command = message.split(' ')[1]
                    if command.lower() not in commands.triggers:
                        sendMessage(s, "Command {} doesn't exist".format(command))
                        continue
                    else:
                        query = "UPDATE commands2 SET reply='"+updatedCommand+"' WHERE command='"+command+"'"                        
                        dbExecute(query)
                        sendMessage(s, "Command: '"+command+"' edited.")

                        commands.load_commands()
                        continue       

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
                        if command.lower() in commands.triggers:
                            sendMessage(s, "Command {} already exists".format(command))
                            continue
                        reply = str(message[3])
                        print(reply.encode("utf-8"))

                        if command[0] == '!':
                            query = "INSERT INTO commands2 (command, reply, clearance) VALUES ( %s, %s, %s)"
                            

                            dbExecuteargs(query, (command, reply, clearance))
                            sendMessage(s, "Command: '"+command+"' added.")
                            commands.triggers.append(command)
                            commands.replies[command] = reply
                            commands.clearances[command] = clearance
                            #(triggers, responses, clearances) = load_commands()
                            continue
                    
                if re.search(r"!delcom ![a-zA-Z0-9]+", message ) and (user in mods):
                    print("** Removing command **")
                    message = message.split(' ', 2)

                    dbExecute("DELETE FROM commands2 WHERE command='"+str(message[1]).strip()+"' ")
                    commands.load_commands()
                    if (message[1].lower() in commands.timertriggers):
                        commands.timertriggers.remove(message[1].lower())
                        config.set("Timers", "TRIGGERS", ",".join(commands.timertriggers))
                        with open("config.ini", 'w') as configfile:
                            config.write(configfile)
                
                        sendMessage(s, "Command {} removed from timer.".format(message[1].lower()))
                    sendMessage(s, "Command: '"+str(message[1])+"' deleted.")
                    continue
#####################################################################################################################
                                                    ## UTILS ## 
#####################################################################################################################

                if (re.search(r"^!roll$", message) or re.search(r"^!roll [0-9]+d[0-9]+$", message)):
                    if user in rollcooldown:
                        if time.time() < rollcooldown[user]:
                            continue
                    args = message.lower().split(" ")
                    if (len(args) == 1):
                        sendMessage(s, "You rolled a {}".format(random.randint(1,20)))
                        rollcooldown[user] = time.time() + 30
                    elif (len(args) == 2):
                        numdice = int(args[1].split("d")[0])
                        dicetype = int(args[1].split("d")[1])
                        rolls = []
                        total = 0
                        if (0 < numdice) and (numdice < 7):
                            if dicetype <= 100:
                                for i in range(numdice):
                                    curroll = random.randint(1, dicetype)
                                    rolls.append(str(curroll))
                                    total += curroll
                                if numdice > 1:
                                    sendMessage(s, "You rolled {}={}".format("+".join(rolls), total))
                                else:
                                    sendMessage(s, "You rolled a {}".format(total))
                    else:
                        continue
                    if user not in mods:
                        rollcooldown[user] = time.time() + 30

                if re.search(r"^!spell [a-zA-Z\'\s]+", message):
                    spell_name = message.split(" ",1)[1].lower().replace("'","")
                    if spell_name in dnd_spells:
                        get_spell_text(dnd_spells[spell_name])
                        continue
                    else:
                        sendMessage(s, "Spell not found.")
                        continue

                if re.search(r"^!timer ![a-zA-Z0-9]+", message ) and (user in mods):
                    target = message.split(" ")[1].lower()
                    if target not in commands.triggers:
                        sendMessage(s,"Command {} does not exist".format(target))
                        continue
                    if target in commands.timertriggers:
                        commands.timertriggers.remove(target)
                        config.set("Timers", "TRIGGERS", ",".join(commands.timertriggers))
                        sendMessage(s, "Command {} removed from timer.".format(target))
                    else:
                        commands.timertriggers.append(target)
                        config.set("Timers", "TRIGGERS", ",".join(commands.timertriggers))
                        sendMessage(s, "Command {} added to timer.".format(target))
                    with open("config.ini", 'w') as configfile:
                        config.write(configfile)
                    continue
                if re.search(r"^!refreshmods", message):
                    requested = True
                    sendMessage(s, "/mods")

                if (re.search(r"^!regular", message) and (user in mods)):
                    args = message.split(" ")
                    if len(args) >= 2:
                        if args[1] == "list":
                            sendMessage(s, "/w {} Regulars: {}".format(user, ", ".join(regulars)))
                            continue

                        if len(args) != 3:
                            continue
                        if args[1] == "add":
                            
                            if args[2].lower() in regulars:
                                sendMessage(s, "{} is already a regular.".format(args[2]))
                                continue

                            regulars.append(args[2].lower())
                            config.set("Twitch", "regulars", ",".join(regulars))
                            sendMessage(s, "Added {} to regulars".format(args[2]))
                        if args[1] == "del":
                            if args[2].lower() not in regulars:
                                sendMessage(s, "{} was not a regular".format(args[2]))
                                continue
                            regulars.remove(args[2].lower())
                            config.set("Twitch", "regulars", ",".join(regulars))
                            sendMessage(s, "Removed {} from regulars.".format(args[2]))
                        with open("config.ini", 'w') as configfile:
                            config.write(configfile)

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
                      
                    if "!retweet" not in commands.triggers:
                        commands.triggers.append("!retweet")
                        createdtrigger = True
                    commands.replies["!retweet"] = "Let your friends know we're live and retweet out our stream: {}".format(url)
                    commands.clearances["!retweet"] = "all"
                    if "!retweet" not in commands.timertriggers:
                        commands.timertriggers.append("!retweet")
                    
                    sendMessage(s, "!retweet command and timer created/updated.")

#####################################################################################################################
                                                    ## QUOTES ## 
#####################################################################################################################

                if "!quote" in message or "!addquote" in message or "!delquote" in message:

                    if re.search(r"^!quote random$", message ):
                        print("** Quote random **")

                        

                        sent = False
                        while sent == False:
                            try:
                                
                                quotes = dbGetOne("call getrandomquote()")
                                #quote = random.choice(quotes)
                                

                                sendMessage(s, "{} #{}".format(quotes[1], quotes[0]))
                                sent = True
                            except:
                                continue


                    if re.search(r"^!quote [0-9]+$", message ):
                        print("** Quote <nr> **")

                        messages = message.split(' ')
                        number = int(messages[1])
                        print(number)
                        quote = dbGetOne("SELECT * FROM quotes2 WHERE id = {}".format(int(number)))
                        print(quote)
                        if quote is not None:
                            sendMessage(s, "{} #{}".format(quote[1], quote[0]))
                        else:
                            sendMessage(s, "Quote #{} does not exist.".format(number))

                    if re.search(r"^!delquote [0-9]+", message ) and (user in mods):
                        print("** Remove quote **")
                        messages = message.split(' ')
                        number = int(messages[1])
                        quote = dbGetOne("SELECT * FROM quotes2 WHERE id = {}".format(int(number)))
                        print(quote)
                        if quote is not None:
                            dbExecute("DELETE FROM quotes2 WHERE id = {}".format(number))
                            sendMessage(s, "Quote #{} deleted.".format(number))
                        else:
                            sendMessage(s, "Quote #{} does not exist.".format(number))


                    if re.search(r"^!addquote", message ) and (user in mods):
                        print("** Add quote **")
                        
                        nextquote  = dbGetOne("SELECT AUTO_INCREMENT FROM INFORMATION_SCHEMA.TABLES WHERE table_name = 'quotes2' AND table_schema = DATABASE( )")[0]
                        print(nextquote)
                        newquote = str(message.strip().split(' ', 1)[1])
                        date = str(datetime.datetime.now()).split(" ")[0]
                        

                        sendMessage(s, "Added quote #{}".format(nextquote))
                        dbExecuteargs('INSERT INTO quotes2 (quote) VALUES (%s)', ("{} {}".format(newquote, date)))


        except:
            print(doesntexist)
            
            pass
        else:
            break




