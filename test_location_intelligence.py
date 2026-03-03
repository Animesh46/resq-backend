import asyncio

from modules import location_intelligence


async def run():
    print("== resolve_city_input tests ==")
    for inp in ["Chennai", "chennai downtown", "Madurai", "unlistedcity"]:
        resolved = location_intelligence.resolve_city_input(inp)
        print(f"{inp!r} -> {resolved!r}")

    print("\n== vulnerable areas ==")
    ch = await location_intelligence.get_vulnerable_areas("chennai", "flood")
    print("chennai flood", ch[:2])
    mu = await location_intelligence.get_vulnerable_areas("madurai", "flood")
    print("madurai flood", mu)

    print("\n== safe locations ==")
    chs = await location_intelligence.get_safe_locations("chennai", "flood")
    print(chs[:2])
    mus = await location_intelligence.get_safe_locations("madurai", "flood")
    print(mus)


if __name__ == "__main__":
    asyncio.run(run())
