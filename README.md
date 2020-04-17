# term-project
A web crawler to show load speeds of different domains

## Overview
> Gerhard van Andel - Project Overview

The goal for this project is to scrape the web and show response time differences.

![diagram][diagram]

Using distributed processing to scape the web

A specific list of software and hardware components
+ `Redis` - used as a data store for search data
+ `RabbitMQ` - give tasks (web-site urls) to then read and parse
+ `contoller` - flask web service to request web site crawling to and search requests
+ `web_bots` - takes a task off of RabbitMQ (web-site urls) to then search
+ `scan_bots` - takes a task off of RabbitMQ (web-data blocks) to scan for more links and then update
+ `cleaner` - takes items off of the cache and moves them to storage

[diagram]: /term-project.png "Diagram"

