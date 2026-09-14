# Read me
---
This project consists of 2, one python part is a scrapper fetching infos about the game's objects to build a "database". This is then used in the c++ project to build a graph corresponding to the required criteria set when launching the app. (args: path/to/db.js {name/item-id} amount_per_min) < use item-id instead of name for multi name items (like Gold Ingot) or use "" to encapsulate.
---
Current state:

Scrape.py (currently the main for the python scrapper) should work as intended, modify the "HEADERS" var in fetch.py to not use the default config of the UserAgent. It caches the pages data that and are sent in "./cache". The json output is sent to "./Data".

There is a POC of the app to test and plan stuff out.
