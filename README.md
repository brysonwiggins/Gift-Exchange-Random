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

## Gift idea lists

Each person can keep a Christmas list on the website (for example `https://santa.wiggyserver.com`):

- `/ideas/<name>` is a person's **public, read-only** list. When names are drawn, the giver's email links to their recipient's list.
- `/edit/<secret>` is a person's **private** link for adding, editing and removing items. An item is a title plus an optional link and description. Only someone with the link can change the list.
- `/ideas/` lists everyone.

Lists carry over from year to year, and people remove old items themselves.

### Setup

1. `pip install -r requirements.txt`
2. Add these to `santa.conf` (see `santa.conf.example`):
   ```
   siteUrl = https://santa.wiggyserver.com
   dbFile = santa.db
   ```
   `dbFile` is a SQLite database. The script and the website must use the same file.
   If `siteUrl` is not set, the draw emails go out exactly as before, with no list links.

### Each year

```
python santa-helper-program.py invite   # email everyone their private edit link (a few weeks early)
python santa-helper-program.py          # draw names; emails include the recipient's list link
```

Other commands:

```
python santa-helper-program.py links          # print everyone's view/edit links, no emails
python santa-helper-program.py rotate "Name"  # new edit link for someone (old one stops working)
```

New names in `exchangeList.txt` get their links automatically. Existing people keep the same links every year.

### Running the website

The website is a small Flask app in `webapp/`. Run it with gunicorn from the repo folder:

```
SANTA_CONF=/path/to/santa.conf gunicorn -w 2 -b 127.0.0.1:8050 "webapp.app:create_app()"
```

`deploy/santa-ideas.service` is an example systemd unit. Point your reverse proxy at it.

Caddy:
```
santa.wiggyserver.com {
    reverse_proxy 127.0.0.1:8050
}
```

nginx (add your usual TLS/certbot config):
```
server {
    server_name santa.wiggyserver.com;
    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

To try it locally, run `flask --app "webapp.app:create_app()" run` and use the links printed by `python santa-helper-program.py links`.

Run the tests with `pip install pytest && pytest`.
