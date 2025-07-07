import os

import praw
import requests
import json
from bs4 import BeautifulSoup as bs
from concurrent.futures import ThreadPoolExecutor, as_completed

limit = 1000
workers = 10

