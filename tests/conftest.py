import os

# Unit tests use the bundled fixtures in data/; production defaults to the
# live Geoapify and Open-Meteo lookups, which need a key and a network.
os.environ["TRAVEL_DATA_SOURCE"] = "local"
