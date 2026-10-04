from flask import Flask, render_template, request, jsonify
from chat import (
    route_query, void_mem, tokenizer, model, args, device,
    get_coding_persona, format_code_response
)
import torch
import os
import json

app = Flask(__name__)

# Ensure upload directory exists (optional)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json()
        message = data.get("message", "")
        context_files = data.get("files", [])
        user_settings = data.get("settings", {})

        # Defaults
        default_temp = 0.7
        default_max_tokens = 75

        if not message.strip() and not context_files:
            return jsonify({"reply": "I am listening. Please say something."})

        # File context
        full_context_message = message
        if context_files:
            file_names = ", ".join([f['name'] for f in context_files])
            full_context_message = f"[System Context: Attached files: {file_names}]\n{message}"

        # Skill routing
        response, skill_type = route_query(full_context_message)
        if response is not None:
            return jsonify({"reply": response, "skill": skill_type})

        # Memory context + coding persona
        is_coding = (skill_type == "coding")
        context_block = void_mem.inject_memory_into_prompt(full_context_message)

        if is_coding:
            context_block += get_coding_persona(full_context_message)

        full_prompt = (
            f"{context_block}\n"
            f"### User:\n{full_context_message}\n"
            f"### V.O.I.D.:\n"
        )

        # Temperature + max tokens
        temperature = user_settings.get("temperature", default_temp)
        max_new = user_settings.get("maxTokens", default_max_tokens)

        if is_coding:
            max_new = max(max_new, 250)
            temperature = min(temperature, 0.5)

        input_ids = tokenizer.encode(full_prompt)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=device)

        if input_tensor.size(1) > args.seq_len:
            input_tensor = input_tensor[:, -args.seq_len:]

        with torch.no_grad():
            generated = input_tensor

            for _ in range(max_new):
                if generated.size(1) > args.seq_len:
                    gen_cond = generated[:, -args.seq_len:]
                else:
                    gen_cond = generated

                logits = model(gen_cond)
                logits = logits[:, -1, :] / temperature
                probs = torch.nn.functional.softmax(logits, dim=1)
                next_token = torch.multinomial(probs, num_samples=1)
                generated = torch.cat((generated, next_token), dim=1)

        output = tokenizer.decode(generated[0].cpu().tolist())

        try:
            final_response = output.split("### V.O.I.D.:")[-1].strip()
        except:
            final_response = output

        if is_coding:
            final_response = format_code_response(final_response)

        return jsonify({
            "reply": final_response,
            "status": "success",
            "skill": skill_type
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({
            "reply": "I encountered a neural pathway error.",
            "error": str(e)
        }), 500


# ============================
# FIXED: Prevent double-boot
# ============================
if __name__ == "__main__":
    # disable flask’s auto reload (the cause of double model load)
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )
