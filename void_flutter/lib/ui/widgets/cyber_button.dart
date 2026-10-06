import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/constants/app_colors.dart';

enum CyberButtonVariant { primary, secondary, outline, ghost }

class CyberButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback onPressed;
  final bool isPrimary;
  final CyberButtonVariant? variant;
  final bool isLoading;
  final Color? customColor;
  final Color? textColor;
  final double borderRadius;
  final EdgeInsetsGeometry padding;

  const CyberButton({
    super.key,
    required this.label,
    this.icon,
    required this.onPressed,
    this.isPrimary = true,
    this.variant,
    this.isLoading = false,
    this.customColor,
    this.textColor,
    this.borderRadius = 8,
    this.padding = const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
  });

  @override
  Widget build(BuildContext context) {
    final effectiveVariant = variant ??
        (isPrimary ? CyberButtonVariant.primary : CyberButtonVariant.secondary);

    Color bg;
    Color fg;
    BorderSide borderSide;

    switch (effectiveVariant) {
      case CyberButtonVariant.primary:
        bg = customColor ?? AppColors.accent;
        fg = textColor ?? AppColors.bgApp;
        borderSide = BorderSide.none;
        break;
      case CyberButtonVariant.secondary:
        bg = customColor ?? AppColors.surfaceContainer;
        fg = textColor ?? AppColors.textPrimary;
        borderSide = const BorderSide(color: AppColors.borderHairline, width: 1);
        break;
      case CyberButtonVariant.outline:
        bg = Colors.transparent;
        fg = textColor ?? AppColors.accent;
        borderSide = const BorderSide(color: AppColors.borderHairline, width: 1);
        break;
      case CyberButtonVariant.ghost:
        bg = Colors.transparent;
        fg = textColor ?? AppColors.textSecondary;
        borderSide = BorderSide.none;
        break;
    }

    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(borderRadius),
        border: borderSide != BorderSide.none
            ? Border.fromBorderSide(borderSide)
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(borderRadius),
          onTap: isLoading ? null : onPressed,
          splashColor: AppColors.accentSubtle,
          highlightColor: AppColors.accentSubtle,
          child: Padding(
            padding: padding,
            child: isLoading
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: fg,
                    ),
                  )
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (icon != null) ...[
                        Icon(icon, size: 15, color: fg),
                        const SizedBox(width: 8),
                      ],
                      Text(
                        label,
                        style: GoogleFonts.inter(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                          letterSpacing: 0.2,
                          color: fg,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}
