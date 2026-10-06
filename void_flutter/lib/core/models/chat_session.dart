import 'chat_message.dart';

class ChatSession {
  final String id;
  String title;
  final DateTime timestamp;
  final List<ChatMessage> messages;

  ChatSession({
    required this.id,
    required this.title,
    required this.timestamp,
    List<ChatMessage>? messages,
  }) : messages = messages ?? [];

  ChatSession copyWith({
    String? id,
    String? title,
    DateTime? timestamp,
    List<ChatMessage>? messages,
  }) {
    return ChatSession(
      id: id ?? this.id,
      title: title ?? this.title,
      timestamp: timestamp ?? this.timestamp,
      messages: messages ?? List.from(this.messages),
    );
  }

  factory ChatSession.fromJson(Map<String, dynamic> json) {
    final rawMessages = json['messages'] as List? ?? [];
    return ChatSession(
      id: json['id']?.toString() ?? DateTime.now().millisecondsSinceEpoch.toString(),
      title: json['title']?.toString() ?? 'Conversation',
      timestamp: json['timestamp'] != null
          ? (DateTime.tryParse(json['timestamp'].toString()) ??
              DateTime.fromMillisecondsSinceEpoch(
                  int.tryParse(json['timestamp'].toString()) ?? DateTime.now().millisecondsSinceEpoch))
          : DateTime.now(),
      messages: rawMessages
          .map((m) => ChatMessage.fromJson(Map<String, dynamic>.from(m)))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'timestamp': timestamp.toIso8601String(),
      'messages': messages.map((m) => m.toJson()).toList(),
    };
  }
}
