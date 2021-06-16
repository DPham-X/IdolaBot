#!/bin/bash
kill $(ps aux | grep "[i]dola_bot.py"   | awk '{print $2}')
