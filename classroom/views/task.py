# tasks.py

import cv2
import dlib
from scipy.spatial import distance
import time
import datetime
from django.http import StreamingHttpResponse

def event_stream(request):
     #イベントストリームの送信を開始する前に、必要なレスポンスヘッダーを設定する
     response = StreamingHttpResponse(streaming_content = stream_events())
     response['Content-Type'] = 'text/event-stream'
     response['Cache-control'] = 'no-cache'
     return response

def stream_events():
    #イベントデータを生成して返すジェネレーター関数
    #イベントデータは'data'フィールドにラベル付けされる
    start_time = datetime.datetime.now()
    while True:
        now = datetime.datetime.now()
        elapsed_time = now - start_time
        if elapsed_time.seconds >= 5:
            yield f'data: {now}\n\n'
            start_time = now
        else:
            time.sleep(1)  # 1秒待機

def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear


def detect_drowsiness():

    
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

    eye_ar_threshold = 0.2
    blink_start_time = 0
    blink_count = 0
    time_since_last_blink = 0
    drowsy_threshold = 5

    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # グレースケール変換(解析効率化のため)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)

        for face in faces:
            landmarks = predictor(gray, face)
            left_eye = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)]
            right_eye = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)]
            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)
            ear = (left_ear + right_ear) / 2.0

            if ear < eye_ar_threshold:
                if blink_start_time == 0:
                    blink_start_time = time.time()
                elif time.time() - blink_start_time > 0.5:
                    blink_count += 1
                    time_since_last_blink = 0
                    blink_start_time = 0
            else:
                time_since_last_blink += 1
                if blink_count >= 5 and time_since_last_blink > drowsy_threshold:
                    print("居眠り検知！")

        # ここで必要な処理を実行
        # 例: データベースに結果を保存

    cap.release()
    cv2.destroyAllWindows()
