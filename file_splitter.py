import os

folder = 'google_api_transcription'
if not os.path.isdir(folder):
    os.mkdir(folder)
with open('transcripts2.log', 'r') as infile:
    filename = ''
    counter = -1
    for line in infile:
        if len(filename) == 0:
            index, filename = line.split(',')
            assert int(index) > counter
            counter = int(index)
        else:
            with open(folder + '/' + filename.rsplit('.', 1)[0] + '.txt', 'w') as outfile:
                outfile.writelines([filename, line])
            filename = ''
