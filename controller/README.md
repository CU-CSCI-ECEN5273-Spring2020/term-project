# Contoller

### API

#### Add url to scrape

+ Endpoint: `/api/url` [POST]

+ Body: 

```json
{"url": "https://yahoo.com/"}
```

+ Response:

```json
{
  "correlation": "6156d421-eae8-468f-8ef0-f11ecc4df263",
  "data": [
    {
      "depth": 1,
      "domain": "yahoo.com",
      "path": "/",
      "scheme": "https",
      "timestamp": "2020-04-17T02:54:03.454660Z",
      "type": "spider",
      "url": "https://yahoo.com/"
    }
  ],
  "identifier": "6156d421-eae8-468f-8ef0-f11ecc4df263",
  "status": "queued"
}
```

#### Get the stats of the search

+ Endpoint: `/api/url/<uuid>` [GET] 

+ Response 

```json
{
  "data": [
    {
      "duration": 0.227436,
      "timestamp": "2020-04-17T02:54:16.267082",
      "url": "https://yahoo.com/"
    },
    {
      "duration": 0.110447,
      "timestamp": "2020-04-17T02:54:51.104898",
      "url": "https://mail.yahoo.com/?.src=fp"
    },
    {
      "duration": 0.08498,
      "timestamp": "2020-04-17T02:55:12.614959",
      "url": "https://mail.yahoo.com/?.src=fp"
    },
    {
      "duration": 0.228778,
      "timestamp": "2020-04-17T02:54:40.453677",
      "url": "https://login.yahoo.com/config/login?.src=fpctx&.intl=us&.lang=en-US&.done=https://www.yahoo.com"
    },
    {
      "duration": 0.261513,
      "timestamp": "2020-04-17T02:54:29.257328",
      "url": "https://www.yahoo.com/"
    },
    {
      "duration": 0.210599,
      "timestamp": "2020-04-17T02:55:02.082195",
      "url": "https://login.yahoo.com/config/login?.src=fpctx&.intl=us&.lang=en-US&.done=https://www.yahoo.com"
    }
  ],
  "status": "OK",
  "total": 6
}

```


#### See if a url is in the database

