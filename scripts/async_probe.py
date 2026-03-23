import asyncio

INPUT = "../results/candidates.txt"
OUTPUT = "../results/responded_predicted_addresses.txt"

CONCURRENCY = 1000  # Point to be noted: we need to increase concurrency value gradually

async def probe(ip):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, 80),
            timeout=0.8
        )
        writer.close()
        await writer.wait_closed()
        return ip
    except:
        return None

async def worker(queue, out):
    while True:
        ip = await queue.get()
        res = await probe(ip)

        if res:
            print(res)
            out.write(res + "\n")
            out.flush()

        queue.task_done()

async def main():
    queue = asyncio.Queue()

    with open(INPUT) as f:
        for line in f:
            queue.put_nowait(line.strip())

    with open(OUTPUT, "a") as out:
        tasks = [
            asyncio.create_task(worker(queue, out))
            for _ in range(CONCURRENCY)
        ]

        await queue.join()

        for t in tasks:
            t.cancel()

asyncio.run(main())
