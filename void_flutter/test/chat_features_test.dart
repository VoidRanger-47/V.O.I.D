import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:void_flutter/core/models/chat_message.dart';
import 'package:void_flutter/core/network/api_service.dart';
import 'package:void_flutter/core/providers/chat_provider.dart';
import 'package:void_flutter/core/constants/app_colors.dart';
import 'package:void_flutter/ui/widgets/chat_bubble.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('VOID Multi-Session and Deletion Tests', () {
    test('ChatProvider creates sessions, switches, and deletes individual sessions', () async {
      final provider = ChatProvider(ApiService());

      // Initial default session
      expect(provider.sessions.length, greaterThanOrEqualTo(1));
      final initialId = provider.currentSessionId;

      // Create new session
      provider.newSession();
      expect(provider.sessions.length, greaterThanOrEqualTo(2));
      final newId = provider.currentSessionId;
      expect(newId, isNot(equals(initialId)));

      // Switch back to initial
      provider.switchSession(initialId);
      expect(provider.currentSessionId, equals(initialId));

      // Individual deletion of initial session
      await provider.deleteSession(initialId);
      expect(provider.sessions.any((s) => s.id == initialId), isFalse);
    });

    test('ChatProvider individual message deletion removes specified message', () async {
      final provider = ChatProvider(ApiService());
      final testMsg = ChatMessage(
        id: 'msg-to-delete-123',
        text: 'This is a test message to delete',
        sender: MessageSender.user,
        timestamp: DateTime.now(),
      );

      provider.currentSession.messages.add(testMsg);
      expect(provider.messages.any((m) => m.id == 'msg-to-delete-123'), isTrue);

      await provider.deleteMessage('msg-to-delete-123');
      expect(provider.messages.any((m) => m.id == 'msg-to-delete-123'), isFalse);
    });

    testWidgets('ChatBubble displays delete button and triggers onDelete callback', (WidgetTester tester) async {
      bool deleteTriggered = false;

      final message = ChatMessage(
        id: 'm1',
        text: 'Hello VOID system',
        sender: MessageSender.user,
        timestamp: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            backgroundColor: AppColors.bgApp,
            body: ChatBubble(
              message: message,
              onDelete: () {
                deleteTriggered = true;
              },
            ),
          ),
        ),
      );

      expect(find.text('Hello VOID system'), findsOneWidget);
      expect(find.byIcon(Icons.delete_outline), findsOneWidget);

      await tester.tap(find.byIcon(Icons.delete_outline));
      await tester.pump();

      expect(deleteTriggered, isTrue);
    });
  });
}
