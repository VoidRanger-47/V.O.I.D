import 'package:flutter/material.dart';

/// V.O.I.D. Studio — System Constants & Design Tokens
class VoidTokens {
  VoidTokens._();

  // Base Surfaces (Exoskeleton Deep Charcoal & Dark Slate — Web #0f0f11, #171719, #18181c)
  static const Color voidBlack = Color(0xFF0F0F11);
  static const Color voidObsidian = Color(0xFF171719);
  static const Color voidGraphite = Color(0xFF15151A);
  static const Color voidSurface = Color(0xFF18181C);
  static const Color voidSurfaceBorder = Color(0x14FFFFFF); // rgba(255,255,255,0.08) / 0xFF26262A
  static const Color voidSurfaceHover = Color(0x0FFFFFFF); // rgba(255,255,255,0.06)

  // V.O.I.D. Primary Accents (Web #ff5500 / #ff6a1a)
  static const Color voidOrange = Color(0xFFFF5500);
  static const Color voidOrangeBright = Color(0xFFFF6A1A);
  static const Color voidOrangeDim = Color(0xFFE63E00);
  static const Color voidOrangeGlow = Color(0x33FF5500);

  // Semantic Tactical Status
  static const Color statusGreen = Color(0xFF10B981);
  static const Color statusGreenGlow = Color(0x3310B981);
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
  static const Color hudLine = Color(0x24FF5500);
  static const Color hudLineSubtle = Color(0x15FFFFFF);
  static const Color hudBracket = Color(0x88FF5500);

  // Typography Colors (Web #f0eeeb, #8a8a88, #ff5500)
  static const Color textHigh = Color(0xFFF0EEEB);
  static const Color textMedium = Color(0xFFA8A8A6);
  static const Color textMuted = Color(0xFF8A8A88);
  static const Color textOrange = Color(0xFFFF5500);

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