+ Endpoint: `/api/url/<identifier>` [GET] 
+ Body: ``` ```
+ Response:
```json
{
  "correlation": "6156d421-eae8-468f-8ef0-f11ecc4df263",
  "data": [
    {
      "depth": 1,
      "domain": "yahoo.com",
      "path": "/",
      "scheme": "https",
      "timestamp": "2020-04-17T02:54:03.454660Z",
      "type": "spider",
      "url": "https://yahoo.com/"
    },
    {
      "code": 200,
      "depth": 2,
      "local": "gs://bucket/html/6156d421-eae8-468f-8ef0-f11ecc4df263.html",
      "method": "GET",
      "time": 0.227436,
      "timestamp": "2020-04-17T02:54:03.492393Z",
      "type": "scan"
    },
    {
      "data": {
        "links": [
          "0ba29fb7-7550-4d59-97b1-ca5423fb2eb3",
          "e990300d-590a-4125-a930-be52716a457c",
          "9d059740-2f26-44ad-8ebd-fe97c66adddc",
          "e2ebd780-99e4-49d6-9d45-fb810aee0781",
          "6d2c1155-ec63-4316-a744-0a5f304d53dc",
          "e91623fb-4fea-4d80-9a8a-5f5a16b9d4cd",
          "58587f08-74fa-4a96-8ff7-196efb07e11b",
          "d2852757-b0a6-470e-90da-b78f8e57d844",
          "5c701653-7b02-4be3-abb2-073ff3c8b459",
          "4af3953a-288e-4032-8ef9-6757bc374e36",
          "b21109c6-607b-4680-9415-32af27fb7d48",
          "77498e45-68e5-4af2-ac84-4f898217df0d",
          "488769c8-ad98-4d53-9c45-62b5edfa273e",
          "27430bc7-a592-47e4-8786-133f090df173",
          "9e49ccff-a73a-424c-be46-a45366c06db4",
          "5799174c-2b3f-4850-bc2a-bc7c1040da10",
          "fff27114-7c6a-45d0-a79e-f95a99595edc",
          "be0a240e-9aed-4fbc-a590-9e2b6f770491",
          "9822a642-e06e-46c0-a6a7-65906da0e8d1",
          "1583383a-0979-406c-91eb-a2f87294460c",
          "b2710917-18e2-4003-9245-0a0a9fe9ba13",
          "ac6dc188-2e1c-4623-962f-1901c935ca51",
          "51deb495-84da-4e97-b891-9fa6cb07e5a8",
          "01a60ebc-93b5-4fe1-b4f8-7fdf868d2328",
          "8406d391-59da-40c2-b750-8add516bd6ad",
          "1f934503-83d5-4b7d-9894-7a6f7f81ab29",
          "78a7e083-4b53-4860-8d9b-3fbc4606fb4f",
          "2c968fc7-6c14-4e61-bcfa-655da7a54b23",
          "145c7b0f-9c92-4e06-8a79-e21567dbb620",
          "96fff8d3-653c-4028-892b-db06ac58615c",
          "0321c920-b110-496f-9413-8382ab29c46d",
          "f5ea07d5-456a-4bcb-8279-2ca5462f78ef",
          "daa857f5-5c4d-46b5-bde4-7d3fa4514bf2",
          "a60ca3ca-3c3f-4b5a-851c-bc338e063f50",
          "dafe9b05-d0f9-4072-b73b-b47be9bfc680",
          "67c0807c-47a4-42b5-bca4-fc58dd502ba2",
          "ea945c9c-864a-4d83-b437-e6d14070b17e",
          "809f120b-bddc-4671-92e7-c254e207b383",
          "1636592f-8d04-4d99-b2c6-8e6c8de5cf55",
          "78749dc4-0ec1-405b-8251-e69445b8b9c8",
          "050a4f07-00e1-4e46-9ad3-e4a423210daf",
          "85cb59b9-46b4-441c-a252-a4064c1c8417",
          "f6a4b6f2-d4cc-423f-ae13-a8c757acd0e9",
          "72c79ca2-555b-4eb8-b87b-e8cd6889e170",
          "0f3f69db-cc32-4496-88da-dd1690d863d2",
          "770efa13-4874-4e6c-ad50-15260b2da51f",
          "b6d03b10-2115-4df7-989b-f0729760cb87",
          "d36eaa0a-d2e3-4996-bfb2-52aad68d7ed1",
          "40c127d4-f5bc-41f1-887b-8835bae2d759",
          "73c78b8b-d1f5-4973-a406-51fc92ddc979",
          "41d6a0ce-32ef-43f9-b6b3-56a0f61e9d72",
          "fc2b9e5d-19ce-4ed0-9d2b-c564d31fb9fc",
          "ff96642b-b490-420a-a777-094671d401e8",
          "4cbfdf4e-d27e-428e-8cd0-26d1232d49fb",
          "35e59e9a-9ab1-4c36-997d-27b1d3a10c03",
          "11c1be58-7a61-4534-8c60-4489f87adec0",
          "32b44634-351a-41ad-8aed-5bbfed5dc69d",
          "46202ab4-a008-4a28-9206-5dbe62456306",
          "798be6d5-0363-45af-adfe-3cc87e68f785",
          "e62ffa79-9f18-4e57-8556-da4dcbf04816",
          "62df94fb-6287-4890-b98f-c86dbbef96a5",
          "c37a1260-a389-4e31-821f-0dc41a8d1670"
        ],
        "title": "Yahoo"
      },
      "timestamp": "2020-04-17T02:54:17.176013Z",
      "type": "scan"
    }
  ],
  "identifier": "6156d421-eae8-468f-8ef0-f11ecc4df263",
  "status": "cleanup-complete"
}
```

#### Queues

+ Endpoint: `/api/queues` [GET]

+ Response:

```json
{
  "queues": [
    {
      "count": 772,
      "queue": "spider_queue"
    },
    {
      "count": 0,
      "queue": "scan_queue"
    },
    {
      "count": 0,
      "queue": "cleanup_queue"
    }
  ],
  "status": "OK",
  "total": 772
}
```