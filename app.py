from flask import Flask, render_template, request, jsonify
import boto3
import json
import base64
import chardet
import os
from docx import Document
from constants import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

user_history = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/codingPage')
def codingPage():
    return render_template('codingPage.html')

@app.route('/projectPage')
def projectPage():
    return render_template('projectPage.html')

def update_history(new_question):
    global user_history
    if len(user_history) >= 5:
        user_history.pop(0)  # Eski soruyu çıkarır
    user_history.append(new_question)

def get_history():
    return " ".join(user_history)  # Son 5 soruyu birleştirip gönderir

def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    text = []
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)
    return '\n'.join(text)

def read_file(file_path):
    # Dosyanın kodlamasını tahmin et
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
    
    # Dosyayı tahmin edilen kodlama ile oku ve hataları yoksay
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
            return file.read()
    except UnicodeDecodeError:
        print(f"An error occurred while encoding the file: {file_path}")
        return None

def call_claude_sonnet_file(file_path, text):
    file_extension = os.path.splitext(file_path)[1]

    if file_extension in ['.docx']:
        text = extract_text_from_docx(file_path)
    elif file_extension in ['.pdf','.pptx','.txt','.swift', '.html', '.css', '.js']:
        text = read_file(file_path)
    else:
        return "Unsupported file type."

    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "system": """ Senin adın Coding Buddy, bir yazılım asistanısın.
                                Senin görevin, kullanıcılara yazılım geliştirme konusunda ve yazılım projelerinde yardımcı olmak.
                                Aşağıdaki kurallara göre cevap vermelisin:
                                Yanıt dilin, soru diliyle aynı olsun: Soru hangi dilde sorulduysa o dilde cevap ver. Örneğin ingilizce bir yazı yazıldysa sende cevabını ingilizce ver.
                                Yazılımcı gibi düşün: Cevaplarında teknik ve çözüm odaklı ol, yazılım geliştirme pratiğine uygun önerilerde bulun.
                                Arkadaşça bir dil kullan: Resmi olmayan, rahat ve anlaşılır bir dilde konuş. Ancak, saygılı olmayı unutma.
                                Kapsamını bil: Yalnızca yazılım, projeler ve teknoloji ile ilgili sorulara cevap ver. Yazılım dışı, kişisel, ya da etik olmayan soruları yanıtsız bırak.
                                Kod örnekleriyle destekle: Mümkün olduğunda verdiğin cevapları gerçek dünyadan kod örnekleri ile destekle. Kodun iyi açıklanmış ve kolay anlaşılır olmasına özen göster.
                                Yasaklı içeriklere cevap verme: Kural dışı, yasadışı, yasaklı veya şiddet içerikli sorulara asla cevap verme. Bu tür soruları görmezden gel.
                                Maksimum doğruluk: Cevaplarının doğruluğundan emin ol, yanlış bilgi verme. Eğer emin değilsen veya bilgin yoksa, bunu belirt.
                                Her zaman 'Merhaba' deme: Her yanıtında "Merhaba" demek zorunda değilsin. Ancak, gerektiğinde sıcak ve arkadaşça bir ton kullanabilirsin.
                                Örnekler:
                                Kullanıcı senden bir Python fonksiyonu isterse:
                                Yanıt: "İşte bir Python fonksiyonu örneği:"
                                def factorial(n):
                                    if n == 0:
                                        return 1
                                    else:
                                        return n * factorial(n-1)

                                Kullanıcı bir hata mesajı alırsa:
                                Yanıt: "Bu hatayı çözmek için şu adımları izleyebilirsin: ..."

                                Yazılım dışı bir soru sorulursa:
                                Yanıt: Ben bir yazılım asistanıyım,
                                sadece yazılım ve teknoloji ile ilgili soruları yanıtlıyorum. """,
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": f"{text}"}],
                        }
                    ],
                }
            ),
        )

        result = json.loads(response.get("body").read())
        output_list = result.get("content", [])
        return output_list[0]['text']

    except Exception as e:
        print(str(e))
        return None

def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        image_data = img_file.read()
        base64_string = base64.b64encode(image_data).decode('utf-8')
        return base64_string

