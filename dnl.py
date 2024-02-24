from fastapi import FastAPI, File, UploadFile, HTTPException
from openai import OpenAI
from PIL import Image
import io
import base64
import os
from fastapi.responses import HTMLResponse
from moviepy.editor import VideoFileClip, AudioFileClip
import shutil

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


# 파일 처리 및 텍스트 추출 함수
async def process_audio_video(file_path: str, client):
    if file_path.endswith(('.mp3', '.m4a', '.wav', '.mpga')):
        clip = AudioFileClip(file_path)
    else:
        clip = VideoFileClip(file_path)

    total_duration = clip.duration
    interval = 130
    current_start = 0
    result = ''

    while current_start < total_duration:
        end_time = min(current_start + interval, total_duration)
        new_clip = clip.subclip(current_start, end_time)

        with open("temp_clip.wav", "wb") as temp_file:
            new_clip.write_audiofile(temp_file.name, codec="pcm_s16le")  # 임시 오디오 파일 저장
            with open(temp_file.name, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
                # result += transcript.data['text']  # 추출된 텍스트를 결과에 추가
                # result += transcript['choices'][0]['text']  # 수정된 부분
                result += transcript
        current_start += interval

    clip.close()
    return result

# 텍스트 요약 함수
async def summarize(client, text: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "Summarize the following in Korean and in formal language"},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    upload_dir = 'uploads'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    # 업로드한 파일 저장
    with open(file_path, 'wb') as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 파일 처리 및 텍스트 추출
    result = await process_audio_video(file_path, client)

    # 추출된 전체 텍스트 요약
    final_summary = await summarize(client, result)

    # 임시 파일 삭제
    os.remove(file_path)

    return {"summary": final_summary}

