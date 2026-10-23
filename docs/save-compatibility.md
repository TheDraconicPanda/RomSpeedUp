# European to US save investigation

Status: not tested. No European save or USA ROM is available in this environment.
A patched ROM is not a save. Do not assume a successful boot proves save safety.

The US disassembly's `src/save.c` uses chunk footers, counters and validation;
`src/player_data.c` records language and version in player data. Those facts are
consistent with needing format/language checks; they do not establish every
European language/version can be transferred safely. No live conversion code or
region-byte edits are authorized by this project's patch design.

1. Export an in-game battery save from Delta. Keep the original save, original ROM
   and any emulator state separate. A save state is emulator/version dependent;
   it is not interchangeable with a raw battery save. DeSmuME `.dsv` may wrap raw
   data with metadata; use the emulator's supported export/import, not truncation.
2. Make two byte-identical backups; record SHA256, size, original game code,
   European language/revision and emulator version. Copy to an ignored `private/`
   folder. Never point the USA test at the only copy of a save.
3. Import a disposable copy through the US emulator's supported battery-save
   interface. Keep emulator-created filenames separate for stock, v3 and v4.
4. Check Continue trainer/time/badges, location, party/PC species, stats, moves,
   nicknames, accents, bag, Pokédex and story flags. Test battle, storage and map
   transitions. Save in game, restart and reload; check for repair/corruption text.
5. Export the USA-written save and test a **copy** on the original European game.
   Compare parsed semantic data and progression. Save counters, RTC and playtime
   can change without indicating incompatibility. Preserve all originals.
6. Record exact successful combinations. A pass on one English EU save does not
   establish all European languages/revisions, link modes or emulator containers.

Without these results, compatibility remains an explicit release blocker rather
than a promise. Selective timing patches must never edit save layout or data.
