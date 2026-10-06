enum MessageSender { user, voidAgent, system }

class ChatMessage {
  final String id;
  final String text;
  final MessageSender sender;
  final DateTime timestamp;
  final String? skillUsed;
  final bool isStreaming;
  final Map<String, dynamic>? metadata;

  ChatMessage({
    required this.id,
    required this.text,
    required this.sender,
    required this.timestamp,
    this.skillUsed,
    this.isStreaming = false,
    this.metadata,
  });

  ChatMessage copyWith({
    String? id,
    String? text,
    MessageSender? sender,
    DateTime? timestamp,
    String? skillUsed,
    bool? isStreaming,
    Map<String, dynamic>? metadata,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      text: text ?? this.text,
      sender: sender ?? this.sender,
      timestamp: timestamp ?? this.timestamp,
      skillUsed: skillUsed ?? this.skillUsed,
      isStreaming: isStreaming ?? this.isStreaming,
      metadata: metadata ?? this.metadata,
    );
  }

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    MessageSender senderEnum = MessageSender.user;
    final s = (json['sender'] ?? 'user').toString().toLowerCase();
    if (s.contains('void') || s.contains('bot') || s.contains('agent')) {
      senderEnum = MessageSender.voidAgent;
    } else if (s.contains('system')) {
      senderEnum = MessageSender.system;
    }

    return ChatMessage(
      id: json['id'] ?? DateTime.now().millisecondsSinceEpoch.toString(),
      text: json['text'] ?? json['content'] ?? json['response'] ?? '',
      sender: senderEnum,
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'].toString()) ?? DateTime.now()
          : DateTime.now(),
      skillUsed: json['skill'] ?? json['skill_used'],
      isStreaming: json['is_streaming'] ?? false,
      metadata: json['metadata'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'text': text,
      'sender': sender.name,
      'timestamp': timestamp.toIso8601String(),
      'skill': skillUsed,
      'is_streaming': isStreaming,
      'metadata': metadata,
    };
  }
}
