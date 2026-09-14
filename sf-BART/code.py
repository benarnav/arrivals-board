# The whole program lives in arrivals_board.py (shared by every city) and city.py (this city).
# Set debug=True to print every arrivals dictionary and the weather and AQI replies, profile=True for fetch timings.
import arrivals_board
import city

arrivals_board.run(city, debug=False, profile=False)
