import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart' as geo;

class LocationData {
  final double latitude;
  final double longitude;
  final String address;
  final double accuracy;

  LocationData({
    required this.latitude,
    required this.longitude,
    required this.address,
    required this.accuracy,
  });
}

class LocationService extends ChangeNotifier {
  LocationData? _currentLocation;
  bool _isTracking = false;

  LocationData? get currentLocation => _currentLocation;
  bool get isTracking => _isTracking;

  Future<void> startLocationTracking() async {
    try {
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        await Geolocator.requestPermission();
      }

      final Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.best,
      );

      // Get address from coordinates
      List<geo.Placemark> placemarks = await geo.placemarkFromCoordinates(
        position.latitude,
        position.longitude,
      );

      String address = 'Unknown location';
      if (placemarks.isNotEmpty) {
        final p = placemarks.first;
        address =
            '${p.street}, ${p.locality}, ${p.postalCode}, ${p.country}';
      }

      _currentLocation = LocationData(
        latitude: position.latitude,
        longitude: position.longitude,
        address: address,
        accuracy: position.accuracy,
      );

      _isTracking = true;
      notifyListeners();
    } catch (e) {
      print('Location error: $e');
    }
  }

  Future<void> shareLocation() async {
    if (_currentLocation != null) {
      // Would call API to share location with authorities
      print('Location shared: ${_currentLocation!.latitude}, ${_currentLocation!.longitude}');
    }
  }

  void stopTracking() {
    _isTracking = false;
    notifyListeners();
  }
}
