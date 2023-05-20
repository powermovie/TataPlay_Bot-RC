import os
import time
import subprocess
import threading
import json

from datetime import datetime

from pytz import timezone

from config import DL_DONE_MSG, GROUP_TAG

from urllib.request import urlopen, Request

from utils import get_slug, calculateTime, humanbytes, get_duration, get_thumbnail, progress_for_pyrogram, get_readable_time

from utils import aria2c, mp4decrpyt



def download_audio_stream(link, stream_format, filename, msg):
    try:
        cmd = [
        "yt-dlp",
        "--geo-bypass-country",
        "IN",
        "-k",
        "--allow-unplayable-formats",
        "--no-check-certificate",
        "-f",
        str(stream_format),
        f"{link}",
        "-o",
        f"{filename}.m4a",
        "--external-downloader",
        f"{aria2c}"
    ]
        subprocess.call(cmd)
    except Exception as e:
       msg.edit(str(e))


def mpd_download(link, audio_data, video_data, msg):
    # audio_data: ["audio_94482_hin=94000","audio_94490_tam=94000","audio_94483_tel=94000","audio_94486_ben=94000"]
    # video_id: "video=1297600"
    end_code = str(time.time()).replace("." , "")

    threads = []
    for i in range(0, len(audio_data)):
        filename = f"enc_{audio_data[i]}_{end_code}"
        thread = threading.Thread(target=download_audio_stream, args=(link, audio_data[i], filename, msg))
        threads.append(thread)
        thread.start()
        print(f"[DL] Audio Stream {i + 1} of {len(audio_data)}")
    try:
        video_cmd = [
            "yt-dlp",
            "--geo-bypass-country",
            "IN",
            "-k",
            "--allow-unplayable-formats",
            "--no-check-certificate",
            "-f",
            str(video_data),
            f"{link}",
            "-o",
            f"enc_{video_data}-{end_code}.mp4",
            "--external-downloader",
            f"{aria2c}"
        ]
        print("[DL] Video Stream")
        subprocess.call(video_cmd)
    except Exception as e:
       msg.edit(str(e))

    for thread in threads:
        thread.join()

    return end_code


def decrypt(audio_data, video_data, key, end_code, msg):
  for i in range(0 , len(audio_data)):
    enc_dl_audio_file_name = f"enc_{audio_data[i]}_{end_code}.m4a"
    dec_out_audio_file_name = f"dec_{audio_data[i]}_{end_code}.m4a"

    cmd_audio_decrypt = [
            f"{mp4decrpyt}",
            "--key",
            str(key),
            str(enc_dl_audio_file_name),
            str(dec_out_audio_file_name)
            
        ]
    try:
      decrypt_audio = subprocess.run(cmd_audio_decrypt, check=True)
    except subprocess.CalledProcessError as e:
      print(f"Error: Audio decryption failed for {enc_dl_audio_file_name}")
      return None

    try:
      os.remove(enc_dl_audio_file_name)
    except OSError as e:
      msg.edit(f"Error: Unable to remove encrypted audio file {enc_dl_audio_file_name}")
      return None

  enc_dl_video_file_name = f"enc_{video_data}-{end_code}.mp4"
  dec_out_video_file_name = f"dec_{video_data}-{end_code}.mp4"

  cmd_video_decrypt = [
            f"{mp4decrpyt}",
            "--key",
            str(key),
            str(enc_dl_video_file_name),
            str(dec_out_video_file_name)
            
        ]
  try:
    decrypt_video = subprocess.run(cmd_video_decrypt, check=True)
  except subprocess.CalledProcessError as e:
    msg.edit(f"Error: Video decryption failed for {enc_dl_video_file_name}")
    return None

  try:
    os.remove(enc_dl_video_file_name)
  except OSError as e:
    msg.edit(f"Error: Unable to remove encrypted video file {enc_dl_video_file_name}")
    return None

  return end_code


