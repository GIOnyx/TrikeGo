import openrouteservice
from django.conf import settings
from .models import RouteSnapshot, DriverLocation
from decimal import Decimal
import math

class RoutingService:
    def __init__(self):
        # Get your API key from https://openrouteservice.org/dev/#/signup
        self.api_key = getattr(settings, 'OPENROUTESERVICE_API_KEY', 'YOUR_API_KEY_HERE')
        self.client = openrouteservice.Client(key=self.api_key)
    
    def calculate_route(self, start_coords, end_coords, profile='driving-car'):
        """
        Calculate route between two points
        
        Args:
            start_coords: tuple (longitude, latitude)
            end_coords: tuple (longitude, latitude)
            profile: 'driving-car', 'cycling-regular', 'foot-walking'
        
        Returns:
            dict with route_data, distance (km), duration (seconds)
        """
        try:
            coords = [start_coords, end_coords]
            route = self.client.directions(
                coordinates=coords,
                profile=profile,
                format='geojson',
                geometry='true',
                instructions='true'
            )
            
            # Extract route information
            distance = route['features'][0]['properties']['segments'][0]['distance'] / 1000  # Convert to km
            duration = route['features'][0]['properties']['segments'][0]['duration']  # in seconds
            
            return {
                'route_data': route,
                'distance': round(distance, 2),
                'duration': int(duration)
            }
        except Exception as e:
            print(f"Routing error: {e}")
            return None
    
    def save_route_snapshot(self, booking, route_info):
        """Save route snapshot to database"""
        # Deactivate previous routes
        RouteSnapshot.objects.filter(booking=booking, is_active=True).update(is_active=False)
        
        # Create new route snapshot
        snapshot = RouteSnapshot.objects.create(
            booking=booking,
            route_data=route_info['route_data'],
            distance=Decimal(str(route_info['distance'])),
            duration=route_info['duration'],
            is_active=True
        )
        return snapshot
    
    def should_reroute(self, driver_location, current_route, threshold_meters=100):
        """
        Determine if rerouting is needed based on driver's deviation from route
        
        Args:
            driver_location: DriverLocation object
            current_route: RouteSnapshot object
            threshold_meters: deviation threshold in meters
        
        Returns:
            bool: True if rerouting is needed
        """
        if not current_route or not current_route.route_data:
            return True
        
        try:
            # Get route coordinates
            route_coords = current_route.route_data['features'][0]['geometry']['coordinates']
            driver_point = (float(driver_location.longitude), float(driver_location.latitude))
            
            # Find minimum distance to route
            min_distance = float('inf')
            for coord in route_coords:
                distance = self._haversine_distance(
                    driver_point[1], driver_point[0],
                    coord[1], coord[0]
                )
                min_distance = min(min_distance, distance)
            
            return min_distance > threshold_meters
        except Exception as e:
            print(f"Error checking route deviation: {e}")
            return False
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_eta(self, driver_location, destination_coords):
        """Calculate estimated time of arrival from driver's current location"""
        driver_coords = (float(driver_location.longitude), float(driver_location.latitude))
        route_info = self.calculate_route(driver_coords, destination_coords)
        
        if route_info:
            return route_info['duration']  # in seconds
        return None