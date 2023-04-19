# telegram_bot_project_link

-скачаваем nodejs и localtunnel(это нужно для вебхука)
sudo apt-get install nodejs npm
sudo npm install -g localtunnel

-поднимаем URL, потом в файле nohup будет взять URL
nohup lt --port 80 & 

-в адресной строке в браузере нужно поменять url на тот который мы взяли из nohup
https://api.telegram.org/botTOKEN/setWebhook?url=URL

-нужные либы
pip3 isntall aiosqlite
pip3 install aiogram

-установим локаль
sudo locale-gen ru_RU.UTF-8
sudo update-locale

-потом в файле скрипта бота main.py в переменной WEBHOOK_HOST(48 строка) заменить URL на тот, который мы взяли из nohup и запускаем бота
nohup python3 main.py &

-проверить состояние вебхука
https://api.telegram.org/botTOKEN/getWebhookInfo
