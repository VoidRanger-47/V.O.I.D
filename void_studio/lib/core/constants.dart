import 'package:flutter/material.dart';

/// V.O.I.D. Studio — System Constants & Design Tokens
class VoidTokens {
  VoidTokens._();

  // Base Surfaces (Exoskeleton Near-Black & Graphite)
  static const Color voidBlack = Color(0xFF060709);
  static const Color voidObsidian = Color(0xFF0A0C10);
  static const Color voidGraphite = Color(0xFF101319);
  static const Color voidSurface = Color(0xFF151922);
  static const Color voidSurfaceBorder = Color(0xFF222836);
  static const Color voidSurfaceHover = Color(0xFF1E2430);

  // V.O.I.D. Primary Accents
  static const Color voidOrange = Color(0xFFFF6B00);
  static const Color voidOrangeBright = Color(0xFFFF851B);
  static const Color voidOrangeDim = Color(0xFF994000);
  static const Color voidOrangeGlow = Color(0x33FF6B00);

  // Semantic Tactical Status
  static const Color statusGreen = Color(0xFF00FF88);
  static const Color statusGreenGlow = Color(0x3300FF88);
  static const Color statusYellow = Color(0xFFFFD600);
  static const Color statusYellowGlow = Color(0x33FFD600);
  static const Color statusRed = Color(0xFFFF3344);
  static const Color statusRedGlow = Color(0x33FF3344);
  static const Color statusPurple = Color(0xFFB388FF);
  static const Color statusPurpleGlow = Color(0x33B388FF);
  static const Color statusCyan = Color(0xFF00E5FF);
  static const Color statusCyanGlow = Color(0x3300E5FF);

  // HUD Wireframes & Tech Grid
  static const Color hudGrid = Color(0x0CFFFFFF);
  static const Color hudLine = Color(0x24FF6B00);
  static const Color hudLineSubtle = Color(0x15FFFFFF);
  static const Color hudBracket = Color(0x88FF6B00);

  // Typography Colors
  static const Color textHigh = Color(0xFFF0F4FA);
  static const Color textMedium = Color(0xFFA0ABBE);
  static const Color textMuted = Color(0xFF5E6A80);
  static const Color textOrange = Color(0xFFFF851B);

  // Spatial Dimensions & Breakpoints
  static const double spineWidth = 64.0;
  static const double spineExpandedWidth = 220.0;
  static const double systemRailHeight = 44.0;
  static const double bottomConsoleHeight = 240.0;
  static const double telemetryPanelWidth = 320.0;
  static const double bottomNavHeight = 54.0;
  static const double mobileBreakpoint = 768.0;
  static const double tabletBreakpoint = 1100.0;
}

enum WorkspaceMode {
  core,
  code,
  agents,
  memory,
  models,
  vision,
  hardware,
  terminal,
  logs,
  settings,
}

enum CoreState {
  idle,
  thinking,
  generating,
  executing,
  learning,
  vision,
  error,
  offline,
}
