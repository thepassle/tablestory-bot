import time
import socket
import random
import re
import urllib, json
import MySQLdb
import string
import requests
import datetime
from threading import Thread

# needs a timer (and be able toadd a command to the timer)
# sanitizing sql
# do the dnd api thing
# dice rolling? !roll 1d20
# make the code better pnySmile

HOST = "irc.twitch.tv"
PORT = 6667

PASS = "oauth:XXXXXXXXXXXXXXXXXXXXX"
IDENT = "tablestorybot"
CHANNEL = "tablestory"

def getUser(line):
    separate = line.split(":", 2)
    user = separate[1].split("!", 1)[0]
    return str(user)

def getMessage(line):
    separate = line.split(":", 2)
    message = separate[2]
    return str(message).lower().strip()

def openSocket():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.send("PASS " + PASS + "\r\n")
    s.send("NICK " + IDENT + "\r\n")
    s.send("JOIN #" + CHANNEL + "\r\n")
    return s
    
def sendMessage(s, message):
    messageTemp = "PRIVMSG #" + CHANNEL + " :" + message
    s.send(messageTemp + "\r\n")
    print("Sent: " + messageTemp)

def joinRoom(s):
    readbuffer = ""
    Loading = True
    while Loading:
        readbuffer = readbuffer + s.recv(1024)
        temp = string.split(readbuffer, "\n")
        readbuffer = temp.pop()
        for line in temp:
            print(line)
            Loading = loadingComplete(line)
    
def loadingComplete(line):
    if("End of /NAMES list" in line):
        return False
    else:
        return True

def is_live_stream(streamer_name, client_id):
    twitch_api_stream_url = "https://api.twitch.tv/kraken/streams/" + streamer_name + "?client_id=" + client_id

    streamer_html = requests.get(twitch_api_stream_url)
    streamer = json.loads(streamer_html.content)

    return streamer["stream"] is not None

# def taskLoop():
#     while True:
#         print "** BEGIN TASKLOOP **"
#         time.sleep(60)

# loopThread = Thread(target = taskLoop)
# loopThread.setDaemon(True)
# loopThread.start()

def getModList():
    url = "https://tmi.twitch.tv/group/user/tablestory/chatters"
    response = urllib.urlopen(url)
    data = json.loads(response.read())
    moderators = []
    for name in data["chatters"]["moderators"]:
        moderators.append(name)
    return moderators

s = openSocket()
joinRoom(s)
readbuffer = ""
message = ""

while True:
    while True:
        try:

            mods = getModList()
            mods.append('karlklaxon')

            try:
                chat_data =  s.recv(1024)
            except socket.timeout:
                print "Err"

            readbuffer = readbuffer + chat_data
            temp = readbuffer.split('\n')
            readbuffer = temp.pop()
            if readbuffer == "":
                pass

            for line in temp: 
                if "PING" in line:
                    s.send("PONG :tmi.twitch.tv\r\n".encode())

                user = getUser(line)
                message = getMessage(line)

                print "{} typed: {} \n".format(user, message)


                if re.search(r"[a-zA-Z]{2,}\.[a-zA-Z]{2,}", message ) and user not in mods:
                    sendMessage(s, "/timeout "+user+" 1")
                    sendMessage(s, "Links are not allowed!")

#####################################################################################################################
                                                    ## COMMANDS ## 
#####################################################################################################################                

                # this REALLY needs to be changed
                if message[0] == "!":
                    allCommands = dbGetAll("SELECT * FROM commands")

                    for command in allCommands:
                        trigger = str(command[0])
                        reply = str(command[1])
                        clearance = str(command[2])

                        if re.search(r""+trigger+" [a-zA-Z0-9]+", message ):
                            if clearance == 'mod' and user not in mods:
                                pass
                            else:
                                target = message.strip().split(' ',1)[1] 
                                sendMessage(s, "@" + target + ": " + reply)

                        elif message == trigger:
                            if clearance == 'mod' and user not in mods:
                                pass
                            else:
                                sendMessage(s, reply)


                #add command
                if re.search(r"!addcom -ul=all ![a-zA-Z0-9]+", message ) or re.search(r"!addcommand -ul=mod ![a-zA-Z0-9]+", message ) and user in mods:
                    print "** Adding command **"
                    #if theres only '!addcom' and '!someword', but no reply
                    if len(message.split(' ')) <= 3:
                        pass

                    elif len(message.split(' ')) > 3:
                        message = message.split(' ', 3)

                        clearance = str(message[1].split('=')[1])
                        command = str(message[2])
                        reply = str(message[3])
                        if command[0] == '!':
                            dbExecute("INSERT INTO commands (command, reply, clearance) VALUES ( '"+command+"', '"+reply+"', '"+clearance+"' )" )
                            sendMessage(s, "Command: '"+command+"' added.")


                if re.search(r"!delcom ![a-zA-Z0-9]+", message ) and user in mods:
                    print "** Removing command **"
                    message = message.split(' ', 2)

                    dbExecute("DELETE FROM commands WHERE command='"+str(message[1]).strip()+"' ")
                    sendMessage(s, "Command: '"+str(message[1])+"' deleted.")

#####################################################################################################################
                                                    ## UTILS ## 
#####################################################################################################################

                if re.search(r"!caster [a-zA-Z0-9_]+", message ) and user in mods:
                    print "** Caster command **"

                    message = message.split(' ')

                    twitch_api_stream_url = "https://api.twitch.tv/kraken/channels/"+message[1]+"?client_id=7n93eyua2byab5b1izk7opodhioahd"
                    streamer_html = requests.get(twitch_api_stream_url)
                    streamer = json.loads(streamer_html.content)
                    game = streamer["game"]

                    sendMessage(s, "We love @"+message[1]+", go give them a follow at www.twitch.tv/"+message[1]+" ! They were last seen playing "+str(game))

#####################################################################################################################
                                                    ## QUOTES ## 
#####################################################################################################################

                if "!quote" in message or "!addquote" in message or "!delquote" in message:
                    dataquotes = dbGetAll("SELECT * FROM quotes")
                    print dataquotes
                    totalquotes = len(dataquotes)
                    print totalquotes

                    if re.search(r"!quote random$", message ):
                        print "** Quote random **"

                        number = random.randint(1,totalquotes)
                        quote = dbGetOne("SELECT * FROM quotes WHERE number = '"+number+"'")[1]

                        sendMessage(s, str(quote))


                    if re.search(r"!quote [0-9]+$", message ):
                        print "** Quote <nr> **"

                        message = message.split(' ')
                        number = message[1]

                        quote = dbGetOne("SELECT * FROM quotes WHERE number = '"+number+"'")[1]
                        sendMessage(s, str(quote))


                    if re.search(r"!delquote [0-9]+", message ) and user in mods:
                        print "** Remove quote **"

                        quotenr = message.split(' ', 1)[1]
                        dbExecute('DELETE FROM quotes WHERE number='+str(quotenr)+'')
                        sendMessage(s, "Quote #" + quotenr + " deleted.")


                    if re.search(r"!addquote", message ) and user in mods:
                        print "** Add quote **"

                        newquote = str(message.strip().split(' ', 1)[1])
                        date = str(datetime.datetime.now()).split(" ")[0]
                        totalquotes = str(int(totalquotes+1))

                        sendMessage(s, "Added quote #" + totalquotes)
                        dbExecute('INSERT INTO quotes (number, quote) VALUES ('+totalquotes+', "\''+newquote+'\', '+date+'  #'+totalquotes+'")')


        except:
            pass
        else:
            break




