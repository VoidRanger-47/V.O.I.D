import 'package:flutter/material.dart';
import 'constants.dart';

class VoidTheme {
  VoidTheme._();

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: VoidTokens.voidBlack,
      primaryColor: VoidTokens.voidOrange,
      colorScheme: const ColorScheme.dark(
        primary: VoidTokens.voidOrange,
        secondary: VoidTokens.statusCyan,
        surface: VoidTokens.voidObsidian,
        error: VoidTokens.statusRed,
      ),
      fontFamily: 'Segoe UI',
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          color: VoidTokens.textHigh,
          fontSize: 26,
          fontWeight: FontWeight.w700,
          letterSpacing: 2.0,
        ),
        headlineMedium: TextStyle(
          color: VoidTokens.textHigh,
          fontSize: 20,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.5,
        ),
        titleMedium: TextStyle(
          color: VoidTokens.textHigh,
          fontSize: 14,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.0,
        ),
        bodyMedium: TextStyle(
          color: VoidTokens.textMedium,
          fontSize: 13,
          letterSpacing: 0.4,
        ),
        bodySmall: TextStyle(
          color: VoidTokens.textMuted,
          fontSize: 11,
          fontFamily: 'Consolas',
          letterSpacing: 0.5,
        ),
        labelSmall: TextStyle(
          color: VoidTokens.voidOrangeBright,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          fontFamily: 'Consolas',
          letterSpacing: 1.2,
        ),
      ),
      scrollbarTheme: ScrollbarThemeData(
        thumbColor: WidgetStateProperty.all(VoidTokens.voidOrange.withOpacity(0.3)),
        trackColor: WidgetStateProperty.all(VoidTokens.voidSurface),
        radius: const Radius.circular(2),
        thickness: WidgetStateProperty.all(4),
      ),
    );
  }

  // Monospace tech typography helper
  static TextStyle mono({
    double fontSize = 12,
    FontWeight fontWeight = FontWeight.normal,
    Color color = VoidTokens.textMedium,
    double letterSpacing = 0.5,
  }) {
    return TextStyle(
      fontFamily: 'Consolas',
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      letterSpacing: letterSpacing,
    );
  }

  // Tactical uppercase HUD label
  static TextStyle hudLabel({
    double fontSize = 10,
    FontWeight fontWeight = FontWeight.w700,
    Color color = VoidTokens.voidOrange,
    double letterSpacing = 1.4,
  }) {
    return TextStyle(
      fontFamily: 'Consolas',
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      letterSpacing: letterSpacing,
    );
  }
}
