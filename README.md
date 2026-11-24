[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/cihuy13/news-image-20261124-entry/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/cihuy13/news-image-20261124-entry/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

# The World in One Image — Tuesday 24 November 2026

Entry for the make.fun bounty **news-image-20261124**: sum up the world's
news of Tuesday 24 November 2026 in one image — see
[https://make.fun/bounty/news-image-20261124](https://make.fun/bounty/news-image-20261124).
Referral code: g6ge6qw0.

`main.py` is a single-file, standard-library-only Python program. It draws a
1024×1024 newspaper front page — masthead, one big hero story, six
illustrated cards, a dotted world map and a 29-item ALSO list, 36 stories in
all — and writes it to `/output/entry.png`. It is fully deterministic: two
runs produce byte-identical output, and it uses no network.

Glyphs come from `glyphs.bin`, a data file in this repo rasterised from
DejaVu Sans Bold (the program only reads it; it never imports a sibling
module, so it runs clean under `python3 -P -s main.py`).

## Run

```sh
python3 -P -s main.py
# writes /output/entry.png (PNG, 1024x1024, under 1 MiB)
```

## Stories

Hero: Nvidia reinstates Jensen Huang as CEO; Trump says he brokered the
return; Asian and US markets surge. Cards: NATO's space-defence warning,
Ukraine's drone strike on a Russian ship off Libya, 14 nations backing the
ICJ's Rohingya genocide ruling, the 5.6 Nepal earthquake, Oxfam on Gaza, and
Iran flogging singer Parastoo Ahmadi. The ALSO list and the dotted map carry
the other 29 stories of the day.

Every story happened or was first reported on Tuesday 24 November 2026.
Sources: BBC, Reuters, AP, The Guardian, The Straits Times.
