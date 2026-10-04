# 📧 V.O.I.D. Gmail Analyzer & Inbox Intelligence Plugin

The **Gmail Analyzer Plugin** gives V.O.I.D. the ability to securely inspect, parse, summarize, categorize, and extract critical action items from your Gmail inbox using 100% local IMAP SSL protocol.

---

## 🚀 Quick Setup Guide (2 Minutes)

To connect your live Gmail account to V.O.I.D.:

### Step 1: Generate a Google App Password
1. Go to your **[Google Account Security Settings](https://myaccount.google.com/security)**.
2. Ensure **2-Step Verification** is turned **ON**.
3. In the search bar at the top of your Google Account page, search for **`App passwords`**.
4. Create a new App Password:
   - App Name: `VOID AI Assistant`
5. Copy the 16-character generated password (e.g. `abcd efgh ijkl mnop`).

### Step 2: Configure `config.json`
Open `plugins/gmail_analyzer/config.json` and paste your details:

```json
{
  "email_address": "your_email@gmail.com",
  "app_password": "abcdefghijklmnop",
  "imap_server": "imap.gmail.com",
  "imap_port": 993,
  "max_emails_fetch": 15,
  "demo_mode": false
}
```

---

## 💬 Voice & Chat Commands Supported

Once loaded, you can ask V.O.I.D. naturally:

- **Inbox Analysis**:
  - *"V.O.I.D., analyze my Gmail."*
  - *"Summarize my recent emails."*
- **Unread Messages**:
  - *"Check my unread emails."*
  - *"Do I have any new mail?"*
- **Urgent & Action Items**:
  - *"Any urgent emails today?"*
  - *"What action items do I have in my inbox?"*
- **Search**:
  - *"Search emails for AWS invoice."*
  - *"Search emails from GitHub."*
- **Status**:
  - *"Gmail status"*

---

## 🔒 Privacy & Local Security
- **No Cloud Third Parties**: V.O.I.D. connects directly from your local machine to `imap.gmail.com:993` over encrypted TLS/SSL.
- **Zero Data Logging**: Your emails are analyzed locally in-memory and are never uploaded or shared.
- **Graceful Offline Mode**: When offline or before credentials are entered, the plugin runs in simulated Demonstration Mode.
