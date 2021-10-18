# Discord Bot for IDOLA

[![IdolaBot CI](https://github.com/DPham-X/IdolaBot/actions/workflows/cicd.yml/badge.svg?branch=master)](https://github.com/DPham-X/IdolaBot/actions/workflows/cicd.yml)

Discord bot for SEGA's JP IDOLA.

Use `!help to see the commands`

```md
Commands available:
  arena_border        Shows the border for arena
  arena_roll          Shows what your next symbol roll will be using your are...
  arena_team          Shows the latest ranked arena team for a given profile_...
  arena_top_100       Shows the Top 100 Arena players
  creation_border     Shows the border for Idola Raid Creation
  creation_top_100    Shows the Top 100 Idola Creation players
  find_guild_by_id    Search for open brigades by their Display ID
  find_guild_by_name  Search for open brigades by their brigade name
  guild               Shows brigade information
  guild_by_range      Show top brigades in the leaderboards by range
  guild_top_100       Show the Top 100 brigade
  register_profile    Register an idola profile_id to your discord profile
  soul                Get Soul Symbol information from Bumped
  suppression_border  Shows the border for Idola Raid Suppression
  suppression_top_100 Shows the Top 100 Idola Raid Suppression players
  weapon              Get Weapon Symbol information from Bumped
```

## Installation

    git clone git@github.com:DPham-X/IdolaBot.git
    cd IdolaBot

### Ubuntu 20.04

    make install-ubuntu

Next fill out the idola environment variables (`.env`) located inside `IdolaBot/.env`

Once the environment variables have been filled out run that start script

    make start

## Updating

    make update
