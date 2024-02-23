from fastapi import FastAPI, File, UploadFile
from openai import OpenAI
from PIL import Image
import io
import base64
import os
import os  # os 모듈을 임포트

app = FastAPI()
# 환경 변수에서 API 키 사용
api_key1 = os.getenv("OPENAI_API_KEY")
# api_key1=os.environ[OPENAI_API_KEY]
if not api_key1:
    raise ValueError("API 키가 제공되지 않았습니다. OPENAI_API_KEY 환경 변수를 설정하세요.")

client = OpenAI(api_key=api_key1)

def describe(text):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 이미지에 대해서 아주 자세히 묘사해주고 max_tokens 이전에 말을 종료해줘."},
                    {
                        "type": "image_url",
                        "image_url": text,
                    },
                ],
            }
        ],
        max_tokens=2024,
    )
    return response.choices[0].message.content

@app.get("/")
async def read_root():
    return {"message": "환영합니다. FastAPI 서버가 실행 중입니다."}



@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue())
    img_base64_str = img_base64.decode('utf-8')
    image_data = f"data:image/jpeg;base64,{img_base64_str}"

    description = describe(image_data)

    return {"description": description}
