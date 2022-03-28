import configparser
import smtplib, ssl
import random

masterEmail = ""
masterPass = ""
listFile = ""
names = []
emails = []
debug = open("LogFile.txt", "w")

class Mail:
    def __init__(self):
        self.port = 465
        self.smtp_server_domain_name = "smtp.gmail.com"
        self.sender_mail = masterEmail
        self.password = masterPass

    def send(self, email, subject, content):
        ssl_context = ssl.create_default_context()
        service = smtplib.SMTP_SSL(self.smtp_server_domain_name, self.port, context=ssl_context)
        service.login(self.sender_mail, self.password)
        
        service.sendmail(self.sender_mail, email, f"To: {email}\r\nSubject: {subject}\r\n{content}")
        service.quit()


def initializeList():
    with open('exchangeList.txt') as f:
        lines = f.readlines()
    for line in lines:
        name, email = line.split(',')
        names.append(name.strip())
        emails.append(email.strip())
    f.close()
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

def createEmails(assignments):
    mail = Mail()
    for assignment in assignments:
        senderName = names[assignment[0]]
        senderEmail = emails[assignment[0]]
        recieverName = names[assignment[1]]
        subject = "Gift Exchange Name - TOP SECRET"
        body = """HO-HO-HO MERRY CHRISTMAS {sender}!!!!!!\n
        I am emailing you to let you know that this year you get to give a gift to {reciever}!!!!!\n
        Remember to keep this a secret to make it a suprise!\n
        With lots of love:
        \tSanta's helper program""".format(sender=senderName.upper(), reciever=recieverName.upper())
        debug.write(senderName + " drew " + recieverName + '\n')    
        mail.send(senderEmail, subject, body)
    return

def main():
    initializeList()
    for x in range(100):
        createEmails(selectNames(names.__len__()))
    return


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.readfp(open(r'santa.conf'))
    masterEmail = config.get('email data', 'masterEmail')
    masterPass = config.get('email data', 'masterPass')
    listFile = config.get('email data', 'listFile')
    main()
    debug.close()