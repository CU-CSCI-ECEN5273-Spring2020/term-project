# Contoller

### API

#### Add url to scrape

+ Endpoint: `/api/url` [POST]
+ Body: ```[ "www.google.com", "www.yahoo.com" ]```
+ Response: ```[ "12345678-1234-5678-1234-567812345678", "12345678-1234-5678-1234-567812345679" ]```

#### Get the status of a search

+ Endpoint: `/api/url/<uuid>` [GET] 
+ Body: ``` ```
+ Response ``` { "uuid": "12345678-1234-5678-1234-567812345678", "topic": "cats", "data": "gs://mybucket/myfolder/12345678-1234-5678-1234-567812345678.html", "url": "https://cats.stackexchange.com/cats"} ```


#### See if a url is in the database

+ Endpoint: `/api/search?query=cats` [GET] 
+ Body: ``` ```
+ Response: ``` [ {"url": "https://cats.stackexchange.com/cats", "short": "Blaa Blaa Blaa cats...", "monetized": true } ] ```
