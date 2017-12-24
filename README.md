# schist

Python script to backup shell (zsh, bash) history to a sqlite3 database via cron/launchd. Syncs, merges, and dedupes current state on each run.

## Usage

Run a backup of shell history, (by default, writes the db at `~/.schist.sq3`)


```
# for zsh:

$ schist zsh backup

# for bash:

$ schist bash backup

```

Dump out the complete history in a shell compatible format with 'restore':


```
$ schist zsh restore -
```

Show some stats on the last backup time, and the number of commands over the past hour, day, and week.

```
$ schist zsh stats
```
