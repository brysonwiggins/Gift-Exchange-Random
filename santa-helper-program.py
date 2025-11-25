import configparser
import httplib2
import os
import oauth2client
from oauth2client import client, tools, file
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
import mimetypes
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
import random
from collections import Counter
from datetime import datetime

SCOPES = 'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = 'credentials.json'
APPLICATION_NAME = 'Santa Helper Program'
masterEmail = ""
masterPass = ""
listFile = ""
historyFile = ""
names = []
emails = []
historyCounts = Counter()
debug = open("LogFile.txt", "w")

class Mail:
    def __init__(self):
        self.port = 465
        self.smtp_server_domain_name = "smtp.gmail.com"
        self.sender_mail = masterEmail
        self.password = masterPass
        self.subject = "Gift Exchange Name - TOP SECRET"

    def send(self, email, content):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('gmail', 'v1', http=http)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = self.subject
        msg['From'] = self.sender_mail
        msg['To'] = email
        msg.attach(MIMEText(content, 'plain'))
        # Can add HTML to email (experiement in future)
        # msg.attach(MIMEText(content, 'html'))
        encodedMsg = {'raw': base64.urlsafe_b64encode(msg.as_string().encode()).decode()}

        try:
            message = (service.users().messages().send(userId="me", body=encodedMsg).execute())
            print('Message Id: %s' % message['id'])
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            return "Error"

    def get_credentials(self):
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                    'gmail-python-email-send.json')
        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            credentials = tools.run_flow(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials


def initializeList():
    with open(listFile) as f:
        lines = f.readlines()
    for line in lines:
        name, email = line.split(',')
        names.append(name.strip())
        emails.append(email.strip())
    f.close()
    return

def loadHistory():
    if historyFile == "" or not os.path.exists(historyFile):
        return
    with open(historyFile) as f:
        for line in f:
            parts = [part.strip() for part in line.strip().split(',') if part.strip() != ""]
            if parts.__len__() == 3:
                _, giver, recipient = parts
            elif parts.__len__() == 2:
                giver, recipient = parts
            else:
                continue
            historyCounts[(giver, recipient)] += 1
    return

def selectNames(count):
    hatOfNames = [*range(0,count, 1)]
    pickedNames = []
    pickingFor = 0
    while(pickedNames.__len__() < count):
        if(pickingFor == count - 2 and pickingFor + 1 in hatOfNames):
            pickedName = pickingFor + 1
        else:
            pickedName = random.choice(hatOfNames)
            if(pickedName == pickingFor):
                pickedName = hatOfNames[(hatOfNames.index(pickedName) + 1) % hatOfNames.__len__()]
        pickedNames.append((pickingFor, pickedName))
        hatOfNames.pop(hatOfNames.index(pickedName))
        pickingFor += 1
    return pickedNames

def getPairWeight(senderIndex, recipientIndex):
    senderName = names[senderIndex]
    recipientName = names[recipientIndex]
    count = historyCounts.get((senderName, recipientName), 0)
    return 1.0 / (1 + count)

def weightedSelectNames(count, maxAttempts = 1000):
    attempt = 0
    while attempt < maxAttempts:
        attempt += 1
        hatOfNames = [*range(0,count, 1)]
        assignments = []
        pickingFor = 0
        success = True
        while pickingFor < count:
            candidates = [candidate for candidate in hatOfNames if candidate != pickingFor]
            if candidates.__len__() == 0:
                success = False
                break
            weights = [getPairWeight(pickingFor, candidate) for candidate in candidates]
            pickedName = random.choices(candidates, weights=weights, k=1)[0]
            assignments.append((pickingFor, pickedName))
            hatOfNames.pop(hatOfNames.index(pickedName))
            pickingFor += 1
        if success:
            return assignments
    raise RuntimeError('Unable to find weighted assignments without conflicts')

def recordHistory(assignments):
    if historyFile == "":
        return
    year = datetime.now().year
    with open(historyFile, 'a') as f:
        for assignment in assignments:
            giver = names[assignment[0]]
            recipient = names[assignment[1]]
            f.write('{year},{giver},{recipient}\n'.format(year=year, giver=giver, recipient=recipient))

def createEmails(assignments):
    mail = Mail()
    for assignment in assignments:
        senderName = names[assignment[0]]
        senderEmail = emails[assignment[0]]
        recieverName = names[assignment[1]]
        body = """HO-HO-HO MERRY CHRISTMAS {sender}!!!!!!\n
        I am emailing you to let you know that this year you get to give a gift to {reciever}!!!!!\n
        Remember to keep this a secret to make it a surprise!\n
        With lots of love:
        \tSanta's helper program""".format(sender=senderName.upper(), reciever=recieverName.upper())
        debug.write(senderName + " -> " + recieverName + '\n')    
        mail.send(senderEmail, body)
    return

def main():
    initializeList()
    loadHistory()
    try:
        if historyFile != "":
            assignments = weightedSelectNames(names.__len__())
        else:
            assignments = selectNames(names.__len__())
    except RuntimeError:
        assignments = selectNames(names.__len__())
    createEmails(assignments)
    recordHistory(assignments)
    return


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.readfp(open(r'santa.conf'))
    masterEmail = config.get('email data', 'masterEmail')
    masterPass = config.get('email data', 'masterPass')
    listFile = config.get('email data', 'listFile')
    try:
        historyFile = config.get('email data', 'historyFile')
    except (configparser.NoOptionError, configparser.NoSectionError):
        historyFile = ""
    main()
    debug.close()
