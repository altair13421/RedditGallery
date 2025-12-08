# RedditGallery

Technically A Reddit Scrapper?

## Works for:
- images
- galleries
- gifs

## Doesn't Work:
- I think Videos
- UI BAD (Still better than the Initial one I thought)
- Comments aren't there (On Purpose)
- no vpn support (Don't wanna Add it, works for me).

## Other Features:
- Can Add Categories, and Assign Subreddits to these Categories
- Can View These Categories from the Home page (Like I said, UI Bad)
- The Settings Tab will have what these ENVs Set
- Can Excluded From main Gallery (2 Gallery types, the One With the Category only, and the Other Main Gallery)
- Can Bulk Import With and Without Categories

### Without Categories
```json
{
  "subs": ["AnimeWallpaper", "moescape"]
}
```
### With Categories
```json
{
  "subs": {
    "AnimeWallpaper": ["QuickView", "Wallpaper"],
    "moescape": ["Wallpaper"],
    "moesmoking": ["Questionable"]
  }
}
```
