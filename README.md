# TG Budget Bot

Telegram Bot for collecting our expenses by using API of an app "Проверка чека"

## Prepare

Run this inside project folder to install project requirements

```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

After that you need to configure enviromental variables in .env file (as in .env.example)

You need to get your telegram bot token via @BotFather and authorization token for your google account (see pygsheet authorization docs for instructions)

Complete all other values in that file in a way you need

If something will be unclear feel free to send an email

## Systemctl service
To run bot as service on linux server you can fill blanks (<...>) in tg-bot.service.example file and then run this 3 commands in bash terminal inside project dir

```
sudo cp tg-bot.service.example /lib/systemd/system/tg-bot.service
sudo systemctl start tg-bot.service
sudo systemctl enable tg-bot.service
```