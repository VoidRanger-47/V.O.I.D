import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/chat_message.dart';
import '../models/chat_session.dart';
import '../network/api_service.dart';

class ChatProvider with ChangeNotifier {
  static const String _storageKey = 'void_chat_sessions_v1';
  static const String _activeSessionKey = 'void_active_session_id_v1';

  final ApiService _apiService;
  final List<ChatSession> _sessions = [];
  String _currentSessionId = '';
  bool _isLoading = false;
  bool _forceSearch = false;
  bool _thinkingMode = false;

  ChatProvider(this._apiService) {
    final defaultSession = _createDefaultSession();
    _sessions.add(defaultSession);
    _currentSessionId = defaultSession.id;
    _initSessions();
  }

  List<ChatSession> get sessions => List.unmodifiable(_sessions);
  String get currentSessionId => _currentSessionId;

  ChatSession get currentSession {
    if (_sessions.isEmpty) {
      final defaultSession = _createDefaultSession();
      _sessions.add(defaultSession);
      _currentSessionId = defaultSession.id;
      return defaultSession;
    }
    final idx = _sessions.indexWhere((s) => s.id == _currentSessionId);
    if (idx != -1) {
      return _sessions[idx];
    }
    _currentSessionId = _sessions.first.id;
    return _sessions.first;
  }

  List<ChatMessage> get messages => currentSession.messages;
  bool get isLoading => _isLoading;
  bool get forceSearch => _forceSearch;
  bool get thinkingMode => _thinkingMode;

  void toggleForceSearch() {
    _forceSearch = !_forceSearch;
    notifyListeners();
  }

  void toggleThinkingMode() {
    _thinkingMode = !_thinkingMode;
    notifyListeners();
  }

  ChatSession _createDefaultSession({String title = 'New Conversation'}) {
    final now = DateTime.now();
    return ChatSession(
      id: 'session_${now.millisecondsSinceEpoch}',
      title: title,
      timestamp: now,
      messages: [
        ChatMessage(
          id: 'init-${now.millisecondsSinceEpoch}',
          text: 'V.O.I.D. Neural System Online. Ready for instructions.',
          sender: MessageSender.voidAgent,
          timestamp: now,
          skillUsed: 'system_info',
        ),
      ],
    );
  }

