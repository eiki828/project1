from django.shortcuts import render
from django.http import StreamingHttpResponse
import datetime
import time

# IndexのViewを作成
def index(request):
    return render(request, 'eventstream/index.html')

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