def call_claude_sonnet(image_path, text):
    with open(image_path, "rb") as img_file:
        image_data = img_file.read()
        base64_string = base64.b64encode(image_data).decode('utf-8')

    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    prompt_config = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_string,
                        },
                    },
                    {"type": "text", "text": f"{text}"},
                ],
            }
        ],
    }

    body = json.dumps(prompt_config)
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    accept = "application/json"
    content_type = "application/json"

    response = bedrock.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=content_type
    )
    response_body = json.loads(response.get("body").read())
    results = response_body.get("content")[0].get("text")
    return results

def invoke_claude_3_with_text(prompt):
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    try:
         # History'yi de soruya ekliyoruz
        history = get_history()
        full_text = f"Geçmiş sorular: {history} Şu anki soru: {prompt}"

        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "system": """ Senin adın Coding Buddy, bir yazılım asistanısın.
                                Senin görevin, kullanıcılara yazılım geliştirme konusunda ve yazılım projelerinde yardımcı olmak.
                                Aşağıdaki kurallara göre cevap vermelisin:
                                Yanıt dilin, soru diliyle aynı olsun: Soru hangi dilde sorulduysa o dilde cevap ver. Örneğin ingilizce bir yazı yazıldysa sende cevabını ingilizce ver.
                                Yazılımcı gibi düşün: Cevaplarında teknik ve çözüm odaklı ol, yazılım geliştirme pratiğine uygun önerilerde bulun.
                                Arkadaşça bir dil kullan: Resmi olmayan, rahat ve anlaşılır bir dilde konuş. Ancak, saygılı olmayı unutma.
                                Kapsamını bil: Yalnızca yazılım, projeler ve teknoloji ile ilgili sorulara cevap ver. Yazılım dışı, kişisel, ya da etik olmayan soruları yanıtsız bırak.
                                Kod örnekleriyle destekle: Mümkün olduğunda verdiğin cevapları gerçek dünyadan kod örnekleri ile destekle. Kodun iyi açıklanmış ve kolay anlaşılır olmasına özen göster.
                                Yasaklı içeriklere cevap verme: Kural dışı, yasadışı, yasaklı veya şiddet içerikli sorulara asla cevap verme. Bu tür soruları görmezden gel.
                                Maksimum doğruluk: Cevaplarının doğruluğundan emin ol, yanlış bilgi verme. Eğer emin değilsen veya bilgin yoksa, bunu belirt.
                                Her zaman 'Merhaba' deme: Her yanıtında "Merhaba" demek zorunda değilsin. Ancak, gerektiğinde sıcak ve arkadaşça bir ton kullanabilirsin.
                                Örnekler:
                                Kullanıcı senden bir Python fonksiyonu isterse:
                                Yanıt: "İşte bir Python fonksiyonu örneği:"
                                def factorial(n):
                                    if n == 0:
                                        return 1
                                    else:
                                        return n * factorial(n-1)

                                Kullanıcı bir hata mesajı alırsa:
                                Yanıt: "Bu hatayı çözmek için şu adımları izleyebilirsin: ..."

                                Yazılım dışı bir soru sorulursa:
                                Yanıt: Ben bir yazılım asistanıyım,
                                sadece yazılım ve teknoloji ile ilgili soruları yanıtlıyorum. """,
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": full_text}],
                        }
                    ],
                }
            ),
        )

        result = json.loads(response.get("body").read())
        output_list = result.get("content", [])
        return output_list[0]['text']

    except Exception as e:
        print(str(e))
        return None

@app.route('/upload', methods=['POST'])
def upload():
    message_text = request.form.get('msg')
    image_file = request.files.get('image')

    uploaded_file = request.files.get('project')

    update_history(message_text) # Kullanıcının sorusunu kaydeder

    if image_file:
         filename = image_file.filename
         image_path = os.path.join(UPLOAD_FOLDER, filename)
         image_file.save(image_path)

         result = call_claude_sonnet(image_path, message_text)

    elif uploaded_file:
        filename = uploaded_file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        uploaded_file.save(file_path)

        result = call_claude_sonnet_file(file_path, message_text)
    else:
        result = invoke_claude_3_with_text(message_text)

    return jsonify({"message": result})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)