  Future<void> _initSessions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedData = prefs.getString(_storageKey);
      if (savedData != null && savedData.isNotEmpty) {
        final List decoded = jsonDecode(savedData);
        _sessions.clear();
        for (final item in decoded) {
          _sessions.add(ChatSession.fromJson(Map<String, dynamic>.from(item)));
        }
      }
      final savedActiveId = prefs.getString(_activeSessionKey);
      if (savedActiveId != null && _sessions.any((s) => s.id == savedActiveId)) {
        _currentSessionId = savedActiveId;
      }
    } catch (_) {
      // Fallback on parse failure
    }

    if (_sessions.isEmpty) {
      final defaultSession = _createDefaultSession();
      _sessions.add(defaultSession);
      _currentSessionId = defaultSession.id;
    } else if (_currentSessionId.isEmpty || !_sessions.any((s) => s.id == _currentSessionId)) {
      _currentSessionId = _sessions.first.id;
    }

    notifyListeners();
  }

  Future<void> _saveSessionsToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final data = jsonEncode(_sessions.map((s) => s.toJson()).toList());
      await prefs.setString(_storageKey, data);
      await prefs.setString(_activeSessionKey, _currentSessionId);
    } catch (_) {}
  }

  /// Start a new conversation session
  void newSession() {
    final session = _createDefaultSession();
    _sessions.insert(0, session);
    _currentSessionId = session.id;
    _saveSessionsToPrefs();
    notifyListeners();
  }

  /// Switch active conversation session
  void switchSession(String sessionId) {
    if (_sessions.any((s) => s.id == sessionId)) {
      _currentSessionId = sessionId;
      _saveSessionsToPrefs();
      notifyListeners();
    }
  }

  /// Individual deletion of a conversation session
  Future<void> deleteSession(String sessionId) async {
    final idx = _sessions.indexWhere((s) => s.id == sessionId);
    if (idx == -1) return;

    _sessions.removeAt(idx);

    if (_sessions.isEmpty) {
      final fresh = _createDefaultSession();
      _sessions.add(fresh);
      _currentSessionId = fresh.id;
    } else if (_currentSessionId == sessionId) {
      _currentSessionId = _sessions.first.id;
    }

    await _saveSessionsToPrefs();
    notifyListeners();
  }

  /// Individual deletion of a single message from the current session
  Future<void> deleteMessage(String messageId) async {
    final active = currentSession;
    final idx = active.messages.indexWhere((m) => m.id == messageId);
    if (idx != -1) {
      active.messages.removeAt(idx);
      await _saveSessionsToPrefs();
      notifyListeners();
    }
  }

  /// Clear messages of current conversation
  void clearHistory() {
    final active = currentSession;
    active.messages.clear();
    active.messages.add(ChatMessage(
      id: 'init-${DateTime.now().millisecondsSinceEpoch}',
      text: 'V.O.I.D. Neural System Online. Ready for instructions.',
      sender: MessageSender.voidAgent,
      timestamp: DateTime.now(),
      skillUsed: 'system_info',
    ));
    _saveSessionsToPrefs();
    notifyListeners();
  }

  Future<void> sendMessage(String text, {String? provider, String? model}) async {
    final cleanText = text.trim();
    if (cleanText.isEmpty || _isLoading) return;

    final active = currentSession;

    // Update conversation title from first user query if still generic
    if (active.title == 'New Conversation' || active.title == 'Conversation') {
      final shortTitle = cleanText.length > 28 ? '${cleanText.substring(0, 28)}...' : cleanText;
      active.title = shortTitle;
    }

    // 1. Add user message
    final userMsgId = DateTime.now().millisecondsSinceEpoch.toString();
    active.messages.add(ChatMessage(
      id: userMsgId,
      text: cleanText,
      sender: MessageSender.user,
      timestamp: DateTime.now(),
    ));

    // 2. Add placeholder assistant streaming message
    final botMsgId = (DateTime.now().millisecondsSinceEpoch + 1).toString();
    final botMsg = ChatMessage(
      id: botMsgId,
      text: '',
      sender: MessageSender.voidAgent,
      timestamp: DateTime.now(),
      isStreaming: true,
    );
    active.messages.add(botMsg);

    _isLoading = true;
    notifyListeners();
    _saveSessionsToPrefs();

    // 3. Stream real-time tokens from V.O.I.D. server
    bool receivedTokens = false;
    final accumulated = StringBuffer();
    String? activeSkill;

    try {
      await for (final event in _apiService.streamChatMessage(
        cleanText,
        forceSearch: _forceSearch,
        thinkingMode: _thinkingMode,
        provider: provider,
        model: model,
      )) {
        if (event.containsKey('error') && accumulated.isEmpty) {
          throw Exception(event['error']);
        }

        if (event['type'] == 'tool_call') {
          activeSkill = event['tool'] ?? event['name'];
        }

        if (event['skill'] != null) {
          activeSkill = event['skill'];
        }

        if (event.containsKey('replace_all')) {
          accumulated.clear();
          accumulated.write(event['replace_all']);
        } else if (event.containsKey('token')) {
          receivedTokens = true;
          accumulated.write(event['token']);
        }

        final idx = active.messages.indexWhere((m) => m.id == botMsgId);
        if (idx != -1) {
          final isDone = event['done'] == true;
          active.messages[idx] = active.messages[idx].copyWith(
            text: accumulated.toString(),
            skillUsed: activeSkill,
            isStreaming: !isDone,
          );
          notifyListeners();
        }
      }

      // If stream ended with no tokens, fallback to standard REST request
      if (!receivedTokens && accumulated.isEmpty) {
        final res = await _apiService.sendChatMessage(
          cleanText,
          forceSearch: _forceSearch,
          thinkingMode: _thinkingMode,
          provider: provider,
          model: model,
        );

        final responseText = res['response'] ?? res['reply'] ?? res['content'] ?? 'No response received from model.';
        final skill = res['skill'] ?? res['skill_used'];

        final idx = active.messages.indexWhere((m) => m.id == botMsgId);
        if (idx != -1) {
          active.messages[idx] = active.messages[idx].copyWith(
            text: responseText,
            skillUsed: skill,
            isStreaming: false,
            metadata: res,
          );
        }
      }
    } catch (e) {
      // Try fallback to REST endpoint if streaming hit an error
      try {
        final res = await _apiService.sendChatMessage(
          cleanText,
          forceSearch: _forceSearch,
          thinkingMode: _thinkingMode,
          provider: provider,
          model: model,
        );

        final responseText = res['response'] ?? res['reply'] ?? res['content'] ?? 'No response received from model.';
        final skill = res['skill'] ?? res['skill_used'];

        final idx = active.messages.indexWhere((m) => m.id == botMsgId);
        if (idx != -1) {
          active.messages[idx] = active.messages[idx].copyWith(
            text: responseText,
            skillUsed: skill,
            isStreaming: false,
            metadata: res,
          );
        }
      } catch (fallbackError) {
        final idx = active.messages.indexWhere((m) => m.id == botMsgId);
        if (idx != -1) {
          active.messages[idx] = active.messages[idx].copyWith(
            text: 'Error communicating with V.O.I.D. ($e)',
            sender: MessageSender.system,
            isStreaming: false,
          );
        }
      }
    } finally {
      // Ensure streaming indicator is turned off
      final idx = active.messages.indexWhere((m) => m.id == botMsgId);
      if (idx != -1 && active.messages[idx].isStreaming) {
        active.messages[idx] = active.messages[idx].copyWith(isStreaming: false);
      }
      _isLoading = false;
      _saveSessionsToPrefs();
      notifyListeners();
    }
  }
}
