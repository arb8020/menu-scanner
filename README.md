# OVERVIEW
i get decision fatigue when there's too many options on a menu.

so i wanted to make a little app to scan a menu, write questions for me, and then tell me what to order. 

## KEY FILES
- node.js with express for backend
- html/css/js for the frontend
- worker.py just wraps gpt to generate transcripts of the menu
- and then generates the questions/recommendations
- redis handles the job queue and storing data

## USAGE
- clone repo
- npm/pip install dependencies
- put your api key in a .env
- start the redis server
- start the node server
- start your python worker
- go to port 3000 on localhost or wherever you're running this
