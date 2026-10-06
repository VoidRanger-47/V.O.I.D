import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/constants/app_colors.dart';

class HudStatusBadge extends StatelessWidget {
  final String label;
  final bool isActive;
  final Color? activeColor;
  final IconData? icon;
  final bool isShieldBadge;

  const HudStatusBadge({
    super.key,
    required this.label,
    required this.isActive,
    this.activeColor,
    this.icon,
    this.isShieldBadge = false,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveColor =
        isActive ? (activeColor ?? AppColors.statusGreen) : AppColors.textSecondary;

    if (isShieldBadge) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: AppColors.surfaceContainer,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AppColors.borderHairline, width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon ?? Icons.shield_outlined,
              size: 11,
              color: effectiveColor,
            ),
            const SizedBox(width: 5),
            Text(
              label.toUpperCase(),
              style: GoogleFonts.jetBrainsMono(
                color: effectiveColor,
                fontSize: 10,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.0,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: effectiveColor.withOpacity(0.08),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: effectiveColor.withOpacity(0.25),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 5,
            height: 5,
            decoration: BoxDecoration(
              color: effectiveColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            label.toUpperCase(),
            style: GoogleFonts.jetBrainsMono(
              color: effectiveColor,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.1,
            ),
          ),
        ],
      ),
    );
  }
}
