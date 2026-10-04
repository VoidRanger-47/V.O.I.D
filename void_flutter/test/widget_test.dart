import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:void_flutter/core/network/api_service.dart';
import 'package:void_flutter/core/providers/chat_provider.dart';
import 'package:void_flutter/core/providers/settings_provider.dart';
import 'package:void_flutter/core/providers/system_provider.dart';
import 'package:void_flutter/core/providers/vision_provider.dart';
import 'package:void_flutter/main.dart';
import 'package:void_flutter/ui/widgets/zero_gravity_boot_screen.dart';
import 'package:void_flutter/ui/screens/home_screen.dart';

void main() {
  testWidgets('VOID app launches with ZeroGravityBootScreen and transitions to HomeScreen',
      (WidgetTester tester) async {
    final apiService = ApiService();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => SettingsProvider(apiService)),
          ChangeNotifierProvider(create: (_) => ChatProvider(apiService)),
          ChangeNotifierProvider(create: (_) => VisionProvider(apiService)),
          ChangeNotifierProvider(create: (_) => SystemProvider(apiService)),
        ],
        child: const VoidApp(),
      ),
    );

    // Initial frame: VoidBootScreen / ZeroGravityBootScreen is active
    expect(find.byType(ZeroGravityBootScreen), findsOneWidget);

    // Progress through Phase 1: Magnetic Snap (0.0s – 0.6s)
    await tester.pump(const Duration(milliseconds: 600));
    expect(find.byType(ZeroGravityBootScreen), findsOneWidget);

    // Progress through Phase 2: Weightless Drift (0.6s – 1.5s)
    await tester.pump(const Duration(milliseconds: 950));

    // Transition duration (600ms)
    await tester.pump(const Duration(milliseconds: 700));

    // Verify HomeScreen is now rendered
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets('ZeroGravityBootScreen executes onBootComplete callback at 1.5s',
      (WidgetTester tester) async {
    bool bootCompleted = false;

    await tester.pumpWidget(
      MaterialApp(
        home: ZeroGravityBootScreen(
          logoAssetPath: 'assets/images/void_symbol.png',
          onBootComplete: () {
            bootCompleted = true;
          },
        ),
      ),
    );

    expect(bootCompleted, isFalse);

    // Pump past the 1.5s duration and allow status listener to trigger
    await tester.pump(const Duration(milliseconds: 1550));
    expect(bootCompleted, isTrue);
  });
}
