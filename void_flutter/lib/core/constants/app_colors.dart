import 'package:flutter/material.dart';

/// V.O.I.D. Design System Tokens — Minimalist Ultra-Clean Dark Aesthetic
/// Strictly mirrored from the VOID web interface (--bg-app: #0f0f11, --accent-color: #ff5500).
class AppColors {
  // 1. Visual Identity & Canvas Tokens
  /// Deep Canvas / Matte Charcoal Black (`#0f0f11` / `0xFF0F0F11`)
  static const Color bgApp = Color(0xFF0F0F11);

  /// Surface / Container / Sidebar (`#171719` / `0xFF171719`)
  static const Color surface = Color(0xFF171719);
  static const Color surfaceContainer = Color(0xFF171719);
  static const Color bgSidebar = Color(0xFF171719);
  static const Color bgCard = Color(0xFF18181C);
  static const Color bgModal = Color(0xFF18181C);
  static const Color bgArtifact = Color(0xFF15151A);
  static const Color bgMessageUser = Color(0x14FF5500); // rgba(255,85,0,0.08)
  static const Color bgInput = Color(0xFF171719);
  static const Color bgHover = Color(0x0FFFFFFF); // rgba(255,255,255,0.06)
  static const Color bgCode = Color(0xFF121215);
  static const Color bgCodeHeader = Color(0xFF18181C);
  static const Color bgNewChat = Color(0xFF171719);

  // 2. Borders & Hairlines
  /// Surface Border / Hairline Divider (`rgba(255,255,255,0.08)` -> `0x14FFFFFF` / `#26262A`)
  static const Color border = Color(0x14FFFFFF);
  static const Color borderHairline = Color(0x14FFFFFF);
  static const Color borderSubtle = Color(0x14FFFFFF);
  static const Color borderStrong = Color(0x24FFFFFF); // rgba(255,255,255,0.14)

  // 3. Brand Accent — Electric Cyber Orange (Web #ff5500 / #ff6a1a)
  /// Primary Action / Focus / Active Glow (`0xFFFF5500`)
  static const Color accent = Color(0xFFFF5500);
  static const Color accentDark = Color(0xFFE63E00);
  static const Color accentLight = Color(0xFFFF7A2E);
  static const Color accentWarm = Color(0xFFFF6A1A);

  /// Accent Subtle / Hover / Active Pill (`0x1FFF5500` — 12% opacity tint)
  static const Color accentSubtle = Color(0x1FFF5500);

  // 4. Typography Colors
  /// Crisp near-white (Web `--text-primary: #f0eeeb`)
  static const Color textPrimary = Color(0xFFF0EEEB);

  /// Low-contrast, clean secondary typography (soft neutral slate-gray, NOT orange)
  static const Color textSecondary = Color(0xFF9E9EA4);

  /// Web `--text-muted: #8a8a88`
  static const Color textMuted = Color(0xFF8A8A88);

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
  static const Color goldAccent = Color(0xFFFFD54F);

  // 6. Compatibility Mappings
  static const Color background = bgApp;
  static const Color surfaceElevated = surface;
  static const Color surfaceHover = bgHover;
  static const Color cyan = techBlue;
  static const Color neonBlue = techBlue;
  static const Color neonGreen = statusGreen;
  static const Color neonRed = red;

  // 7. Gradients (Web --accent-gradient: linear-gradient(135deg, #ff7a2e 0%, #ff5500 50%, #e63e00 100%))
  static const LinearGradient accentGradient = LinearGradient(
    colors: [Color(0xFFFF7A2E), Color(0xFFFF5500), Color(0xFFE63E00)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient userAvatarGradient = LinearGradient(
    colors: [Color(0xFFFF7A2E), Color(0xFFFF5500)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0x0AFFFFFF), Color(0x02FFFFFF)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
