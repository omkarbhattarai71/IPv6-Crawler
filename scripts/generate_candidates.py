import joblib
import pandas as pd
import random
import ipaddress

model = joblib.load("../models/prefix_model.pkl")
data = pd.read_csv("../processed/features.csv")

data["log_density"] = data["density"].apply(lambda x: __import__("math").log1p(x))

pred = model.predict(data[["density", "log_density"]])
candidates = data[pred == 1]

MAX_PREFIXES = 100000
OUTPUT = "../results/candidates.txt"

patterns = [1, 2, 80, 443, 8080, 0x100, 0x200]

with open(OUTPUT, "w") as out:
    for prefix in candidates["prefix"][:MAX_PREFIXES]:
        net = ipaddress.ip_network(prefix)
        base = int(net.network_address)

        # pattern-based (HIGH VALUE)
        for p in patterns:
            out.write(str(ipaddress.IPv6Address(base + p)) + "\n")

        # biased random (MEDIUM VALUE)
        for _ in range(30):
            rand_int = random.choice([
                random.randint(0, 2**16),
                random.randint(0, 2**32),
                random.getrandbits(64)
            ])
            out.write(str(ipaddress.IPv6Address(base + rand_int)) + "\n")

print("Candidates generated")
                                                                          
