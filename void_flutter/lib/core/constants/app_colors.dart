import 'package:flutter/material.dart';

/// V.O.I.D. Design System Tokens — Minimalist Ultra-Clean Dark Aesthetic
/// Strictly mirrored from the VOID web interface.
class AppColors {
  // 1. Visual Identity & Canvas Tokens
  /// Deep Canvas / Matte Black (`0xFF0D0D0D`)
  static const Color bgApp = Color(0xFF0D0D0D);

  /// Surface / Container / Card (`0xFF161616`) — subtle contrast against pure black
  static const Color surface = Color(0xFF161616);
  static const Color surfaceContainer = Color(0xFF161616);
  static const Color bgSidebar = Color(0xFF161616);
  static const Color bgCard = Color(0xFF161616);
  static const Color bgModal = Color(0xFF161616);
  static const Color bgMessageUser = Color(0xFF161616);
  static const Color bgInput = Color(0xFF0D0D0D);
  static const Color bgHover = Color(0xFF202020);
  static const Color bgCode = Color(0xFF111111);
  static const Color bgCodeHeader = Color(0xFF181818);
  static const Color bgNewChat = Color(0xFF161616);

  // 2. Borders & Hairlines
  /// Surface Border / Hairline Divider (`0xFF262626`) — 1px clean geometric borders
  static const Color border = Color(0xFF262626);
  static const Color borderHairline = Color(0xFF262626);
  static const Color borderSubtle = Color(0xFF262626);
  static const Color borderStrong = Color(0xFF383838);

  // 3. Brand Accent — Electric Burnt Orange
  /// Primary Action / Focus / Active Glow (`0xFFDA7756`)
  static const Color accent = Color(0xFFDA7756);
  static const Color accentDark = Color(0xFFB8593A);
  static const Color accentLight = Color(0xFFE88A6E);

  /// Accent Subtle / Hover / Active Pill (`0x1FDA7756` — 12% opacity tint)
  static const Color accentSubtle = Color(0x1FDA7756);

  // 4. Typography Colors
  /// Crisp near-white (`0xFFF5F5F5`)
  static const Color textPrimary = Color(0xFFF5F5F5);

  /// Low contrast, legible secondary/muted (`0xFF8E8E93`)
  static const Color textSecondary = Color(0xFF8E8E93);
  static const Color textMuted = Color(0xFF8E8E93);

  // 5. System & Status Colors
  /// Danger / Error (`0xFFE05656`)
  static const Color danger = Color(0xFFE05656);
  static const Color red = Color(0xFFE05656);
  static const Color statusRed = Color(0xFFE05656);

  /// Status active execution / Online (`0xFF10B981`)
  static const Color statusGreen = Color(0xFF10B981);
  static const Color techBlue = Color(0xFF38BDF8);
  static const Color visionCyan = Color(0xFF00E5FF);
  static const Color amber = Color(0xFFF59E0B);
  static const Color purple = Color(0xFFA855F7);
  static const Color codeColor = Color(0xFFA5D6FF);

  // 6. Compatibility Mappings
  static const Color background = bgApp;
  static const Color surfaceElevated = surface;
  static const Color surfaceHover = bgHover;
  static const Color cyan = accent;
  static const Color neonBlue = techBlue;
  static const Color neonGreen = statusGreen;
  static const Color neonRed = red;
  static const Color goldAccent = accent;

  // 7. Gradients (Clean geometric and subtle)
  static const LinearGradient accentGradient = LinearGradient(
    colors: [Color(0xFFE88A6E), Color(0xFFDA7756), Color(0xFFB8593A)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient userAvatarGradient = LinearGradient(
    colors: [Color(0xFFE88A6E), Color(0xFFDA7756)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0x0AFFFFFF), Color(0x02FFFFFF)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
