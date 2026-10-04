import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:void_flutter/core/network/api_service.dart';
import 'package:void_flutter/core/providers/chat_provider.dart';
import 'package:void_flutter/core/providers/settings_provider.dart';
import 'package:void_flutter/core/providers/system_provider.dart';
import 'package:void_flutter/core/providers/vision_provider.dart';
import 'package:void_flutter/ui/widgets/void_attachment_action_menu.dart';
import 'package:void_flutter/ui/screens/void_neural_chat_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('VoidAttachmentButton Tests', () {
    testWidgets('renders in default state with add icon', (WidgetTester tester) async {
      final controller = AnimationController(
        vsync: const TestVSync(),
        duration: const Duration(milliseconds: 200),
      );

      bool tapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            backgroundColor: const Color(0xFF111111),
            body: Center(
              child: VoidAttachmentButton(
                animation: controller,
                onTap: () => tapped = true,
              ),
            ),
          ),
        ),
      );

      expect(find.byType(VoidAttachmentButton), findsOneWidget);
      expect(find.byIcon(Icons.add_rounded), findsOneWidget);

      await tester.tap(find.byType(VoidAttachmentButton));
      await tester.pump();
      expect(tapped, isTrue);

      controller.dispose();
    });

    testWidgets('rotates by 45 degrees and changes color when active', (WidgetTester tester) async {
      final controller = AnimationController(
        vsync: const TestVSync(),
        duration: const Duration(milliseconds: 200),
        value: 1.0, // Fully active state
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            backgroundColor: const Color(0xFF111111),
            body: Center(
              child: VoidAttachmentButton(
                animation: controller,
                onTap: () {},
              ),
            ),
          ),
        ),
      );

      final icon = tester.widget<Icon>(find.byIcon(Icons.add_rounded));
      expect(icon.color, const Color(0xFFFF5F15)); // V.O.I.D. Orange

      controller.dispose();
    });
  });

  group('VoidAttachmentActionMenu Tests', () {
    testWidgets('renders all 5 action items with titles and descriptive subtitles',
        (WidgetTester tester) async {
      bool visionTapped = false;
      bool filesTapped = false;
      bool imageTapped = false;
      bool memoryTapped = false;
      bool webTapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            backgroundColor: const Color(0xFF111111),
            body: Center(
              child: VoidAttachmentActionMenu(
                onVisionTap: () => visionTapped = true,
                onFilesTap: () => filesTapped = true,
                onGenerateImageTap: () => imageTapped = true,
                onNeuralMemoryTap: () => memoryTapped = true,
                onWebSearchTap: () => webTapped = true,
              ),
            ),
          ),
        ),
      );

      // Verify Header
      expect(find.text('V.O.I.D. NEURAL ACTIONS'), findsOneWidget);

      // Verify 5 Action Items Titles & Subtitles
      expect(find.text('Vision Input / Attach Photo'), findsOneWidget);
      expect(find.text('Upload image for neural analysis'), findsOneWidget);

      expect(find.text('Files & Docs'), findsOneWidget);
      expect(find.text('Browse local system files'), findsOneWidget);

      expect(find.text('Generate Image'), findsOneWidget);
      expect(find.text('SD-Turbo offline canvas'), findsOneWidget);

      expect(find.text('Neural Memory'), findsOneWidget);
      expect(find.text('Inspect local context memory'), findsOneWidget);

      expect(find.text('Web Search / Network'), findsOneWidget);
      expect(find.text('Query external web data'), findsOneWidget);

      // Test tap interactions
      await tester.tap(find.text('Vision Input / Attach Photo'));
      await tester.pump();
      expect(visionTapped, isTrue);

      await tester.tap(find.text('Files & Docs'));
      await tester.pump();
      expect(filesTapped, isTrue);

      await tester.tap(find.text('Generate Image'));
      await tester.pump();
      expect(imageTapped, isTrue);

      await tester.tap(find.text('Neural Memory'));
      await tester.pump();
      expect(memoryTapped, isTrue);

      await tester.tap(find.text('Web Search / Network'));
      await tester.pump();
      expect(webTapped, isTrue);
    });
  });

  group('VoidNeuralChatScreen Integration Tests', () {
    testWidgets('Tapping + button opens action menu and outside tap closes it',
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
          child: const MaterialApp(
            home: VoidNeuralChatScreen(),
          ),
        ),
      );

      // Initial frame: Attachment menu should not be visible
      expect(find.byType(VoidAttachmentButton), findsOneWidget);
      expect(find.byType(VoidAttachmentActionMenu), findsNothing);

      // Tap the '+' attachment button
      await tester.tap(find.byType(VoidAttachmentButton));
      await tester.pump(const Duration(milliseconds: 300));

      // Attachment menu is now open and visible
      expect(find.byType(VoidAttachmentActionMenu), findsOneWidget);
      expect(find.text('Vision Input / Attach Photo'), findsOneWidget);

      // Tap on the empty state / message area outside the menu to dismiss
      await tester.tapAt(const Offset(200, 200));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump();

      // Menu should be dismissed
      expect(find.byType(VoidAttachmentActionMenu), findsNothing);
    });

    testWidgets('Tapping + button again toggles and closes open action menu',
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
          child: const MaterialApp(
            home: VoidNeuralChatScreen(),
          ),
        ),
      );

      // Open menu
      await tester.tap(find.byType(VoidAttachmentButton));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.byType(VoidAttachmentActionMenu), findsOneWidget);

      // Tap + button again (now rotated as x)
      await tester.tap(find.byType(VoidAttachmentButton));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump();

      // Menu should be dismissed
      expect(find.byType(VoidAttachmentActionMenu), findsNothing);
    });

    testWidgets('Tapping text field dismisses open action menu',
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
          child: const MaterialApp(
            home: VoidNeuralChatScreen(),
          ),
        ),
      );

      // Open menu
      await tester.tap(find.byType(VoidAttachmentButton));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.byType(VoidAttachmentActionMenu), findsOneWidget);

      // Tap the TextField
      await tester.tap(find.byType(TextField));
      await tester.pump(const Duration(milliseconds: 300));

      // Menu should be dismissed
      expect(find.byType(VoidAttachmentActionMenu), findsNothing);
    });
  });
}