def mux_video(audio_data, video_data, end_code, show_name, res, langs, time_data, msg):
  dec_out_video_file_name = f"dec_{video_data}-{end_code}.mp4"
  audio_files = [f"dec_{audio_data[i]}_{end_code}.m4a" for i in range(len(audio_data))]
  ffmpeg_opts = ["ffmpeg", "-y", "-i", dec_out_video_file_name]
  
  for audio_file in audio_files:
    ffmpeg_opts.extend(["-i", audio_file])
  
  for i in range(len(audio_data)):
    ffmpeg_opts.extend(["-map", f"{i+1}:a:0"])
    
  ffmpeg_opts.extend(["-map", "0:v:0"])
  ffmpeg_opts.extend(["-metadata", f"encoded_by={GROUP_TAG}"])
  ffmpeg_opts.extend(["-metadata:s:a", f"title={GROUP_TAG}"])
  ffmpeg_opts.extend(["-metadata:s:v", f"title={GROUP_TAG}"])
  out_name = f"{end_code}.mkv"
  
  out_file_name = "{}.{}.{}.TATAPLAY.WEB-DL.AAC2.0.{}.H264-{}.mkv".format(show_name, time_data, res, "-".join(langs) , GROUP_TAG).replace(" " , ".")
  out_file_name = out_file_name.replace("30.00" , "30").replace("00.00" , "00")
  ffmpeg_opts.extend(["-c", "copy", out_name])
 
  try:
    subprocess.check_call(ffmpeg_opts)
  except subprocess.CalledProcessError as e:
    msg.edit(f"Error: {e}")
    return None

  try:
    os.rename(out_name, out_file_name)
  except OSError as e:
    msg.edit(f"Error: {e}")
    return None

  for audio_file in audio_files:
    try:
      os.remove(audio_file)
    except OSError as e:
      msg.edit(f"Error: {e}")
    
  try:
    os.remove(dec_out_video_file_name)
  except OSError as e:
    msg.edit(f"Error: {e}")

  return out_file_name


def ind_time():
    return datetime.now(timezone("Asia/Kolkata")).strftime('[%H:%M].[%d-%m-%Y]')


def download_playback_catchup(channel, title, data_json, app, message):
  msg = message.reply_text(f"<b>Processing...</b>")

  time_data = ind_time()
  
  final_file_name = "{}.{}.{}.TATAPLAY.WEB-DL.AAC2.0.{}.H264-{}.mkv".format(title, time_data, data_json[channel][0]['quality'], "-".join(data_json[channel][0]['audio']) , GROUP_TAG).replace(" " , ".")

  process_start_time = time.time()
        

  msg.edit(f'''<b>Downloading...</b>\n<code>{final_file_name}</code>
  ''')

  end_code = mpd_download(data_json[channel][0]['link'], data_json[channel][0]['audio_id'], data_json[channel][0]['video_id'], msg)

  msg.edit(f'''<b>Decrypting...</b>\n<code>{final_file_name}</code>
        ''')

  # Decrypting
  dec = decrypt(data_json[channel][0]['audio_id'], data_json[channel][0]['video_id'], data_json[channel][0]['k'], end_code, msg)
  msg.edit(f'''<b>Muxing...</b>\n<code>{final_file_name}</code>
        ''')

  # Muxing
  filename = mux_video(data_json[channel][0]['audio_id'], data_json[channel][0]['video_id'], end_code, title, data_json[channel][0]['quality'], data_json[channel][0]['audio'], time_data, msg)


  process_end_time = time.time()

  size = humanbytes(os.path.getsize(filename))
  duration = get_duration(filename)
  thumb = get_thumbnail(filename, "", duration / 2)
  start_time = time.time()
  caption = DL_DONE_MSG.format(
                  "Ripping" , get_readable_time(process_end_time - process_start_time) ,filename, data_json[channel][0]['title'] , size)
  app.send_video(video=filename, chat_id = message.from_user.id , caption=caption , progress=progress_for_pyrogram, progress_args=("**Uploading...** \n", msg, start_time) , thumb=thumb, duration=duration , width=1280, height=720)
          

  os.remove(filename)
          
  msg.delete()

  

   


