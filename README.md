# BeaconDex Platinum

BeaconDex Platinum is a source-based Pokémon Platinum ROM hack built on the
[`pret/pokeplatinum`](https://github.com/pret/pokeplatinum) decompilation.

The project targets the US Rev 1 release (`CPUE`, ROM version `1`). The clean
source baseline reconstructs this ROM exactly:

```text
SHA-1  0862ec35b24de5c7e2dcb88c9eea0873110d755c
Size   134217728 bytes
```

Development is organized around these goals:

- make every NPC trainer encounter a Double Battle;
- offer six starters and let the player select two different partners;
- add all 63 BeaconDex species without replacing the original roster;
- distribute those species through Sinnoh's encounters and trainer teams;
- preserve Platinum's story and progression; and
- support complete species data, graphics, evolution, Pokédex, and saving.

See [`INSTALL.md`](INSTALL.md) for the upstream build prerequisites. Project
specific setup, source decisions, and validation records live in
[`docs/beacondex`](docs/beacondex).

This repository contains source and build tooling. It does not distribute a
commercial Pokémon Platinum ROM.
