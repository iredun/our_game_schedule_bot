import pickle
from pprint import pprint

with open("chats_data.dat", "rb") as f:
    data = pickle.load(f)

pprint(data)
