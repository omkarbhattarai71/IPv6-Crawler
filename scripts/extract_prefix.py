from collections import Counter

input_file = "../processed/clean_ipv6.txt"
output_file = "../processed/prefix_counts.txt"

counter = Counter()

def ipv6_to_prefix64(ip_str):
    # Split into 8 groups
    parts = ip_str.split(":")
    # Count how many gropus are missing
    if "" in parts:
        # Handle addresses like "::" or "::1" or "2001::"
        empty_index = parts.index("")
        # Remove all empty strings
        parts = [p for p in parts if p!=""]
        # Insert zeros to reach 8 groups
        missing = 8 - len(parts)
        parts = parts[:empty_index] + ["0"] * missing + parts[empty_index:]
    # Convert each group to int
    nums = [int(p, 16) for p in parts]
    # Zero out lower 64 bits (last 4 groups)
    nums[4:] = [0, 0, 0, 0]
    # Rebuild prefix
    prefix = ":".join(f"{n:04x}" for n in nums)
    return prefix + "/64"

with open(input_file) as f:
    for line in f:
        ip = line.strip()
        if not ip:
            continue
        prefix = ipv6_to_prefix64(ip)
        counter[prefix] += 1

with open(output_file, "w") as out:
    for p, c in counter.items():
        out.write(f"{p} {c}\n")
                                                                                                                                
