from .distance import calculate_distance

BASE_FARE = 40     
PER_KM_RATE = 15   
def calculate_fare(lat1, lon1, lat2, lon2):
    
    distance_km = calculate_distance(lat1, lon1, lat2, lon2)
    total_fare = BASE_FARE + (PER_KM_RATE * distance_km)
    return round(total_fare, 2)
