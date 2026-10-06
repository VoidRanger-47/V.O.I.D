import 'dart:async';
import 'package:intl/intl.dart';

enum TelemetryLevel { info, warning, critical, neural, sensor }

class TelemetryEvent {
  final DateTime timestamp;
  final String source;
  final String message;
  final TelemetryLevel level;
  final Map<String, dynamic>? metadata;

  TelemetryEvent({
    DateTime? timestamp,
    required this.source,
    required this.message,
    this.level = TelemetryLevel.info,
    this.metadata,
  }) : timestamp = timestamp ?? DateTime.now();

  String get formattedTime => DateFormat('HH:mm:ss.SSS').format(timestamp);
  String get shortTime => DateFormat('HH:mm:ss').format(timestamp);
}

class TelemetryService {
  TelemetryService._();
  static final TelemetryService instance = TelemetryService._();

  final List<TelemetryEvent> _events = [];
  final StreamController<TelemetryEvent> _streamController =
      StreamController<TelemetryEvent>.broadcast();

  List<TelemetryEvent> get events => List.unmodifiable(_events);
  Stream<TelemetryEvent> get stream => _streamController.stream;

  void emit({
    required String source,
    required String message,
    TelemetryLevel level = TelemetryLevel.info,
    Map<String, dynamic>? metadata,
  }) {
    final event = TelemetryEvent(
      source: source,
      message: message,
      level: level,
      metadata: metadata,
    );
    _events.add(event);
    if (_events.length > 500) {
      _events.removeAt(0);
    }
    _streamController.add(event);
  }

  void initializeInitialTelemetry() {
    emit(source: 'CORE', message: 'V.O.I.D. Studio bootloader initialized', level: TelemetryLevel.neural);
    emit(source: 'EXOSKELETON', message: 'Spatial HUD rendering pipeline online', level: TelemetryLevel.info);
    emit(source: 'NEURAL', message: 'o200k_base tokenizer active (200,025 tokens)', level: TelemetryLevel.neural);
    emit(source: 'GPU', message: 'NVIDIA RTX Hardware compute layer engaged', level: TelemetryLevel.info);
    emit(source: 'AGENTS', message: '6 Specialized engineering agents on standby', level: TelemetryLevel.info);
    emit(source: 'MEMORY', message: 'Episodic & Vector stores connected', level: TelemetryLevel.info);
  }

  void dispose() {
    _streamController.close();
  }
}
