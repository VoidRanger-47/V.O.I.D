import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../constants/api_endpoints.dart';
import '../models/telemetry_data.dart';
import '../models/vision_context.dart';
import '../models/memory_item.dart';

class ApiService {
  static const String _prefBaseUrlKey = 'void_base_url';
  String _baseUrl = ApiEndpoints.defaultBaseUrl;

  String get baseUrl => _baseUrl;

  ApiService() {
    _loadBaseUrl();
  }

  Future<void> _loadBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_prefBaseUrlKey);
    if (saved != null && saved.isNotEmpty) {
      // If running on web but saved URL was android emulator 10.0.2.2, reset to web localhost
      if (ApiEndpoints.defaultBaseUrl.contains('127.0.0.1') && saved.contains('10.0.2.2')) {
        _baseUrl = ApiEndpoints.defaultBaseUrl;
      } else {
        _baseUrl = saved;
      }
    } else {
      _baseUrl = ApiEndpoints.defaultBaseUrl;
    }
  }

  Future<void> setBaseUrl(String newUrl) async {
    _baseUrl = newUrl.endsWith('/') ? newUrl.substring(0, newUrl.length - 1) : newUrl;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefBaseUrlKey, _baseUrl);
  }

  // --- HEALTH & PING ---
  Future<bool> checkConnection() async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl${ApiEndpoints.health}'),
      ).timeout(const Duration(seconds: 3));
      return res.statusCode == 200;
    } catch (_) {
      // Try tools endpoint fallback if /api/health isn't responding
      try {
        final res2 = await http.get(
          Uri.parse('$_baseUrl${ApiEndpoints.tools}'),
        ).timeout(const Duration(seconds: 3));
        return res2.statusCode == 200;
      } catch (_) {
        return false;
      }
    }
  }

  // --- REAL-TIME SSE CHAT TOKEN STREAMING ---
  Stream<Map<String, dynamic>> streamChatMessage(
    String message, {
    bool forceSearch = false,
    bool thinkingMode = false,
    String? provider,
    String? model,
  }) async* {
    final client = http.Client();
    try {
      final request = http.Request('POST', Uri.parse('$_baseUrl${ApiEndpoints.chatStream}'));
      request.headers['Content-Type'] = 'application/json';
      final bodyMap = <String, dynamic>{
        'message': message,
        'force_search': forceSearch,
        'thinking_mode': thinkingMode,
      };
      if (provider != null) bodyMap['provider'] = provider;
      if (model != null) bodyMap['model'] = model;
      request.body = jsonEncode(bodyMap);

      final response = await client.send(request);

      if (response.statusCode != 200) {
        yield {
          'error': 'Server responded with status ${response.statusCode}',
          'done': true,
        };
        return;
      }

      await for (final rawLine in response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        final line = rawLine.trim();
        if (line.startsWith('data:')) {
          final jsonStr = line.substring(5).trim();
          if (jsonStr.isNotEmpty) {
            try {
              final parsed = jsonDecode(jsonStr);
              if (parsed is Map<String, dynamic>) {
                yield parsed;
              }
            } catch (_) {}
          }
        }
      }
    } catch (e) {
      yield {
        'error': e.toString(),
        'done': true,
      };
    } finally {
      client.close();
    }
  }

  // --- FALLBACK REST CHAT ---
  Future<Map<String, dynamic>> sendChatMessage(
    String message, {
    bool forceSearch = false,
    bool thinkingMode = false,
    String? provider,
    String? model,
  }) async {
    try {
      final bodyMap = <String, dynamic>{
        'message': message,
        'force_search': forceSearch,
        'thinking_mode': thinkingMode,
      };
      if (provider != null) bodyMap['provider'] = provider;
      if (model != null) bodyMap['model'] = model;

      final response = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.chat}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(bodyMap),
      ).timeout(const Duration(seconds: 60));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final text = data['response'] ?? data['reply'] ?? data['content'] ?? '';
        return {
          'status': 'success',
          'response': text,
          'reply': text,
          'skill': data['skill'],
          'metadata': data,
        };
      } else {
        return {
          'status': 'error',
          'response': 'Server responded with status ${response.statusCode}',
        };
      }
    } catch (e) {
      return {
        'status': 'error',
        'response': 'Failed to connect to V.O.I.D. server ($e). Please check host IP in Settings.',
      };
    }
  }

  // --- VISION API ---
  Future<VisionContextData?> getVisionStatus() async {
    try {
      final res = await http.get(Uri.parse('$_baseUrl${ApiEndpoints.visionStatus}')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        return VisionContextData.fromJson(data['data'] ?? {});
      }
    } catch (_) {}
    return null;
  }

  Future<bool> startVision({int? deviceIndex}) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.visionStart}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'device_index': deviceIndex}),
      ).timeout(const Duration(seconds: 6));
      final data = jsonDecode(res.body);
      return data['active'] ?? false;
    } catch (_) {
      return false;
    }
  }

  Future<bool> stopVision() async {
    try {
      final res = await http.post(Uri.parse('$_baseUrl${ApiEndpoints.visionStop}')).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<String> setVisionMode(String mode) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.visionMode}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'mode': mode}),
      ).timeout(const Duration(seconds: 4));
      final data = jsonDecode(res.body);
      return data['mode'] ?? mode;
    } catch (_) {
      return mode;
    }
  }

  Future<Map<String, dynamic>> captureVisionSnapshot() async {
    try {
      final res = await http.post(Uri.parse('$_baseUrl${ApiEndpoints.visionSnapshot}')).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        return jsonDecode(utf8.decode(res.bodyBytes));
      }
    } catch (e) {
      return {'status': 'error', 'message': e.toString()};
    }
    return {'status': 'error', 'message': 'Snapshot request failed'};
  }

  Future<Map<String, dynamic>> analyzeVision(String query) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.visionAnalyze}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'query': query}),
      ).timeout(const Duration(seconds: 12));
      if (res.statusCode == 200) {
        return jsonDecode(utf8.decode(res.bodyBytes));
      }
    } catch (e) {
      return {'status': 'error', 'message': e.toString()};
    }
    return {'status': 'error', 'message': 'Analysis request failed'};
  }

  Future<Map<String, dynamic>> enrollFace(String name) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.visionEnroll}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'name': name, 'samples': 8}),
      ).timeout(const Duration(seconds: 15));
      return jsonDecode(utf8.decode(res.bodyBytes));
    } catch (e) {
      return {'status': 'error', 'result': {'error': e.toString()}};
    }
  }

  Future<List<dynamic>> getVisionProfiles() async {
    try {
      final res = await http.get(Uri.parse('$_baseUrl${ApiEndpoints.visionProfiles}')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        return data['profiles'] ?? [];
      }
    } catch (_) {}
    return [];
  }

  Future<List<MemoryObservation>> getVisualMemory({String? objectFilter}) async {
    try {
      String url = '$_baseUrl${ApiEndpoints.visionMemory}?limit=30';
      if (objectFilter != null && objectFilter.isNotEmpty) {
        url += '&object=${Uri.encodeComponent(objectFilter)}';
      }
      final res = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        final list = data['observations'] as List<dynamic>? ?? [];
        return list.map((o) => MemoryObservation.fromJson(Map<String, dynamic>.from(o))).toList();
      }
    } catch (_) {}
    return [];
  }

  // --- HARDWARE & SYSTEM ---
  Future<TelemetryData> getSystemStats() async {
    try {
      final res = await http.get(Uri.parse('$_baseUrl${ApiEndpoints.systemStats}')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        return TelemetryData.fromJson(data['stats'] ?? data);
      }
    } catch (_) {}
    return TelemetryData(isOnline: false);
  }

  // --- PHONE ADB ACTIONS ---
  Future<Map<String, dynamic>> sendPhoneAction(String command) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.phoneAction}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'command': command}),
      ).timeout(const Duration(seconds: 8));
      return jsonDecode(utf8.decode(res.bodyBytes));
    } catch (e) {
      return {'status': 'error', 'message': e.toString()};
    }
  }

  // --- OLLAMA OFFLINE ENGINE ---
  Future<Map<String, dynamic>> getOllamaStatus() async {
    try {
      final res = await http.get(Uri.parse('$_baseUrl${ApiEndpoints.ollamaStatus}')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return jsonDecode(utf8.decode(res.bodyBytes));
      }
    } catch (_) {}
    return {'status': 'error', 'ollama': {'is_available': false, 'server_running': false, 'installed_models': []}};
  }

  Future<List<String>> getOllamaModels() async {
    try {
      final res = await http.get(Uri.parse('$_baseUrl${ApiEndpoints.ollamaModels}')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        final names = data['names'] as List<dynamic>? ?? [];
        return names.map((e) => e.toString()).toList();
      }
    } catch (_) {}
    return [];
  }

  Future<Map<String, dynamic>> switchOllamaModel({
    required String model,
    bool activate = true,
    String? host,
  }) async {
    try {
      final body = <String, dynamic>{
        'model': model,
        'activate': activate,
      };
      if (host != null && host.isNotEmpty) body['host'] = host;

      final res = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.ollamaSwitch}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ).timeout(const Duration(seconds: 6));

      if (res.statusCode == 200) {
        return jsonDecode(utf8.decode(res.bodyBytes));
      }
    } catch (e) {
      return {'status': 'error', 'error': e.toString()};
    }
    return {'status': 'error'};
  }

  Future<Map<String, dynamic>> pullOllamaModel(String model) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl${ApiEndpoints.ollamaPull}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'model': model}),
      ).timeout(const Duration(seconds: 8));

      return jsonDecode(utf8.decode(res.bodyBytes));
    } catch (e) {
      return {'status': 'error', 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> getCloudStatus() async {
    try {
      final res = await http.get(Uri.parse('$_baseUrl${ApiEndpoints.cloudStatus}')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return jsonDecode(utf8.decode(res.bodyBytes));
      }
    } catch (_) {}
    return {'status': 'error'};
  }
}
