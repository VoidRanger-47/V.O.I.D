class VisionDetectedObject {
  final String label;
  final double confidence;
  final Map<String, dynamic> location;

  VisionDetectedObject({
    required this.label,
    required this.confidence,
    required this.location,
  });

  factory VisionDetectedObject.fromJson(Map<String, dynamic> json) {
    return VisionDetectedObject(
      label: json['label'] ?? 'object',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      location: json['location'] != null ? Map<String, dynamic>.from(json['location']) : {},
    );
  }
}

class VisionDetectedFace {
  final String identity;
  final String name;
  final double? confidence;
  final bool recognized;
  final Map<String, dynamic> location;

  VisionDetectedFace({
    required this.identity,
    required this.name,
    this.confidence,
    required this.recognized,
    required this.location,
  });

  factory VisionDetectedFace.fromJson(Map<String, dynamic> json) {
    return VisionDetectedFace(
      identity: json['identity'] ?? 'unknown',
      name: json['name'] ?? 'Unknown Person',
      confidence: json['confidence'] != null ? (json['confidence']).toDouble() : null,
      recognized: json['recognized'] ?? false,
      location: json['location'] != null ? Map<String, dynamic>.from(json['location']) : {},
    );
  }
}

class VisionSceneInfo {
  final String environment;
  final String lighting;
  final int peopleCount;
  final String activityLevel;
  final String summary;

  VisionSceneInfo({
    this.environment = 'Indoor',
    this.lighting = 'Normal',
    this.peopleCount = 0,
    this.activityLevel = 'Static',
    this.summary = 'Camera standby',
  });

  factory VisionSceneInfo.fromJson(Map<String, dynamic> json) {
    return VisionSceneInfo(
      environment: json['environment'] ?? 'Indoor',
      lighting: json['lighting'] ?? 'Normal',
      peopleCount: json['people_count'] ?? 0,
      activityLevel: json['activity_level'] ?? 'Static',
      summary: json['summary'] ?? '',
    );
  }
}

class VisionContextData {
  final bool isCameraActive;
  final String mode;
  final double actualFps;
  final List<VisionDetectedObject> objects;
  final List<VisionDetectedFace> faces;
  final VisionSceneInfo scene;

  VisionContextData({
    this.isCameraActive = false,
    this.mode = 'BALANCED',
    this.actualFps = 0.0,
    this.objects = const [],
    this.faces = const [],
    required this.scene,
  });

  factory VisionContextData.fromJson(Map<String, dynamic> json) {
    final perception = json['perception'] ?? {};
    final telemetry = json['telemetry'] ?? {};
    final cam = telemetry['camera'] ?? {};

    final objList = (perception['objects'] as List<dynamic>? ?? [])
        .map((o) => VisionDetectedObject.fromJson(Map<String, dynamic>.from(o)))
        .toList();

    final faceList = (perception['faces'] as List<dynamic>? ?? [])
        .map((f) => VisionDetectedFace.fromJson(Map<String, dynamic>.from(f)))
        .toList();

    final sceneInfo = perception['scene'] != null
        ? VisionSceneInfo.fromJson(Map<String, dynamic>.from(perception['scene']))
        : VisionSceneInfo();

    return VisionContextData(
      isCameraActive: cam['active'] ?? perception['camera_active'] ?? false,
      mode: cam['mode'] ?? 'BALANCED',
      actualFps: (cam['actual_fps'] ?? 0.0).toDouble(),
      objects: objList,
      faces: faceList,
      scene: sceneInfo,
    );
  }
}
