kill $(ps aux | grep "[p]ython3 idola_bot.py"   | awk '{print $2}')
