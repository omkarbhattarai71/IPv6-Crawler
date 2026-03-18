input_file = "../processed/prefix_counts.txt"
output_file = "../processed/features.csv"

with open(input_file, buffering=1024*1024) as f, \
     open(output_file, "w", buffering=1024*1024) as out:

    out.write("prefix,density\n")

    for line in f:
        line = line.strip()
        if not line:
            continue

        space = line.find(" ")
        if space == -1:
            continue

        prefix = line[:space]
        density = line[space+1:]

        out.write(prefix + "," + density + "\n")

print("Features created")
