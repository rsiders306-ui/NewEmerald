# Offline Battle Frontier doubles

The Tower, Castle, Arcade, Factory, and Hall now use native Frontier Double
Battle types for their solo challenge flows. Their logical Single challenge IDs
remain in place because those IDs control Frontier Brain scheduling, streaks,
prints, BP, dialogue, and record buckets.

Tower Single, Wi-Fi, and mode 5 join its existing Double format. Castle, Arcade,
and Factory Single flows join their existing Double format. These facilities
already construct three Pokémon per solo side, so no save or party expansion is
needed.

The Hall now requires and selects two eligible Pokémon of the same species for
its main record ladder. It persists both selections, supplies both to the Hall
app, generates two opponent sets, constructs each opponent from its own set,
and uses the higher selected level for Matron scaling. The existing two-slot
Hall storage is sufficient, so the save structure does not grow for this change.
The legacy Hall ladder is labeled `STANDARD DOUBLE`; its separate Double record
bucket remains available.

Fairy stays outside the Hall's fixed 17 selectable type categories. Fairy
Pokémon can participate through their other type or the legacy category logic,
while the nine-byte rank field remains unchanged.

All affected C units, the Hall script, text, and the complete ROM compile.
`tools/beacondex/frontier_doubles_audit.py` protects the reviewed format,
selection, opponent-index, and party-size markers. Emulator testing remains for
normal and Brain battles, Hall quicksave/resume, held-item restoration, and
record updates. A vanilla save suspended inside an old one-Pokémon Hall run has
no intentional second selection and should start a new challenge.
