---
name: music-store-assistant
description: Database schema and business logic for the music store data analysis including artists, albums, and tracks.
---
# Music Store Analytics Schema

## Tables

### Artist
- ArtistId (PRIMARY KEY)
- Name

### Album
- AlbumId (PRIMARY KEY)
- Title
- ArtistId (FOREIGN KEY -> Artist)

### Track
- TrackId (PRIMARY KEY)
- Name
- AlbumId (FOREIGN KEY -> Album)
- MediaTypeId (FOREIGN KEY -> MediaType)
- GenreId (FOREIGN KEY -> Genre)
- Composer
- Milliseconds
- Bytes
- UnitPrice

## Business Logic

**Albums per Artist**: To get the number of albums an artist has, join the Artist table with the Album table on ArtistId.
**Tracks per Album**: Join Album and Track on AlbumId.

## Example Query

-- Give me all artists with more than 1 album
SELECT a.Name, COUNT(al.AlbumId) as AlbumCount
FROM Artist a
JOIN Album al ON a.ArtistId = al.ArtistId
GROUP BY a.ArtistId, a.Name
HAVING COUNT(al.AlbumId) > 1;
