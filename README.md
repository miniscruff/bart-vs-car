# Bart Vs Car
Compare the efficiency of riding BART versus driving a car.

## How to run
1. Run a local server using python: `python3 -m http.server`


## How to fetch data
1. Configure environment:
    1. Can create `.env` file or export env vars
    1. `BART_API_KEY` from [BART API](https://api.bart.gov/api/register.aspx)
    1. `GRAPH_HOPPER_API_KEY` from [Graph Hopper](https://graphhopper.com/dashboard/#/signup)
1. Create virtual env: `python -m venv venv`
1. Activate virtual env: `source venv/bin/activate` ( on linux )
1. Install packages: `pip install -r requirements.txt`
1. Run fetch, and wait: `python fetch.py`
