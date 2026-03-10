import ipaddress
from tqdm import tqdm
from bisect import bisect_right

alias_file = "../dataset/latest-data/apd/2026-02-12-aliased.txt"
input_file = "../dataset/latest-data/input/2026-02-12-input.txt"
output_file = "../processed/clean_ipv6.txt"

print("Loading aliased prefixes...")

# Convert prefixes to (start_int, end_int) ranges
ranges = []
with open(alias_file) as f:
    for line in f:
        prefix = line.strip()
        if not prefix:
            continue
        try:
            net = ipaddress.ip_network(prefix)
            start = int(net.network_address)
            end = int(net.broadcast_address)
            ranges.append((start, end))
        except:
            continue

# Sort by start address for binary search
ranges.sort()

# Extract only the start values for bisect
starts = [r[0] for r in ranges]
print("Filtering addresses...")

def is_aliased(ip_int):
    """Binary search to find if ip_int falls inside any prefix range."""
    idx = bisect_right(starts, ip_int) - 1
    if idx >= 0:
        start, end = ranges[idx]
        return start <= ip_int <= end
    return False

with open(input_file) as f, open(output_file, "w") as out:
    for line in tqdm(f):
        raw = line.strip().split()[0]

        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue  # skip malformed lines

        ip_int = int(ip)
        if not is_aliased(ip_int):
            out.write(str(ip) + "\n")

