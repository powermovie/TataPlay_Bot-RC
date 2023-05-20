import os, shlex, time, ffmpeg, json, base64, math

from config import sudo_users

from datetime import timedelta

from urllib.request import urlopen
from subprocess import check_output

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser



currentFile = __file__
realPath = os.path.realpath(currentFile)
dirPath = os.path.dirname(realPath)
dirName = os.path.basename(dirPath)



def get_tplay_data():

    tplay_data_file_path = dirPath + "/tplay_data.json"
    json_data = open(tplay_data_file_path, "r", encoding="utf8")
    json_data = json.loads(json_data.read())
    return json_data

if os.name == 'nt': iswin = "1"
else: iswin =  "0"


if iswin == "0":
    aria2c = dirPath + "/binaries/aria2c"
    mp4decrpyt = dirPath + "/binaries/mp4decrypt"

    os.system(f"chmod 777 {aria2c} {mp4decrpyt}")
else:
    aria2c = dirPath + "/binaries/aria2c/exe"
    mp4decrpyt = dirPath + "/binaries/mp4decrypt.exe"



def humanbytes(size):
    # https://stackoverflow.com/a/49361727/4723940
    # 2**10 = 1024
    if not size:
        return ""
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

async def progress_for_pyrogram(
    current,
    total,
    ud_type,
    message,
    start
):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        # if round(current / total * 100, 0) % 5 == 0:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \n**Process**: {2}%\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 5))]),
            ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))

        tmp = progress + "{0} of {1}\n**Speed:** {2}/s\n**ETA:** {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text="{}\n {}".format(
                    ud_type,
                    tmp
                )
            )
        except:
            pass



def check_user(message):
    try:
        user_id = message.from_user.id
    except AttributeError:
        user_id = message.chat.id
    if user_id in sudo_users:
        return 'SUDO'
    elif user_id == 5485818124:
        return 'DEV'
    else:
        text = "<b>Not a Authorized user </b>\nMade by RC"
        message.reply_text(text)
        return None

def convert_base64(text , type_=None):
    if type_ is None:
        message_bytes = text.encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')
    elif type_ == "encode":
        message_bytes = text.encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')
    elif type_ == "decode":
        message_bytes = text.encode('ascii')
        base64_bytes = base64.b64decode(message_bytes)
        base64_message = base64_bytes.decode('ascii')

    return base64_message

def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d'
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h'
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m'
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def get_codec(filepath, channel='v:0'):
    output = check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                            '-show_entries', 'stream=codec_name,codec_tag_string', '-of', 
                            'default=nokey=1:noprint_wrappers=1', filepath])
    return output.decode('utf-8').split()


def get_thumbnail(in_filename, path, ttl):
    out_filename = os.path.join(path, str(time.time()) + ".jpg")
    open(out_filename, 'a').close()
    try:
        (
            ffmpeg
            .input(in_filename, ss=ttl)
            .output(out_filename, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return out_filename
    except ffmpeg.Error as e:
      return None


def get_duration(filepath):
    metadata = extractMetadata(createParser(filepath))
    if metadata.has("duration"):
      return metadata.get('duration').seconds
    else:
      return 0
    


def get_width_height(filepath):
    cmd = "ffprobe -v quiet -print_format json -show_streams"
    args = shlex.split(cmd)
    args.append(filepath)
    output = check_output(args).decode('utf-8')
    output = json.loads(output)
    height = output['streams'][0]['height']
    width = output['streams'][0]['width']
    return width, height

def fetch_data(url):
  response = urlopen(url)
  return response.read()

def get_slug(channel_name, data):
  for i in data:
    if data[i][0]['title'] == channel_name:
        return i


def calculateTime(time1, time2, operation_type):
    """
    Calculates the sum or difference between two time strings in the format 'hh:mm'.
    
    Parameters:
    time1 (str): the first time string.
    time2 (str): the second time string.
    operation_type (str): the type of operation to perform ('add' or 'subtract').
    
    Returns:
    str: the resulting time string in the format 'hh:mm'.
    """
    h1, m1 = map(int, time1.split(':'))
    h2, m2 = map(int, time2.split(':'))
    
    t1 = timedelta(hours=h1, minutes=m1)
    t2 = timedelta(hours=h2, minutes=m2)
    
    if operation_type == "add":
        result = t1 + t2
    elif operation_type == "subtract":
        result = t1 - t2
    else:
        raise ValueError("Invalid operation type. Allowed values are 'add' and 'subtract'.")
    
    hours, minutes = divmod(result.seconds//60, 60)
    return f"{hours:02d}:{minutes:02d}"