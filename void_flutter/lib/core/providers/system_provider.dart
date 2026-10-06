import 'dart:async';
import 'package:flutter/material.dart';
import '../models/telemetry_data.dart';
import '../network/api_service.dart';

class SystemProvider with ChangeNotifier {
  final ApiService _apiService;
  TelemetryData _telemetry = TelemetryData();
  bool _isLoading = false;
  Timer? _telemetryTimer;

  SystemProvider(this._apiService);

  TelemetryData get telemetry => _telemetry;
  bool get isLoading => _isLoading;

  void startTelemetryPolling() {
    _telemetryTimer?.cancel();
    fetchStats();
    _telemetryTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      fetchStats();
    });
  }

  void stopTelemetryPolling() {
    _telemetryTimer?.cancel();
    _telemetryTimer = null;
  }

  Future<void> fetchStats() async {
    final stats = await _apiService.getSystemStats();
    _telemetry = stats;
    notifyListeners();
  }

  Future<String> executePhoneAction(String command) async {
    _isLoading = true;
    notifyListeners();
    try {
      final res = await _apiService.sendPhoneAction(command);
      _isLoading = false;
      notifyListeners();
      return res['response'] ?? res['message'] ?? 'Action executed';
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return 'Action failed: $e';
    }
  }

  @override
  void dispose() {
    stopTelemetryPolling();
    super.dispose();
  }
}
