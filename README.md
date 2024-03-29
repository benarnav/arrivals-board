# Arrivals Board for NYC Subway

These files power a 64x32 RGB matrix display that shows arrival times for the New York City Subway or the Washington DC Metro Rail. I am currently using an Adafruit Matrixportal S3 micocontroller. It was vaguely inspired by Tidbyt products, but mostly just the form factor. 

<img src="/example.jpg" alt="example">


## Overview
New York City has the most extensive public transportation system in the United States, but due to its age (over 100 years old!) it is frequently in need of major maintenance which disrupts or delays service. To avoid needlessly waiting for trains on the platform, this display shows the next two trains traveling in one direction (the way I'm usually going) from the station closest to my apartment. Pushing the built-in `Up` button on the microcontroller displays the next `four` trains going in both directions.

The default screen also shows the time, temperature and AQI level. The AQI icon is color coded to signal the recommendations put out by the [US gov](www.airnow.gov). The subway line icons (known as 'bullets' in official parlance), will flash an alert symbol if the transit agency has issued an alert for that line. Pushing the onboard `Down` button will scroll the alerts along the bottom of the display.

Originally, I used an Adafruit Matrixportal M4, but it doesn't have enough memory for all the information and would frequently crash. I also would like to add additional functionality, so the additional memory is necessary. 

## Note on data
The NYC Subway and Washington DC Metro use protocol buffers for their data. The packages needed to parse the datafeeds are too large for a microconroller, so I built a simple `Flask` app that prepares the data for the display. That app is hosted on [Python Anywhere](www.pythonanywhere.com). This setup only requires you obtain a [free API key](https://new.mta.info/developers) from the MTA or [WMATA](https://developer.wmata.com). Specifying the subway lines and station that's displayed is handled by headers in the API call to the Flask app.

NYC Subway routes are organized into two travel directions: North and South and looking at a map this is fairly easy to figure out which direction you would want displayed. Washington DC's Metro is a little more complex and in the official data feed trains are listed as direction 0 or direction 1. I have mapped these to roughly trains that end in the North or East and ones that end in the South or West.

## Future Plans
I've been thinking about adding a dial that would allow switching between more than just two screens, but I haven't thought of what other sort of information I'd like to display. I'd also like to add support for other transit agencies, so if you live in a city where this would be useful, please contribute! 

This would only require and additional two classes in `transit_api.py` to create a new endpoint and a class to parse the data, and an updated class in the `code.py` to correctly display the data. Also, an additional dictionary would need to be added to `station_dict.py` to map stop_id to station names. This allows each train to be associated with a terminal station, which can be useful for future functionality. 

## License
This project is licensed under the [GNU v3](LICENSE).