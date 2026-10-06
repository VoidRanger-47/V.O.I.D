import 'dart:async';
import 'package:flutter/material.dart';
import '../models/vision_context.dart';
import '../models/memory_item.dart';
import '../network/api_service.dart';

class VisionProvider with ChangeNotifier {
  final ApiService _apiService;
  VisionContextData? _contextData;
  List<MemoryObservation> _visualMemories = [];
  List<dynamic> _enrolledProfiles = [];
  bool _isLoading = false;
  bool _hudOverlayEnabled = true;
  Timer? _pollingTimer;

  VisionProvider(this._apiService);

  VisionContextData? get contextData => _contextData;
  List<MemoryObservation> get visualMemories => _visualMemories;
  List<dynamic> get enrolledProfiles => _enrolledProfiles;
  bool get isLoading => _isLoading;
  bool get hudOverlayEnabled => _hudOverlayEnabled;
  bool get isCameraActive => _contextData?.isCameraActive ?? false;

  void toggleHudOverlay(bool value) {
    _hudOverlayEnabled = value;
    notifyListeners();
  }

  void startPolling() {
    _pollingTimer?.cancel();
    fetchStatus();
    _pollingTimer = Timer.periodic(const Duration(milliseconds: 1500), (_) {
      fetchStatus();
    });
  }

  void stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
  }

  Future<void> fetchStatus() async {
    final ctx = await _apiService.getVisionStatus();
    if (ctx != null) {
      _contextData = ctx;
      notifyListeners();
    }
  }

  Future<bool> toggleCamera() async {
    _isLoading = true;
    notifyListeners();

    bool success;
    if (isCameraActive) {
      success = await _apiService.stopVision();
    } else {
      success = await _apiService.startVision();
    }

    await fetchStatus();
    _isLoading = false;
    notifyListeners();
    return success;
  }

  Future<void> setMode(String mode) async {
    await _apiService.setVisionMode(mode);
    await fetchStatus();
  }

  Future<Map<String, dynamic>> triggerSnapshot() async {
    _isLoading = true;
    notifyListeners();
    final res = await _apiService.captureVisionSnapshot();
    await fetchStatus();
    _isLoading = false;
    notifyListeners();
    return res;
  }

  Future<Map<String, dynamic>> triggerScan() async {
    _isLoading = true;
    notifyListeners();
    final res = await _apiService.analyzeVision('Deep scan environment and describe everything.');
    await fetchStatus();
    _isLoading = false;
    notifyListeners();
    return res;
  }

  Future<Map<String, dynamic>> enrollFace(String name) async {
    _isLoading = true;
    notifyListeners();
    final res = await _apiService.enrollFace(name);
    await loadProfiles();
    _isLoading = false;
    notifyListeners();
    return res;
  }

  Future<void> loadProfiles() async {
    _enrolledProfiles = await _apiService.getVisionProfiles();
    notifyListeners();
  }

  Future<void> loadVisualMemory({String? objectFilter}) async {
    _visualMemories = await _apiService.getVisualMemory(objectFilter: objectFilter);
    notifyListeners();
  }

  @override
  void dispose() {
    stopPolling();
    super.dispose();
  }
}
