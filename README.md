# schist

![travis-ci](https://travis-ci.org/slyphon/schist.svg?branch=master)

Python script to backup shell (zsh, bash) history to a sqlite3 database via cron/launchd. Syncs, merges, and dedupes current state on each run.

## y tho

<blockquote class="twitter-tweet" data-lang="en"><p lang="und" dir="ltr"> <a href="https://t.co/Te7E179UQ9">pic.twitter.com/Te7E179UQ9</a></p>&mdash; Berk D. Demir (@bd) <a href="https://twitter.com/bd/status/945038934970531840?ref_src=twsrc%5Etfw">December 24, 2017</a></blockquote>
<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>


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
