/*
  Faun CoreAudio (AudioQueue) backend — macOS

  上游 faun(codeberg.org/wickedsmoke/faun v0.2.3)只內建 Android(AAudio)、
  Linux(PulseAudio)、Windows(WASAPI)三個音訊後端,沒有 macOS。本檔為 Ultima IV
  繁中版補上 macOS 音訊輸出,沿用 faun 既有的 sysaudio_* 介面與 blocking-push 語意:
  faun 的 mixer 執行緒反覆呼叫 sysaudio_write() 推送已混音 PCM,backend 負責節流
  (裝置吃不下就阻塞)。對應 PulseAudio 版的 pa_stream_writable_size 等待,這裡用
  AudioQueue 的 buffer pool + dispatch 號誌:空閒 buffer 用完即阻塞,callback 播完
  一塊就歸還並喚醒寫入端。

  faun 系統 voice 固定 FAUN_F32 / 立體聲 / 44100(faun.c 的 faun_startup),格式映射
  仍寫全(U8/S16/S24/F32)以防未來改動。此檔由 faun.c 在 defined(__APPLE__) 時 #include
  進來,故 FaunVoice / FAUN_* / faun_channelCount 等型別在此可見。
*/

#include <AudioToolbox/AudioToolbox.h>
#include <dispatch/dispatch.h>
#include <pthread.h>
#include <string.h>

#define CA_NUM_BUFFERS  3

typedef struct {
    AudioQueueRef        queue;
    AudioQueueBufferRef  bufPool[CA_NUM_BUFFERS];   // 全部 buffer(釋放用)
    AudioQueueBufferRef  freeRing[CA_NUM_BUFFERS];  // 空閒 buffer 環
    int                  ringHead;                  // 寫入端取出位置
    int                  ringTail;                  // callback 歸還位置
    dispatch_semaphore_t freeSem;                   // 空閒 buffer 計數
    pthread_mutex_t      ringLock;                  // 保護 ringTail
}
CoreAudioSession;

static CoreAudioSession caSession;

// AudioQueue 播完一塊 → 歸還空閒環、號誌 +1,喚醒可能在等的 sysaudio_write。
static void ca_callback(void* userData, AudioQueueRef aq, AudioQueueBufferRef buf)
{
    CoreAudioSession* s = (CoreAudioSession*) userData;
    (void) aq;
    pthread_mutex_lock(&s->ringLock);
    s->freeRing[s->ringTail] = buf;
    s->ringTail = (s->ringTail + 1) % CA_NUM_BUFFERS;
    pthread_mutex_unlock(&s->ringLock);
    dispatch_semaphore_signal(s->freeSem);
}

static void sysaudio_close()
{
    // CoreAudio 無全域 context(狀態綁在 voice/queue),no-op。
}

static const char* sysaudio_open(const char* appName)
{
    (void) appName;
    return NULL;
}

static const char* sysaudio_allocVoice(FaunVoice* voice, int updateHz,
                                       const char* appName)
{
    CoreAudioSession* s = &caSession;
    OSStatus err;
    int chan, bytesPerSample, i;
    UInt32 bufBytes;
    AudioStreamBasicDescription fmt;

    (void) updateHz;
    (void) appName;
    memset(s, 0, sizeof(*s));

    chan = faun_channelCount(voice->mix.chanLayout);

    memset(&fmt, 0, sizeof(fmt));
    fmt.mSampleRate       = voice->mix.rate;
    fmt.mFormatID         = kAudioFormatLinearPCM;
    fmt.mChannelsPerFrame = chan;
    fmt.mFramesPerPacket  = 1;

    switch (voice->mix.format) {
        case FAUN_U8:
            fmt.mFormatFlags = kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 8;  bytesPerSample = 1; break;
        case FAUN_S16:
            fmt.mFormatFlags = kAudioFormatFlagIsSignedInteger |
                               kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 16; bytesPerSample = 2; break;
        case FAUN_S24:
            fmt.mFormatFlags = kAudioFormatFlagIsSignedInteger |
                               kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 24; bytesPerSample = 3; break;
        case FAUN_F32:
        default:
            fmt.mFormatFlags = kAudioFormatFlagIsFloat |
                               kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 32; bytesPerSample = 4; break;
    }
    fmt.mBytesPerFrame  = chan * bytesPerSample;
    fmt.mBytesPerPacket = fmt.mBytesPerFrame;

    err = AudioQueueNewOutput(&fmt, ca_callback, s, NULL, NULL, 0, &s->queue);
    if (err)
        return "AudioQueueNewOutput failed";

    // 每塊容納一次完整 mix 寫入(mix.avail frames);下限保險。
    bufBytes = voice->mix.avail * fmt.mBytesPerFrame;
    if (bufBytes < 4096)
        bufBytes = 4096;

    pthread_mutex_init(&s->ringLock, NULL);
    s->freeSem  = dispatch_semaphore_create(0);
    s->ringHead = s->ringTail = 0;

    for (i = 0; i < CA_NUM_BUFFERS; ++i) {
        err = AudioQueueAllocateBuffer(s->queue, bufBytes, &s->bufPool[i]);
        if (err)
            return "AudioQueueAllocateBuffer failed";
        s->freeRing[s->ringTail] = s->bufPool[i];
        s->ringTail = (s->ringTail + 1) % CA_NUM_BUFFERS;
        dispatch_semaphore_signal(s->freeSem);
    }

    voice->backend = s;
    return NULL;
}

#define CAS  ((CoreAudioSession*) voice->backend)

static void sysaudio_freeVoice(FaunVoice* voice)
{
    CoreAudioSession* s = CAS;
    if (s && s->queue) {
        AudioQueueStop(s->queue, true);
        AudioQueueDispose(s->queue, true);
        s->queue = NULL;
        if (s->freeSem)
            dispatch_release(s->freeSem);
        pthread_mutex_destroy(&s->ringLock);
        voice->backend = NULL;
    }
}

static const char* sysaudio_write(FaunVoice* voice, const void* data,
                                  uint32_t len)
{
    CoreAudioSession* s = CAS;
    AudioQueueBufferRef buf;
    OSStatus err;

    // 等一塊空閒 buffer(對應 PulseAudio 的 writable_size 節流)。
    dispatch_semaphore_wait(s->freeSem, DISPATCH_TIME_FOREVER);

    buf = s->freeRing[s->ringHead];
    s->ringHead = (s->ringHead + 1) % CA_NUM_BUFFERS;

    if (len > buf->mAudioDataBytesCapacity)
        len = buf->mAudioDataBytesCapacity;
    memcpy(buf->mAudioData, data, len);
    buf->mAudioDataByteSize = len;

    err = AudioQueueEnqueueBuffer(s->queue, buf, 0, NULL);
    if (err)
        return "AudioQueueEnqueueBuffer failed";
    return NULL;
}

static int sysaudio_startVoice(FaunVoice* voice)
{
    CoreAudioSession* s = CAS;
    AudioQueueStart(s->queue, NULL);
    return 1;
}

static int sysaudio_stopVoice(FaunVoice* voice)
{
    CoreAudioSession* s = CAS;
    AudioQueuePause(s->queue);   // 對應 cork:暫停但保留已排入的資料
    return 1;
}
