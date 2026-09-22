import os

# Never export telemetry from a test run. Cloud Trace is now the only backend,
# so with application default credentials present a test would write spans
# into the real project alongside production traffic.
os.environ["OTEL_ENABLED"] = "false"

# Unit tests use the bundled fixtures in data/; production defaults to the
# live Geoapify and Open-Meteo lookups, which need a key and a network.
os.environ["TRAVEL_DATA_SOURCE"] = "local"
