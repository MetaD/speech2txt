# Transcribe Audio File with Google Cloud API
#  If trancribing local files:
#    On line 95, make sure local=True. Set long=False unless you are certain that
#    your audio files are quite long or large.
#  If getting errors such as:
#    "400 Inline audio exceeds duration limit. Please use a GCS URI."
#    "400 Request payload size exceeds the limit: 10485760 bytes."
#  Then the files are too long or too large for them to be transcribe locally.
#  Convert the files to one channel (use batch_conversion) and upload those files
#  to Google Cloud Storage. On line 95 set local=False, long=True. Also make sure
#  sample rate (line 50) is correct before transcribing.

from google.cloud import speech_v1
from google.api_core.exceptions import InvalidArgument
import wave
import audioop
import os
import logging
from tqdm import tqdm


def convert2mono(local_file_path, out_file_path=None):
    # convert audio to one channel (mono)
    with wave.open(local_file_path, 'rb') as f:
        rate = f.getframerate()
        audio = f.readframes(f.getnframes())
        audio = audioop.tomono(audio, 2, 1, 1)
        # write mono audio to file
        if out_file_path is not None:
            with wave.open(out_file_path, 'wb') as outf:
                outf.setparams(f.getparams())
                outf.setnchannels(1)
                outf.writeframes(audio)
    return rate, audio


def recognize(file_path, logger, local=True, long=False):
    """
    Transcribe a short audio file using synchronous speech recognition
    Args:
      local_file_path Path to local audio file, e.g. /path/audio.wav
    """

    client = speech_v1.SpeechClient()

    if local:
        # convert audio to one channel (mono)
        rate, audio = convert2mono(file_path)
    else:
        rate = 48000

    config = {
        "language_code": "en-US",  # The language of the supplied audio
        "audio_channel_count": 1,
        "sample_rate_hertz": rate,  # Sample rate in Hertz of the audio data sent
        "encoding": "LINEAR16",  # Encoding of audio data sent. This field is optional for FLAC and WAV audio formats
        "model": "default"
    }
    audio = {'content': audio} if local else {"uri": file_path}
    if long or len(audio['content']) > 10600000:
        response = client.long_running_recognize(config, audio).result().results
    else:
        try:
            response = client.recognize(config, audio).results
        except InvalidArgument:
            response = client.long_running_recognize(config, audio).result().results
    logger.info(str(response))
    # First alternative is the most probable result
    return ','.join([result.alternatives[0].transcript for result in response])


def main():
    # transcribing local files
    # audiopath = 'audio/'
    # filenames = sorted(os.listdir('audio'))

    # transcribing files on Google Cloud Storage
    audiopath = 'gs://dorm_study_audio/audio_mono/'
    filenames = sorted(os.listdir('audio_mono'))

    # set up logs
    transcripts_logger = logging.getLogger('transcripts')
    transcripts_logger.addHandler(logging.FileHandler('transcripts.log'))
    transcripts_logger.setLevel(logging.INFO)
    api_logger = logging.getLogger('api')
    api_logger.addHandler(logging.FileHandler('google_api_output.log'))
    api_logger.setLevel(logging.INFO)

    # transcribe
    for i, f in enumerate(tqdm(filenames)):
        if f.endswith('.wav'):
            api_logger.info(f)
            transcripts_logger.info(str(i) + ',' + f)
            try:
                transcript = recognize(audiopath + f, api_logger, local=False, long=True)
                transcripts_logger.info(transcript)
            except Exception as e:
                transcripts_logger.error(str(e))


def batch_conversion():
    audiopath = 'audio/'
    outpath = 'audio_mono/'
    with open('long_missing.txt', 'r') as f:
        filenames = f.readlines()
    filenames = [f.strip('\n') for f in filenames]
    for f in tqdm(filenames):
        try:
            rate, audio = convert2mono(audiopath + f, outpath + f)
            # print(rate)
        except Exception as e:
            print(f, e)


if __name__ == "__main__":
    # batch_conversion()
    main()
