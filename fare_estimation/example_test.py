from fare_estimation.fare import calculate_fare

# Example: From Cebu IT Park to Colon Street
lat1, lon1 = 10.3276, 123.9181  # IT Park
lat2, lon2 = 10.2956, 123.8986  # Colon Street

fare = calculate_fare(lat1, lon1, lat2, lon2)
print(f"Estimated Fare: PHP {fare}")
