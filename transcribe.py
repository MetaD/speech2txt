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

from google.cloud import speech_v1 as speech
from google.api_core.exceptions import InvalidArgument
import wave
import audioop
from pydub import AudioSegment
import os
import logging
from tqdm import tqdm


def convert2mono(local_file_path, out_file_path=None, ext='wav'):
    if ext != 'wav':
        audio = AudioSegment.from_file(local_file_path, ext)
        if out_file_path is None:
            local_file_path = local_file_path.replace(ext, 'wav')
            out_file_path = local_file_path
        else:
            local_file_path = out_file_path
        audio.export(out_file_path, format='wav')

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


def recognize(file_path, logger, local=True, long=False, ext='wav'):
    """
    Transcribe a short audio file using synchronous speech recognition
    """

    client = speech.SpeechClient()

    if local:
        # convert audio to one channel (mono)
        rate, audio = convert2mono(file_path, ext=ext)
    else:
        rate = 44100

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
    # audiopath = 't20_recordings/'
    # extension = 'm4a'
    # filenames = sorted([f for f in os.listdir(audiopath) if f.endswith(extension)])

    # transcribing files on Google Cloud Storage
    audiopath = 'gs://dorm_study_audio/audio_mono/'
    filenames = sorted(os.listdir('audio_mono'))
    extension = 'wav'

    # set up logs
    transcripts_logger = logging.getLogger('transcripts')
    transcripts_logger.addHandler(logging.FileHandler('transcripts.log'))
    transcripts_logger.setLevel(logging.INFO)
    api_logger = logging.getLogger('api')
    api_logger.addHandler(logging.FileHandler('google_api_output.log'))
    api_logger.setLevel(logging.INFO)

    # transcribe
    for i, f in enumerate(tqdm(filenames)):
        if f.endswith(extension):
            api_logger.info(f)
            transcripts_logger.info(str(i) + ',' + f)
            try:
                transcript = recognize(audiopath + f, api_logger,
                                       local=False, long=True, ext=extension)
                transcripts_logger.info(transcript)
            except Exception as e:
                transcripts_logger.error(str(e))


def batch_conversion(filenames=None, ext='wav'):
    """
    filenames: (string) txt file containing filenames (one per line)
    """
    audiopath = 't20_recordings/'
    outpath = 'audio_mono/'
    if not os.path.isdir(outpath):
        os.mkdir(outpath)
    if filenames:
        with open(filenames, 'r') as f:
            filenames = f.readlines()
        filenames = [f.strip('\n') for f in filenames]
    else:
        filenames = os.listdir(audiopath)
    for f in tqdm(filenames):
        try:
            rate, audio = convert2mono(audiopath + f,
                                       outpath + f.replace(ext, 'wav'),
                                       ext)
            print(rate)
        except Exception as e:
            print(f, e)


if __name__ == "__main__":
    # batch_conversion('long.txt', ext='m4a')
    main()
