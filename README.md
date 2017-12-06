# Wrangling with OpenstreetMapData of Miami
This work is a part of my projects submitted to the Udacity's Data Analyst Nanodegree Program. The **OpenStreetMap** is a project dedicated to create and freely distribute geographical dat for the planet. I downloaded the osm data (xml format) of Miami from mapzen (https://mapzen.com/data/metro-extracts/metro/miami_florida/85933669/Miami/). Here is a stepwise breakdown of how I did the wrangling and extraction.
1. Load the osm data
2. Parse the xml format to extract the node and way fields (street names, landmarks etc)
3. Writer out the csv files
4. Load the csv files into sqlite database
5. Carry out query and analysis
