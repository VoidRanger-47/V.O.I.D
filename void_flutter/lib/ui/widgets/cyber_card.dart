import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class CyberCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? borderColor;
  final Color? backgroundColor;
  final double borderRadius;
  final VoidCallback? onTap;

  const CyberCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.borderColor,
    this.backgroundColor,
    this.borderRadius = 16,
    this.onTap,
    bool showGlow = false, // kept for backward compatibility, shadows removed
  });

  @override
  Widget build(BuildContext context) {
    final border = borderColor ?? AppColors.borderHairline;
    final bg = backgroundColor ?? AppColors.surfaceContainer;

    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(color: border, width: 1.0),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(borderRadius),
          onTap: onTap,
          splashColor: AppColors.accentSubtle,
          highlightColor: AppColors.accentSubtle,
          child: Padding(
            padding: padding,
            child: child,
          ),
        ),
      ),
    );
  }
}
