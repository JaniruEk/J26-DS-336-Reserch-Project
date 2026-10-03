import os
import urllib.request

os.makedirs("data", exist_ok=True)
urllib.request.urlretrieve(
    "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite",
    "data/chinook.db")
print("saved data/chinook.db")
