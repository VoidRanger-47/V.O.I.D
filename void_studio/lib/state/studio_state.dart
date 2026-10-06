import 'dart:async';
import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../services/backend_service.dart';
import '../services/telemetry_service.dart';

class StudioState extends ChangeNotifier {
  WorkspaceMode _activeMode = WorkspaceMode.core;
  CoreState _coreState = CoreState.idle;
  bool _performanceMode = false;
  bool _reducedMotion = false;
  bool _bottomPanelOpen = false;
  bool _telemetryDrawerOpen = true;
  bool _commandPaletteOpen = false;
  String _activeFile = 'core/router.py';
  final String _activeProject = 'V.O.I.D. — Cognitive OS Mk-IV';
  SystemMetrics _metrics = const SystemMetrics();
  bool _isBackendConnected = false;

  StreamSubscription? _metricsSub;
  StreamSubscription? _connSub;

  StudioState() {
    _initListeners();
  }

  WorkspaceMode get activeMode => _activeMode;
  CoreState get coreState => _coreState;
  bool get performanceMode => _performanceMode;
  bool get reducedMotion => _reducedMotion;
  bool get bottomPanelOpen => _bottomPanelOpen;
  bool get telemetryDrawerOpen => _telemetryDrawerOpen;
  bool get commandPaletteOpen => _commandPaletteOpen;
  String get activeFile => _activeFile;
  String get activeProject => _activeProject;
  SystemMetrics get metrics => _metrics;
  bool get isBackendConnected => _isBackendConnected;

  void _initListeners() {
    _metricsSub = BackendService.instance.metricsStream.listen((m) {
      _metrics = m;
      notifyListeners();
    });

    _connSub = BackendService.instance.connectionStream.listen((c) {
      _isBackendConnected = c;
      _coreState = c ? CoreState.idle : CoreState.offline;
      notifyListeners();
    });

    BackendService.instance.startMonitoring();
    TelemetryService.instance.initializeInitialTelemetry();
  }

  void setActiveMode(WorkspaceMode mode) {
    if (_activeMode != mode) {
      _activeMode = mode;
      TelemetryService.instance.emit(
        source: 'WORKSPACE',
        message: 'Active view switched to: ${mode.name.toUpperCase()}',
        level: TelemetryLevel.info,
      );
      notifyListeners();
    }
  }

  void setCoreState(CoreState state) {
    if (_coreState != state) {
      _coreState = state;
      TelemetryService.instance.emit(
        source: 'CORE',
        message: 'Core state changed to: ${state.name.toUpperCase()}',
        level: state == CoreState.error ? TelemetryLevel.critical : TelemetryLevel.neural,
      );
      notifyListeners();
    }
  }

  void togglePerformanceMode() {
    _performanceMode = !_performanceMode;
    TelemetryService.instance.emit(
      source: 'SETTINGS',
      message: 'Performance Mode: ${_performanceMode ? "ACTIVE (LOW GPU)" : "DISABLED (FULL HUD)"}',
      level: TelemetryLevel.info,
    );
    notifyListeners();
  }

  void toggleReducedMotion() {
    _reducedMotion = !_reducedMotion;
    notifyListeners();
  }

  void toggleBottomPanel() {
    _bottomPanelOpen = !_bottomPanelOpen;
    notifyListeners();
  }

  void toggleTelemetryDrawer() {
    _telemetryDrawerOpen = !_telemetryDrawerOpen;
    notifyListeners();
  }

  void openCommandPalette() {
    _commandPaletteOpen = true;
    notifyListeners();
  }

  void closeCommandPalette() {
    _commandPaletteOpen = false;
    notifyListeners();
  }

  void setActiveFile(String filePath) {
    _activeFile = filePath;
    TelemetryService.instance.emit(
      source: 'EDITOR',
      message: 'Inspecting: $filePath',
      level: TelemetryLevel.info,
    );
    notifyListeners();
  }

  @override
  void dispose() {
    _metricsSub?.cancel();
    _connSub?.cancel();
    super.dispose();
  }
}
