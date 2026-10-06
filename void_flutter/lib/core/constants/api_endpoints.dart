import 'package:flutter/foundation.dart';

class ApiEndpoints {
  // Default base URL dynamically resolved per platform
  // - Web (Chrome): http://127.0.0.1:5000
  // - Android Emulator: http://10.0.2.2:5000
  // - Desktop: http://127.0.0.1:5000
  static String get defaultBaseUrl {
    if (kIsWeb) {
      return 'http://127.0.0.1:5000';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5000';
    }
    return 'http://127.0.0.1:5000';
  }

  // Chat & Skills
  static const String chat = '/api/chat';
  static const String chatStream = '/api/chat/stream';
  static const String tools = '/api/tools';
  static const String skillRoute = '/api/skills/route';

  // Vision Subsystem
  static const String visionStatus = '/api/vision/status';
  static const String visionStart = '/api/vision/start';
  static const String visionStop = '/api/vision/stop';
  static const String visionMode = '/api/vision/mode';
  static const String visionFeed = '/api/vision/feed';
  static const String visionSnapshot = '/api/vision/snapshot';
  static const String visionAnalyze = '/api/vision/analyze';
  static const String visionEnroll = '/api/vision/enroll';
  static const String visionProfiles = '/api/vision/profiles';
  static const String visionMemory = '/api/vision/memory';
  static const String visionDevices = '/api/vision/devices';

  // System & Hardware
  static const String systemStats = '/api/system/stats';
  static const String worldState = '/api/world/state';
  static const String health = '/api/health';

  // Phone Automation & ADB
  static const String phoneAction = '/api/phone/action';

  // Memory & Knowledge
  static const String memorySearch = '/api/memory/search';
  static const String memoryStats = '/api/memory/stats';

  // Ollama Offline Engine & Cloud
  static const String ollamaStatus = '/api/ollama/status';
  static const String ollamaModels = '/api/ollama/models';
  static const String ollamaSwitch = '/api/ollama/switch';
  static const String ollamaPull = '/api/ollama/pull';
  static const String cloudStatus = '/api/cloud/status';
}