def download_catchup(catchup_url, data_json, app, message):
    '''
    Parameters:
    catchup_url (str): URLs of TataPlay seperated by +, also can add |CUSTOM Title for Custom Title
    data_json (json): json containing all the info


    Example:
    (More than one url and with Custom Title)
    https://watch.tataplay.com/Kora/121211|Kora.S01E01+https://watch.tataplay.com/Kora/565656|Kora.S01E02
    
    
    (More than one url and with No Custom Title i.e Title from tataplay side)
    https://watch.tataplay.com/Kora/121211+https://watch.tataplay.com/Kora/565656
    
    '''
    catchup_urls = catchup_url.split("+")
    for m in catchup_urls:
        if "|" in m:
            catchup_id, title = m.split("|")[0].split("/")[-1], m.split("|")[1].strip().replace(" ", ".")
        else:
            catchup_id = m.split("/")[-1]
            title = "NO CUSTOM"

        msg = message.reply_text(f"<b>Processing...</b>")
        tataskyapiurl = f'https://streamtape-vercel.vercel.app/url?query=https://kong-tatasky.videoready.tv/content-detail/pub/api/v1/catchupEpg/{catchup_id}'
        trequest = Request(tataskyapiurl, headers={'User-Agent': '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'})
        tResponse = urlopen(trequest)
        tplay_catchup_data = json.loads(tResponse.read())
        channel_tplay_catchup = tplay_catchup_data['data']['meta'][0]['channelName']

        channel = get_slug(channel_tplay_catchup, data_json)
        

        if channel is None:
           msg.edit(f'''<b>Error...</b>\n<code>Channel Not Available to RIP</code>
        ''')
           return
        
        tplay_startTime = tplay_catchup_data['data']['meta'][0]['startTime'] / 1000
        tplay_endTime = tplay_catchup_data['data']['meta'][0]['endTime'] / 1000
        
        sT = time.strftime('%H:%M', time.localtime(tplay_startTime))
        eT = time.strftime('%H:%M', time.localtime(tplay_endTime))
        
        time_data = "[" + calculateTime(sT, "05:30", "add").replace(":", ".") + "-" + calculateTime(eT, "05:30", "add").replace(":", ".") +"]" + ".["  + time.strftime('%d-%m-%Y', time.localtime(tplay_startTime)) + "]"
        
        # Custom Title or TPlay Provided Title
        if title == "NO CUSTOM":
            title = tplay_catchup_data['data']['meta'][0]['title'].replace("Movie - ", "")
        else:
            title == title


        

        
        final_file_name = "{}.{}.{}.TATAPLAY.WEB-DL.AAC2.0.{}.H264-{}.mkv".format(title, time_data, data_json[channel][0]['quality'], "-".join(data_json[channel][0]['audio']) , GROUP_TAG).replace(" " , ".")

        
        
        
        print("________________________")
        print(f"Catchup ID : [{catchup_id.split('?')[0]}]")
        
        

        print(title)
        print(time_data)
        # Downloading

        process_start_time = time.time()
        

        msg.edit(f'''<b>Downloading...</b>\n<code>{final_file_name}</code>
        ''')


        end_code = mpd_download(tplay_catchup_data['data']['detail']['dashWidewinePlayUrl'], data_json[channel][0]['audio_id'], data_json[channel][0]['video_id'], msg)

        msg.edit(f'''<b>Decrypting...</b>\n<code>{final_file_name}</code>
        ''')

        # Decrypting
        dec = decrypt(data_json[channel][0]['audio_id'], data_json[channel][0]['video_id'], data_json[channel][0]['k'], end_code, msg)
        msg.edit(f'''<b>Muxing...</b>\n<code>{final_file_name}</code>
        ''')

        # Muxing
        filename = mux_video(data_json[channel][0]['audio_id'], data_json[channel][0]['video_id'], end_code, title, data_json[channel][0]['quality'], data_json[channel][0]['audio'], time_data, msg)


        process_end_time = time.time()

        size = humanbytes(os.path.getsize(filename))
        duration = get_duration(filename)
        thumb = get_thumbnail(filename, "", duration / 2)
        start_time = time.time()
        caption = DL_DONE_MSG.format(
                "Ripping" , get_readable_time(process_end_time - process_start_time) ,filename, data_json[channel][0]['title'] , size)
        app.send_video(video=filename, chat_id = message.from_user.id , caption=caption , progress=progress_for_pyrogram, progress_args=("**Uploading...** \n", msg, start_time) , thumb=thumb, duration=duration , width=1280, height=720)
        

        os.remove(filename)
        
        msg.delete()