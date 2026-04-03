# Sermons by Series

```dataview
TABLE date, speaker, passage, file.link AS "Sermon"
FROM ""
WHERE status = "processed" AND series != "Standalone" AND series != ""
SORT series ASC, date ASC
```

---

## Standalone Sermons (No Series)

```dataview
TABLE date, speaker, passage, file.link AS "Sermon"
FROM ""
WHERE status = "processed" AND (series = "Standalone" OR series = "")
SORT date DESC
```
