# Arrivals Board for NYC Subway

These files power a 64x32 RGB matrix display that shows arrival times for the New York City Subway or the Washington DC Metro Rail. I am currently using an Adafruit Matrixportal S3 micocontroller. It was vaguely inspired by Tidbyt products, but mostly just the form factor. 

## Overview
New York City has the most extensive public transportation system in the United States, but due to its age (over 100 years old!) it is frequently in need of major maintenance which disrupts or delays service. To avoid needlessly waiting for trains on the platform, this display shows the next two trains traveling in one direction (the way I'm usually going) from the station closest to my apartment. Pushing the built-in `Up` button on the microcontroller displays the next `four` trains going in both directions.

The default screen also shows the time, temperature and AQI level. The AQI icon is color coded to signal the recommendations put out by the [US gov](www.airnow.gov). The subway line icons (known as 'bullets' in official parlance), will flash an alert symbol if the transit agency has issued an alert for that line. Pushing the onboard `Down` button will scroll the alerts along the bottom of the display.

Originally, I used an Adafruit Matrixportal M4, but it doesn't have enough memory for all the information and would frequently crash. I also would like to add additional functionality, so the additional memory is necessary. 

## Note on data
The NYC Subway API uses protocol buffers for their data. The packages needed to decode the datafeeds are too large for a microconroller, so I built a simple `Flask` app that prepares the data for the display. That app is hosted on [Python Anywhere](www.pythonanywhere.com). This setup only requires you obtain a [free API key](https://new.mta.info/developers) from the MTA. Specifying the subway lines and station info that's displayed is handled by headers in the API call to the Flask app.

The Washington DC Metro implementation currently has data for the next `three` trains in both directions using WMATA's json API. This also requires a [free API key](https://developer.wmata.com). 

## Future Plans
I've been thinking about adding a dial that would allow switching between more than just two screens, but I haven't thought of what other sort of information I'd like to display. I'd also like to add support for other transit agencies, so if you live in a city where this would be useful, please contribute!

## License
This project is licensed under the [GNU v3](LICENSE).