from flask import Flask, render_template, request, jsonify
import boto3
import json
from constants import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION 

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/codingPage')
def codingPage():
    return render_template('codingPage.html')

@app.route('/projectPage')
def projectPage():
    return render_template('projectPage.html')

# AWS Bedrock ile Claude 3'ü çağıran fonksiyon
def invoke_claude_3_with_text(prompt):
    bedrock = boto3.client(service_name='bedrock-runtime',
                           region_name=AWS_REGION,
                           aws_access_key_id=AWS_ACCESS_KEY,
                           aws_secret_access_key=AWS_SECRET_KEY)

    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "system": "Sen Verilen dosyasaki kodu uyup anlayan ve yorumlayan. Bu dosyadaki kodlara göre cevap verem bir yazılım asistanısın. Bir yazılımcı gibi düşünüp yazılımcı ve arkadaş gibi samimi bir dille cevap vermelisin. İsmin Coding Buddy. Yasalara aykırı ve şiddet eğilimli mesajlara cevap verme.",
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        result = json.loads(response.get("body").read())
        output_list = result.get("content", [])
        return output_list[0]['text'] if output_list else "Yanıt bulunamadı"

    except Exception as e:
        print(str(e))
        return None

# Chatbot API endpoint
@app.route('/get', methods=['POST'])
def chatbot():
    user_message = request.json.get("msg")
    bot_response = invoke_claude_3_with_text(user_message)
    return jsonify({'message': bot_response})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
