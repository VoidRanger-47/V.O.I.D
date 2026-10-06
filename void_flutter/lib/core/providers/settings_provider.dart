import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../network/api_service.dart';

class SettingsProvider with ChangeNotifier {
  static const String _prefEngineKey = 'void_active_engine';
  static const String _prefModelKey = 'void_active_ollama_model';

  final ApiService _apiService;
  bool _isConnected = false;
  bool _isChecking = false;

  // Ollama & Engine State
  String _activeEngine = 'ollama'; // 'ollama', 'gemini', 'local'
  String _activeOllamaModel = 'llama3.2';
  bool _isOllamaServerRunning = false;
  bool _isOllamaAvailable = false;
  List<String> _ollamaInstalledModels = [];
  String _ollamaHost = 'http://localhost:11434';
  bool _isOllamaLoading = false;

  SettingsProvider(this._apiService) {
    _loadPreferences();
    checkConnection();
  }

  String get baseUrl => _apiService.baseUrl;
  bool get isConnected => _isConnected;
  bool get isChecking => _isChecking;

  // Engine & Ollama getters
  String get activeEngine => _activeEngine;
  String get activeOllamaModel => _activeOllamaModel;
  bool get isOllamaServerRunning => _isOllamaServerRunning;
  bool get isOllamaAvailable => _isOllamaAvailable;
  List<String> get ollamaInstalledModels => List.unmodifiable(_ollamaInstalledModels);
  String get ollamaHost => _ollamaHost;
  bool get isOllamaLoading => _isOllamaLoading;

  String get activeDisplayName {
    if (_activeEngine == 'ollama') {
      return 'Ollama: $_activeOllamaModel';
    } else if (_activeEngine == 'gemini') {
      return 'Gemini Cloud';
    } else {
      return 'V.O.I.D. Native';
    }
  }

  Future<void> _loadPreferences() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedEngine = prefs.getString(_prefEngineKey);
      if (savedEngine != null) _activeEngine = savedEngine;
      final savedModel = prefs.getString(_prefModelKey);
      if (savedModel != null) _activeOllamaModel = savedModel;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> updateBaseUrl(String newUrl) async {
    await _apiService.setBaseUrl(newUrl);
    notifyListeners();
    await checkConnection();
  }

  Future<bool> checkConnection() async {
    _isChecking = true;
    notifyListeners();

    _isConnected = await _apiService.checkConnection();
    _isChecking = false;

    if (_isConnected) {
      await fetchOllamaStatus();
    }

    notifyListeners();
    return _isConnected;
  }

  Future<void> fetchOllamaStatus() async {
    try {
      final data = await _apiService.getOllamaStatus();
      if (data.containsKey('ollama')) {
        final ol = data['ollama'] as Map<String, dynamic>;
        _isOllamaServerRunning = ol['server_running'] == true;
        _isOllamaAvailable = ol['is_available'] == true;
        _ollamaHost = ol['host']?.toString() ?? 'http://localhost:11434';
        final currentModel = ol['active_model']?.toString();
        if (currentModel != null && currentModel.isNotEmpty) {
          _activeOllamaModel = currentModel;
        }

        final installed = ol['installed_models'] as List<dynamic>? ?? [];
        _ollamaInstalledModels = installed.map((e) => e.toString()).toList();

        // Only adopt backend engine if user hasn't set a saved preference
        final prefs = await SharedPreferences.getInstance();
        if (!prefs.containsKey(_prefEngineKey)) {
          final sysEngine = ol['active_system_engine']?.toString();
          if (sysEngine != null && sysEngine.isNotEmpty) {
            _activeEngine = sysEngine;
          }
        }
      }
      notifyListeners();
    } catch (_) {}
  }

  Future<bool> selectEngine(String engine, {String? model}) async {
    _activeEngine = engine;
    if (model != null && model.isNotEmpty) {
      _activeOllamaModel = model;
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefEngineKey, _activeEngine);
      await prefs.setString(_prefModelKey, _activeOllamaModel);
    } catch (_) {}

    notifyListeners();

    if (_isConnected) {
      if (engine == 'ollama') {
        _isOllamaLoading = true;
        notifyListeners();
        final res = await _apiService.switchOllamaModel(
          model: _activeOllamaModel,
          activate: true,
        );
        _isOllamaLoading = false;
        await fetchOllamaStatus();
        notifyListeners();
        return res['status'] == 'success';
      }
    }
    return true;
  }

  Future<bool> switchOllamaModel(String model) async {
    _isOllamaLoading = true;
    _activeOllamaModel = model;
    _activeEngine = 'ollama';
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefEngineKey, 'ollama');
      await prefs.setString(_prefModelKey, model);
    } catch (_) {}

    final res = await _apiService.switchOllamaModel(model: model, activate: true);
    _isOllamaLoading = false;
    await fetchOllamaStatus();
    notifyListeners();
    return res['status'] == 'success';
  }

  Future<bool> pullOllamaModel(String model) async {
    final res = await _apiService.pullOllamaModel(model);
    await fetchOllamaStatus();
    return res['status'] == 'pulling' || res['status'] == 'success';
  }
}
