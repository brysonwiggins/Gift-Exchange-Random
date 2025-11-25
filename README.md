# Gift-Exchange-Random

A Python program that takes a list of names and emails and randomly assigns each name another person in the list.
It also supports **weighted** assignments using a history file so that people are less likely to draw the same
recipient in consecutive years.

After the selections have been made an email is sent from a Master email that informs each person in the list to whom they have been selected to give a gift.

\*notes

- The Master email must be configured to be able to send emails.
  - You will also need to setup a cloud app in the console in order for your email sepcified to successfully authenticate and send emails.
  - Look up tutorials on using Oauth to sign in and send emails in python. [here is an example](https://mailtrap.io/blog/python-send-email-gmail/)
- santa.conf file with required data must be in the same folder as the python script in order to run.
- inside the config file you will need to set listFile that will determine where the list of participants are being pulled from.
  - This file is a comma separated list name, email followed by a new line.
- (Optional) set `historyFile` inside the config file to point to a CSV file that records past pairings.
  - Each line should be `year,name_of_sender,name_of_recipient`. The year column is only used for
    reference; the algorithm only cares about how many times each pairing has already occurred.
  - The script will append the new assignments to this file after every run and automatically weight
    the random selection so that rarely matched pairs are preferred.
