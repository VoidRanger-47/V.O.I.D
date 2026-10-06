class MemoryObservation {
  final int id;
  final String isoTime;
  final String eventType;
  final String objectName;
  final String context;
  final double confidence;
  final double importance;

  MemoryObservation({
    required this.id,
    required this.isoTime,
    required this.eventType,
    required this.objectName,
    required this.context,
    required this.confidence,
    required this.importance,
  });

  factory MemoryObservation.fromJson(Map<String, dynamic> json) {
    return MemoryObservation(
      id: json['id'] ?? 0,
      isoTime: json['iso_time'] ?? '',
      eventType: json['event_type'] ?? 'OBSERVATION',
      objectName: json['object'] ?? json['object_name'] ?? 'Object',
      context: json['context'] ?? 'workspace',
      confidence: (json['confidence'] ?? 1.0).toDouble(),
      importance: (json['importance'] ?? 0.5).toDouble(),
    );
  }
}
