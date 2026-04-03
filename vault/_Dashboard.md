# KX Sermon Bank — Staff Dashboard

> **Kings Cross Church** | San Diego, CA | Sermon Archive
> Use the queries below to plan series, avoid repetition, and find sermons for congregants.

---

## Recent Sermons (Last 90 Days)

```dataview
TABLE date, speaker, passage, series
FROM ""
WHERE status = "processed" AND date >= date(today) - dur(90 days)
SORT date DESC
```

---

## Sermons by Bible Book

```dataview
TABLE length(rows) AS "# Sermons"
FROM ""
WHERE status = "processed" AND bible_book != "" AND bible_book != "None"
GROUP BY bible_book
SORT length(rows) DESC
```

---

## Sermon Series

```dataview
TABLE length(rows) AS "# Sermons", min(rows.date) AS "Started", max(rows.date) AS "Last Preached"
FROM ""
WHERE status = "processed" AND series != "Standalone" AND series != ""
GROUP BY series
SORT max(rows.date) DESC
```

---

## All Speakers

```dataview
TABLE length(rows) AS "# Sermons", max(rows.date) AS "Last Preached"
FROM ""
WHERE status = "processed"
GROUP BY speaker
SORT length(rows) DESC
```

---

## Passages Preached (All Time)

```dataview
TABLE date, speaker, series
FROM ""
WHERE status = "processed" AND passage != "" AND passage != "None"
SORT date ASC
```

---

## Sermons by Year

```dataview
TABLE length(rows) AS "# Sermons"
FROM ""
WHERE status = "processed"
GROUP BY dateformat(date, "yyyy")
SORT dateformat(date, "yyyy") DESC
```

---

## All Theological Tags Used

```dataview
TABLE length(rows) AS "# Sermons"
FROM #grace OR #justification OR #holy-spirit OR #prayer OR #suffering OR #discipleship OR #resurrection OR #atonement OR #faith OR #repentance OR #evangelism OR #sanctification
WHERE status = "processed"
GROUP BY file.tags
SORT length(rows) DESC
```

---

## Finding Sermons for a Congregant

Use Obsidian's **tag search** (`Ctrl+Shift+F`) to search by:
- A life situation: `#suffering`, `#anxiety`, `#marriage`, `#grief`
- A doctrine: `#justification`, `#grace`, `#atonement`
- A book of the Bible: `#New-Testament/Romans`, `#Old-Testament/Psalms`

Or use the **_Index** notes below for browsing:
- [[_Index/By Series]]
- [[_Index/By Speaker]]
- [[_Index/Topics Index]]
